import time
import aiohttp
import asyncio
import logging

logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', )


def count_lines():
    with open("routes.lst", 'r') as fp:
        TODO: file_name from args
        x = len(fp.readlines())
    return x


async def get_lines(lines_count, domain_name):
    list_200 = list()
    total = count_lines()
    with open("routes.lst") as myfile:
        TODO: file_name from args
        final_list = list()
        big_list = list()
        for l in myfile:
            big_list.append(l)
        lines_start = 0
        iter_size = lines_count
        lines_end = lines_count
        while lines_end <= total:
            slice_lines = big_list[int(lines_start):int(lines_end)]
            s_counter = lines_start
            for s in slice_lines:
                url = f"https://{domain_name}/{s.strip()}"
                final_list.append(url)
                s_counter += 1
            lines_start = lines_end
            lines_end += iter_size
            try:
                async with aiohttp.ClientSession() as session:
                    for full_url in final_list:
                        async with session.get(full_url) as resp:
                            url_status = resp.status
                            print(f"{url_status}\t\t{full_url}")
                            if url_status == 200:
                                list_200.append(f"200\t{full_url}")
                                
            except:
                logging.error(f'ERROR: session.get(full_url)')
            slice_lines.clear()


async def walk_list():
    with open("domains.lst") as domain_list:
        time_start = time.perf_counter()
        for domain in domain_list:
            domain_name = domain.strip()
            await get_lines(100, domain_name)
        time_done = time.perf_counter()
        print(f'Total time elapsed: {time_done - time_start:0.2f} seconds.')


asyncio.run(walk_list())
