import time
import aiohttp
import asyncio
import logging
import os, errno

# 861.71 seconds for 9*400 URLs
logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', )


def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occurred


def save_to_file(list_to_save, filename):
    silent_remove(filename)
    with open(filename, mode='wt', encoding='utf-8') as result:
        result.write('\n'.join(list_to_save))
        result.write('\n')
        result.close()
    return 'ok'


def count_lines():
    with open("routes.lst", 'r') as fp:
        # TODO: file_name from args
        x = len(fp.readlines())
    return x


async def get_lines(lines_count, domain_name):
    list_200 = list()
    total = count_lines()
    with open("routes.lst") as routes_list:
        final_list = list()
        big_list = list()
        for l in routes_list:
            # TODO: file_name from args
            big_list.append(l)
        lines_start = 0
        iter_size = lines_count
        lines_end = lines_count
        print(f"Preparing list of urls ...")
        while lines_end <= total:
            slice_lines = big_list[int(lines_start):int(lines_end)]
            s_counter = lines_start
            for s in slice_lines:
                url = f"https://{domain_name}/{s.strip()}"
                final_list.append(url)
                s_counter += 1
            lines_start = lines_end
            lines_end += iter_size
            slice_lines.clear()
    try:
        async with aiohttp.ClientSession() as session:
            for full_url in final_list:
                try:
                    # Turned off SSL validation for speed up
                    # And to skip race condition in ssl.py/sslproto.py
                    async with session.get(full_url, allow_redirects=False, timeout=15,
                                           ssl=False) as resp:
                        try:
                            url_status = resp.status
                            print(f"{url_status}\t\t{full_url}")
                            if url_status == 200:
                                logging.info('Found 200 status' + full_url)
                                list_200.append(f"200\t{full_url}")
                        except:
                            logging.error('No status ' + full_url)
                            raise
                except:
                    logging.error('Failed session.get(full_url) ' + full_url)
                    raise

    except:
        logging.error(f'Failed async with session')
        raise
    print(f"\n\tREADY:")
    print(f"{list_200}\n\n")
    result_name = domain_name + ".result"
    save_to_file(list_200, "results/" + result_name)
    return list_200  # Do something


async def walk_list():
    try:
        with open("domains.lst") as domain_list:
            time_start = time.perf_counter()
            for domain in domain_list:
                domain_name = domain.strip()
                try:
                    await get_lines(100, domain_name)
                except:
                    pass
            time_done = time.perf_counter()
            print(f'Total time elapsed: {time_done - time_start:0.2f} seconds.')
    except:
        logging.error(f"walk_list error")
        pass


try:
    asyncio.run((walk_list()), debug=True)
except:
    ('some error here? ')
    raise
