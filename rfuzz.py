import asyncio
import errno
import os
import time
import httpx


def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e:  
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
    urls = ['https://google.com'] #First URL to check
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
        try:
            print('Checking URL: ', url)
            return await client.get(url, follow_redirects=False)
        except httpx.RequestError as exc:
            print(f"\t\tERROR occurred while requesting {exc.request.url!r}.")
        except httpx.HTTPStatusError as exc:
            print(f"\t\tERROR response {exc.response.status_code} while requesting {exc.request.url!r}.")
        except:
            print(f"Error sending request for ", url)


async def launch():
    tm1 = time.perf_counter()
    list_200 = ['']
    url_list = url_list_gen()
    results = await asyncio.gather(*map(get_async, url_list))
    for r in results:
        if r.status_code == 200:
            print('FOUND!\t\t' + r.request.url + '\t 200')
            list_200.append(r.request.url + '\t 200')
    save_to_file(list_200, 'results_200.txt')
    tm2 = time.perf_counter()
    print(f'Total time elapsed: {tm2 - tm1:0.2f} seconds')


asyncio.run(launch())
