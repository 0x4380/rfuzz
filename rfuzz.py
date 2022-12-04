import requests
import concurrent.futures

DOMAINS = 'domains.lst'
ROUTES = 'routes.lst'


def routes_gen(domain, routes):
    url_list = list()
    with open(domain, 'r') as domains, open(routes) as routes:
        for d in domains:
            for r in routes:
                url_list.append(f"https://{d.strip()}/{r.strip()}")
    return url_list


def check200(url):
    return url, requests.get(url).status_code == 200


def run_threads(url_list):
    with open("result_200.txt", 'w') as output:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = pool.map(check200, url_list)
            for url, is200 in results:
                print(f"Checking\t {url}")
                if is200:
                    output.write(url)


run_threads(routes_gen(DOMAINS, ROUTES))
