import asyncio
import errno
import os
import time
import httpx


def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e:  # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occurred


def save_to_file(link_list, filename):
    silent_remove(filename)
    with open(filename, mode='wt', encoding='utf-8') as result:
        result.write('\n'.join(link_list))
        result.write('\n')
        result.close()
    return 'ok'


def url_list_gen():
  # TODO: make domains.lst and routes.lst as input in args for rfuzz.py 
    urls = ['https://test.com'] # check outgoing connection first
    with open("domains.lst") as domain_list:
        for domain in domain_list:
            domain = domain.strip()
            with open("routes.lst") as file2:
                for route in file2:
                    route = route.strip()
                    url = 'https://' + domain + '/' + route
                    urls.append(url)
    return urls


async def get_async(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)


async def launch():
    list_200 = ['']
    url_list = url_list_gen()
    resps = await asyncio.gather(*map(get_async, url_list))
    for resp in resps:
        if resp.status_code == 200:
            print('FOUND!\t\t' + resp.request.url + '\t 200')
            list_200.append(resp.request.url + '\t 200')
    save_to_file(list_200, 'results_200.txt')


tm1 = time.perf_counter()

asyncio.run(launch())

tm2 = time.perf_counter()
print(f'Total time elapsed: {tm2 - tm1:0.2f} seconds')
