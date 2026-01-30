import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
import logging
import time
from pathlib import Path
from datetime import datetime
import argparse
import signal
import sys
import urllib3

DEFAULT_CONFIG = {
    'max_workers': 10,
    'timeout': 8,  # Optimal timeout for fast scan
    'max_response_size': 5 * 1024 * 1024,  # 5 MB max response size
    'max_download_time': 30,  # Max 30 seconds per download
    'min_speed_kbps': 5,  # Minimum acceptable speed: 5 KB/s
    'retries': 2,
    'follow_redirects': False,
    'verify_ssl': False,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'interesting_codes': [200, 201, 204, 301, 302, 401, 403, 500],
}

# Disabling SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PentestScanner:
    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.session = None
        self.results = {'total': 0, 'found': 0, 'skipped': 0}
        self.running = True
        self.skipped_urls = []  # Store skipped URLs for reporting

        # Ctrl+C for correct shutdown
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        print("\n⚠️  Stopping scans...")
        self.running = False

    def create_session(self):
        session = requests.Session()

        # Browser headers
        session.headers.update({
            'User-Agent': self.config['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

        # Retries only for critical/interesting errors
        retry = Retry(
            total=self.config['retries'],
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )

        adapter = HTTPAdapter(
            max_retries=retry,
            pool_maxsize=self.config['max_workers'],
            pool_connections=self.config['max_workers']
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def load_file_lines(self, filepath, skip_comments=True):
        if not Path(filepath).exists():
            logging.error(f"File not found: {filepath}")
            return []

        lines = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if skip_comments and line.startswith('#'):
                    continue
                if line:
                    lines.append(line)
        return lines

    def generate_urls(self, domains_file, routes_file):
        """Combinate list of All Domains + All Routes"""
        domains = self.load_file_lines(domains_file)
        routes = self.load_file_lines(routes_file)

        if not domains or not routes:
            logging.error("There is no domains or routes")
            return []

        logging.info(f"Domains loaded: {len(domains)}")
        logging.info(f"Routes loaded: {len(routes)}")

        url_list = []
        for domain in domains:
            domain_clean = domain.strip().replace('http://', '').replace('https://', '').rstrip('/')

            for route in routes:
                route_clean = route.strip().lstrip('/')

                # Base URL path
                if not route_clean:
                    url = f"https://{domain_clean}/"
                else:
                    url = f"https://{domain_clean}/{route_clean}"

                url_list.append(url)

        total = len(domains) * len(routes)
        logging.info(f"URL generated count: {total}")
        print(f"🎯 Scanning {total} URL...")

        return url_list

    def check_url(self, url):
        if not self.running:
            return None

        try:
            start_time = time.time()

            # Stream response to avoid memory bombs
            response = None
            try:
                response = self.session.get(
                    url,
                    allow_redirects=self.config['follow_redirects'],
                    timeout=self.config['timeout'],
                    verify=self.config['verify_ssl'],
                    stream=True
                )

                # Check Content-Length header first
                content_length = int(response.headers.get('Content-Length', 0))
                if content_length > self.config['max_response_size']:
                    self._skip_url(url, f"TOO_LARGE ({content_length / 1024 / 1024:.1f}MB)")
                    return None

                # Download with limits
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    elapsed = time.time() - start_time

                    # Time limit
                    if elapsed > self.config['max_download_time']:
                        self._skip_url(url, f"SLOW ({elapsed:.1f}s)")
                        return None

                    # Size limit
                    if len(content) + len(chunk) > self.config['max_response_size']:
                        self._skip_url(url, f"SIZE_LIMIT")
                        return None

                    # Speed check (after 3 seconds)
                    if elapsed > 3:
                        speed_kbps = (len(content) / elapsed) / 1024
                        if speed_kbps < self.config['min_speed_kbps']:
                            self._skip_url(url, f"SPEED {speed_kbps:.1f}KB/s")
                            return None

                    content += chunk

                elapsed_total = (time.time() - start_time) * 1000
                status_code = response.status_code
                content_length_actual = len(content)

                if status_code in self.config['interesting_codes']:
                    result = {
                        'url': url,
                        'status': status_code,
                        'length': content_length_actual,
                        'time': elapsed_total
                    }
                    status_color = self._get_status_color(status_code)
                    print(
                        f"\r[{status_color}{status_code}\033[0m] {url} | {content_length_actual} bytes | {elapsed_total:.0f}ms")
                    logging.info(f"FOUND [{status_code}] {url}")
                    self.results['found'] += 1
                    return result

                return None

            finally:
                if response:
                    try:
                        response.close()
                    except:
                        pass

        except requests.exceptions.Timeout:
            self._skip_url(url, "TIMEOUT")
            return None
        except requests.exceptions.ConnectionError as e:
            # TODO: Need to get some other error's from github's issues
            if "10061" in str(e) or "Connection refused" in str(e):
                self._skip_url(url, "CONN_REFUSED")
            else:
                logging.debug(f"CONN_ERR: {url}")
            return None
        except requests.exceptions.SSLError:
            logging.debug(f"SSL_ERR: {url}")
            return None
        except Exception as e:
            logging.debug(f"ERROR {url}: {e}")
            return None

    def _skip_url(self, url, reason):
        """Mark URL as skipped and log it"""
        self.results['skipped'] += 1
        self.skipped_urls.append({'url': url, 'reason': reason})

        # Color-coded output for skipped URLs
        print(f"\r[\033[94mSKIP\033[0m] {url} | {reason}{' ' * 50}")
        logging.warning(f"SKIPPED [{reason}] {url}")

        # Return to progress line
        if self.results['total'] > 0:
            scanned = self.results['found'] + self.results['skipped']
            progress = (scanned / self.results['total']) * 100
            stats = f"Found: {self.results['found']}"
            if self.results['skipped'] > 0:
                stats += f" | Skipped: {self.results['skipped']}"
            print(f"📊 {progress:.1f}% ({scanned}/{self.results['total']}) | {stats}", end='\r')

    def _get_status_color(self, status_code):
        if 200 <= status_code < 300:
            return "\033[92m"  # Green
        elif 300 <= status_code < 400:
            return "\033[93m"  # Yellow
        elif 400 <= status_code < 500:
            return "\033[91m"  # Red
        elif 500 <= status_code < 600:
            return "\033[95m"  # Purple
        return "\033[97m"  # White

    def save_results(self, results, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Scan date {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Scanned total: {self.results['total']}\n")
            f.write(f"# Found: {self.results['found']}\n")
            f.write(f"# Skipped: {self.results['skipped']}\n")
            f.write("=" * 80 + "\n\n")

            # Report skipped URLs
            if self.skipped_urls:
                f.write("⚠️  SKIPPED URLS (potential traps or slow responses):\n")
                for item in self.skipped_urls:
                    f.write(f"  [{item['reason']}] {item['url']}\n")
                f.write("\n" + "=" * 80 + "\n\n")

            # Group by status codes
            grouped = {}
            for r in results:
                if r:
                    grouped.setdefault(r['status'], []).append(r)

            for status in sorted(grouped.keys()):
                f.write(f"\n{'=' * 20} STATUS {status} {'=' * 20}\n")
                for r in sorted(grouped[status], key=lambda x: x['length'], reverse=True):
                    f.write(f"[{status}] {r['url']} | {r['length']} bytes | {r['time']:.0f}ms\n")

        print(f"\n💾 Results saved: {output_file}")

    def run(self, domains_file, routes_file, output_file='results.txt'):
        print("=" * 60)
        print(" " * 5 + " _______     ________          ________  ________  ")
        print(" " * 5 + "|_   __ \\   |_   __  |        |  __   _||  __   _| ")
        print(" " * 5 + "  | |__) |    | |_ \\_|__   _  |_/  / /  |_/  / /   ")
        print(" " * 5 + "  |  __ /     |  _|  [  | | |    .'.' _    .'.' _  ")
        print(" " * 5 + " _| |  \\ \\_  _| |_    | \\_/ |, _/ /__/ | _/ /__/ | ")
        print(" " * 5 + "|____| |___||_____|   '.__.'_||________||________| ")
        print("=" * 60)
        print(f"Streams: {self.config['max_workers']}")
        print(f"Timeout: {self.config['timeout']}s")
        print(f"Max response size: {self.config['max_response_size'] / 1024 / 1024:.1f} MB")
        print(f"Max download time: {self.config['max_download_time']}s")
        print(f"SSL verify: {self.config['verify_ssl']}")
        print(f"Follow redirects: {self.config['follow_redirects']}")
        print("=" * 60 + "\n")

        start_time = time.time()
        url_list = self.generate_urls(domains_file, routes_file)
        if not url_list:
            return

        self.results['total'] = len(url_list)
        self.session = self.create_session()

        # Scan flow
        results = []
        try:
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config['max_workers']
            ) as executor:
                for result in executor.map(self.check_url, url_list):
                    results.append(result)

                    # Showing progress every 100 requests
                    scanned = self.results['found'] + self.results['skipped']
                    if scanned > 0 and scanned % 100 == 0:
                        progress = (scanned / self.results['total']) * 100
                        stats = f"Found: {self.results['found']}"
                        if self.results['skipped'] > 0:
                            stats += f" | Skipped: {self.results['skipped']}"
                        print(f"📊 {progress:.1f}% ({scanned}/{self.results['total']}) | {stats}", end='\r')

        except KeyboardInterrupt:
            print("\n⚠️  Scan interrupted.")
        finally:
            self.session.close()

        # Save results
        self.save_results(results, output_file)

        # Final statistics
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"✅ Scan is done")
        print(f"⏱️  Time: {elapsed:.2f} sec ({elapsed / 60:.2f} min)")
        print(f"🔍 Checked: {self.results['total']}")
        print(f"🎯 Found: {self.results['found']}")
        if self.results['skipped'] > 0:
            print(f"⏭️  Skipped: {self.results['skipped']}")
        print(f"⚡ Speed: {self.results['total'] / elapsed:.1f} URL/s")
        print("=" * 60)


# ==================== CLI Interface ====================
def main():
    parser = argparse.ArgumentParser(
        description='RFuZZ - Multiplle Domains+Routes fuzzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Samples:
  %(prog)s -d domains.txt -r routes.txt
  %(prog)s -d scope.txt -r wordlist.txt -o results.txt -t 30 -w 50
  %(prog)s -d targets.txt -r sensitive.txt --status-codes 200,403,401

Protection against traps:
  - Max response size limit (default: 5 MB)
  - Max download time per request (default: 30 seconds)
  - Minimum download speed check (default: 5 KB/s)
  - Streaming responses to avoid memory issues
        '''
    )

    parser.add_argument('-d', '--domains', required=True, help='domains list file')
    parser.add_argument('-r', '--routes', required=True, help='routes and interesting files list')
    parser.add_argument('-o', '--output', default='results.txt', help='filename for scan results')
    parser.add_argument('-w', '--workers', type=int, default=20, help='Workers count (by default: 10)')
    parser.add_argument('-t', '--timeout', type=int, default=8, help='Request timeout (by default: 8)')
    parser.add_argument('--max-size', type=int, default=5, help='Max response size in MB (by default: 5)')
    parser.add_argument('--max-time', type=int, default=30,
                        help='Max download time per request in seconds (by default: 30)')
    parser.add_argument('--min-speed', type=int, default=5,
                        help='Minimum acceptable download speed in KB/s (by default: 5)')
    parser.add_argument('--retries', type=int, default=2, help='Request retry (by default: 2)')
    parser.add_argument('--follow-redirects', action='store_true', help='For follow redirects (by default: False)')
    parser.add_argument('--verify-ssl', action='store_true', help='Check SSL certificate (by default: False)')
    parser.add_argument('--user-agent', default=DEFAULT_CONFIG['user_agent'], help='Custom User-Agent')
    parser.add_argument('--status-codes', default='200,201,204,301,302,401,403,500',
                        help='Interesting status codes separated by commas (by default: 200,201,204,301,302,401,403,500)')

    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # Log config
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        filename='scanner.log',
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Parsing status codes
    try:
        status_codes = [int(code.strip()) for code in args.status_codes.split(',')]
    except:
        print("❌ Error: status codes must be a comma-separated list of integers")
        return

    # Config ARGS
    config = {
        'max_workers': args.workers,
        'timeout': args.timeout,
        'max_response_size': args.max_size * 1024 * 1024,  # Convert MB to bytes
        'max_download_time': args.max_time,
        'min_speed_kbps': args.min_speed,
        'retries': args.retries,
        'follow_redirects': args.follow_redirects,
        'verify_ssl': args.verify_ssl,
        'user_agent': args.user_agent,
        'interesting_codes': status_codes,
    }

    # Main run
    scanner = PentestScanner(config)
    scanner.run(args.domains, args.routes, args.output)


if __name__ == '__main__':
    main()
