import requests
import concurrent.futures
import logging
import time

# TODO: make script args for domains and routes, for logging config and verbose, for custom status codes logging
DOMAINS = 'domains.lst'
ROUTES = 'routes.lst'
logging.basicConfig(filename='debugging.log', encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', )


def routes_gen(domain, routes):
    logging.info('Generating URL list')
    counter = 0
    url_list = list()
    with open(domain, 'r') as domains_list:
        for d in domains_list:
            with open(routes, 'r') as routes_list:
                for r in routes_list:
                    url_list.append(f"https://{d.strip()}/{r.strip()}")
                    counter += 1
    logging.info(f"Total URL in list: {counter}")
    return url_list


def check200(url):
    try:
        status_code = requests.get(url, allow_redirects=False).status_code
        logging.debug(f"Result: {status_code}\t{url}")
        if status_code == 200:
            logging.info(f"\t200 FOUND!\t{url}")
            return url
    except:
        return None
        raise


def run_threads(url_list):
    time_start = time.perf_counter()
    with open("result_200.txt", 'w') as output:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            for result in pool.map(check200, url_list):
                if result:
                    output.write(f"{result}\t200\n")
                    print(f"200 FOUND:\t{result}")
    time_done = time.perf_counter()
    print(f'Total time: {time_done - time_start:0.2f} seconds.')


list_urls = routes_gen(DOMAINS, ROUTES)
run_threads(list_urls)
