import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
import logging
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

# Конфигурация
MAX_WORKERS = 10
TIMEOUT = 10
RETRY_TOTAL = 3
BATCH_SIZE = 1000

def create_session():
    session = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=MAX_WORKERS)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def validate_domain(domain):
    domain = domain.strip()
    if not domain or domain.startswith('#'):
        return None
    try:
        result = urlparse(f"https://{domain}")
        return result.netloc if result.netloc else domain
    except:
        return None

def validate_route(route):
    route = route.strip()
    if not route or route.startswith('#'):
        return None
    return route.lstrip('/')

def routes_gen(domain_file, routes_file):
    if not Path(domain_file).exists():
        logging.error(f"File not found: {domain_file}")
        return []
    if not Path(routes_file).exists():
        logging.error(f"File not found: {routes_file}")
        return []
    
    logging.info('Generating URL list')
    counter = 0
    url_list = []
    
    with open(domain_file, 'r', encoding='utf-8') as domains_list:
        for d in domains_list:
            domain = validate_domain(d)
            if not domain:
                continue
                
            with open(routes_file, 'r', encoding='utf-8') as routes_list:
                for r in routes_list:
                    route = validate_route(r)
                    if not route:
                        continue
                    url = f"https://{domain}/{route}"
                    url_list.append(url)
                    counter += 1
                    
                    # Батчинг для экономии памяти
                    if len(url_list) >= BATCH_SIZE:
                        yield url_list
                        url_list = []
                        logging.info(f"Processed {counter} URLs")
    
    if url_list:
        yield url_list
    logging.info(f"Total URLs generated: {counter}")

def check200(url, session):
    try:
        response = session.get(url, allow_redirects=False, timeout=TIMEOUT)
        status_code = response.status_code
        logging.debug(f"Result: {status_code}\t{url}")
        
        if status_code == 200:
            logging.info(f"\t200 FOUND!\t{url}")
            return url
        return None
        
    except requests.exceptions.Timeout:
        logging.warning(f"Timeout: {url}")
        return None
    except requests.exceptions.ConnectionError:
        logging.warning(f"Connection error: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error {url}: {e}")
        return None

def run_threads(url_generator):
    time_start = time.perf_counter()
    session = create_session()
    total_found = 0
    
    try:
        with open("result_200.txt", 'w', encoding='utf-8') as output:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                for url_batch in url_generator:
                    # Создаём частичную функцию с сессией
                    check_func = lambda url: check200(url, session)
                    for result in pool.map(check_func, url_batch):
                        if result:
                            output.write(f"{result}\t200\n")
                            print(f"200 FOUND:\t{result}")
                            total_found += 1
    except KeyboardInterrupt:
        logging.warning("Script interrupted by user")
        print("\n⚠️  Script interrupted by user")
    finally:
        session.close()
    
    time_done = time.perf_counter()
    print(f'\nTotal time: {time_done - time_start:0.2f} seconds.')
    print(f'Total 200 found: {total_found}')

# Запуск
if __name__ == "__main__":
    url_gen = routes_gen(DOMAINS, ROUTES)
    run_threads(url_gen)
