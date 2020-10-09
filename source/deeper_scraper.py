# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 16:30:55 2019

@author: Aleh
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import InvalidSessionIdException
from urllib.request import urlretrieve
from collections import defaultdict
import sys
import os
import time
import codecs
import shutil
import glob
import json
import traceback
import re
import random

timeout_sec = 2

def try_n_times(functor, n, pause_s = 0):
    for _ in range(n):
        try:
            functor()
            break
        except Exception as ex:
            print(f"Exception: {ex!r}")
            time.sleep(pause_s)


def save_html(html, file_path):
    with codecs.open(file_path, "w", "utf-8") as file_object:
        file_object.write(html)


def file_name_from_url(url):
    return url.split('/')[-1].split('?')[0]


def check_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"'{path}' is created")


def wait_for_js(driver):
    wait = WebDriverWait(driver, timeout_sec)
    try:
        wait.until(lambda driver: driver.execute_script('return jQuery.active') == 0)
        #print("jQuery.active == 0")
    except Exception:
        pass
    try:
        wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
        #print("document.readyState == complete")
    except Exception:
        pass


lansky_studios_short_and_names = {'d': 'deeper', 't': 'tushy', 'v': 'vixen', 'b': 'blacked', 'br': 'blackedraw', 'tr': 'tushyraw'}
lansky_studios = list(lansky_studios_short_and_names.values())
free_demo_studios = ['deeper', 'tushyraw']
autoplay_postfix = "?autoplay=true"
geckodriver_path = 'geckodriver.exe'


def scrap_model(driver, model_url, models_dir):
    model_name = model_url.split('/')[-1]
    model_dir = f"{models_dir}/{model_name}"
    model_html_file_path = f"{model_dir}/{model_name}.html"
    check_directory(model_dir)
    if os.path.exists(model_html_file_path):
        return
    driver.get(model_url)
    wait_for_js(driver)
    time.sleep(timeout_sec)

    images = driver.find_elements_by_xpath("//div[@data-test-component='ProgressiveImage']")
    for image in images:
        image_url = image.find_element_by_tag_name('img').get_attribute('src')
        if not image_url:
            continue
        file_name = file_name_from_url(image_url)
        urlretrieve(image_url, f"{model_dir}/{file_name}")
        print(file_name, 'is saved')

    save_html(driver.page_source, model_html_file_path)


def process_video_url(driver, href, videos_dir, studio_name, force = False):
    video_dir = os.path.join(videos_dir, file_name_from_url(href))
    is_already_filled = False
    is_images_filled = os.path.exists(f"{video_dir}/images/05.jpg") and os.path.exists(f"{video_dir}/images/07.jpg") and \
        os.path.exists(f"{video_dir}/images/02.jpg") and os.path.exists(f"{video_dir}/images/06.jpg")
    if glob.glob(video_dir + '/*.mp4') and is_images_filled and \
        os.path.exists(f"{video_dir}/video.json") and os.path.exists(f"{video_dir}/video.html"):
        print(f"'{video_dir}' was already filled")
        is_already_filled = True
        if not force:
            return 'already filled'

    check_directory(video_dir)
    vid_url = href + [autoplay_postfix, ''][href.endswith(autoplay_postfix)]
    driver.get(vid_url)
    wait_for_js(driver)
    time.sleep(timeout_sec)

    save_html(driver.page_source, f"{video_dir}/video.html")

    def parse_metadata():
        scripts = driver.find_elements_by_tag_name('script')
        for script in scripts:
            if 'window.__INITIAL_STATE__' in script.get_attribute('innerHTML'):
                inner_state_script = script.get_attribute('innerHTML').strip()
                #inner_json = json.loads(inner_state_script[27:-1]) # doesn't work anymore
                if not inner_state_script.count('{'):
                    continue
                inner_json = json.loads(inner_state_script[inner_state_script.index('{'):].split(';')[0])
                for video in inner_json['videos']:
                    if 'chapters' in video:
                        print('\n------------------------------------------------')
                        try:
                            print(video['modelsSpaced'], '-', video['title'], 'by', video['directorNames'])
                            print(video['description'])
                            print(video['tags'])
                        except Exception as ex:
                            print(f"Exception: {ex!r}")
                            print(video.keys())
                        print('------------------------------------------------\n')
                        with open(f"{video_dir}/video.json", "w") as out_file:
                            json.dump(video, out_file, indent=4, sort_keys=True)
                        break
                break
    try:
        parse_metadata()
    except Exception as ex:
        print(f"Exception: {ex!r}")
        traceback.print_exc(file=sys.stdout)

    buttons = driver.find_elements_by_tag_name('button')
    if not buttons:
        print('buttons not found')
    is_video_found = False
    div_play = driver.find_element_by_xpath('//div[@data-test-component="PlayButton"]')
    if div_play:
        try_n_times(lambda: div_play.click(), n=5, pause_s=1)
    for button in buttons:
        if button.get_attribute('title') == "Quality":
            try_n_times(lambda: button.click(), n=10, pause_s=1)
            time.sleep(1)
            lis = driver.find_elements_by_tag_name('li')
            for li in lis:
                is_video_found = True
                #print(li.get_attribute('innerHTML'))
                if '1080p' in li.get_attribute('innerHTML'):
                    try_n_times(lambda: li.click(), n=5, pause_s=1)
                    time.sleep(1)
                    videos = driver.find_elements_by_tag_name('video')
                    for video in videos:
                        vid_url = video.get_attribute('src')
                        if '1080P.mp4' in vid_url:
                            vid_name = vid_url.split('/')[-1].split('?')[0]
                            save_path = f"{video_dir}/{vid_name}"

                            save_path_old = f"{videos_dir}/{vid_name}"                  # migration
                            if os.path.exists(save_path_old):                           # migration
                                shutil.move(save_path_old, save_path)                   # migration
                            if os.path.exists(save_path_old.split('.')[0] + '.html'):   # migration
                                os.remove(save_path_old.split('.')[0] + '.html')        # migration
                            if os.path.exists(save_path.split('.')[0] + '.html'):       # migration
                                os.remove(save_path.split('.')[0] + '.html')            # migration


                            if os.path.exists(save_path):
                                print(f"{save_path} was already downloaded")
                            else:
                                driver.get(href) # just to prevent double video loading
                                urlretrieve(vid_url, save_path)
                                print(f"{save_path} is downloaded")
                            break


                    break
            break
    if not is_video_found:
        print(f"Warning! Failed to play video {href}")
        if is_already_filled:
            return True

    def scrap_images():
        images_dir = f"{video_dir}/images"
        check_directory(images_dir)

        main_landscape_url = driver.find_element_by_xpath("//div[@data-test-component='VideoCoverWrapper']").\
            find_element_by_tag_name('img').get_attribute('src')
        file_name = file_name_from_url(main_landscape_url)
        urlretrieve(main_landscape_url, f"{images_dir}/{file_name}")
        print(file_name, 'is saved')

        driver.find_element_by_xpath("//div[@class='swiper-wrapper']").find_element_by_tag_name('img').click()
        time.sleep(timeout_sec)

        images = driver.find_elements_by_xpath("//div[@class='pswp__item']")
        image_url_format = None
        for image in images:
            if not image:
                continue
            image_url = image.find_element_by_tag_name('img').get_attribute('src')
            if '01.jpg' in image_url:
                image_url_format = image_url.replace('01.jpg', '0{}.jpg')
                break

        retrieving_failed = False
        if image_url_format:
            for i in range(8):
                image_url = image_url_format.format(i+1)
                file_name = file_name_from_url(image_url)
                try:
                    urlretrieve(image_url, f"{images_dir}/{file_name}")
                    print(file_name, 'is saved')
                except Exception:
                    retrieving_failed = True
                    print(image_url, 'is failed')

        if retrieving_failed or not image_url_format:
            for i in range(0, 8, 3):
                driver.get(href)
                wait_for_js(driver)
                time.sleep(1)
                try:
                    element = driver.find_element_by_xpath("//div[@class='swiper-wrapper']").find_elements_by_tag_name('img')[i]
                    driver.execute_script("arguments[0].click();", element);
                    for _ in range(50): # try a few times
                        try:
                            imgs = driver.find_elements_by_xpath("//img[@class='pswp__img']")
                            if not imgs:
                                time.sleep(_ * .001)
                                continue
                            for img in imgs:
                                driver.execute_script("window.stop();")
                                image_url = img.get_attribute('src')
                                file_name = file_name_from_url(image_url)
                                urlretrieve(image_url, f"{images_dir}/{file_name}")
                                print(file_name, 'is saved')
                            break
                        except Exception:
                            print("failed #", _)
                    if 'members.' in driver.current_url:
                        print('redirected to', driver.current_url)
                        break
                except Exception:
                    print(f'failed to click image #{i+1}')

    models = driver.find_element_by_xpath("//div[@data-test-component='VideoModels']").\
        find_elements_by_tag_name('a')
    model_urls = [m.get_attribute('href') for m in models]

    if not is_images_filled:
        try:
            scrap_images()
        except Exception as ex:
            print(f"Failed to scrap images: {ex!r}")
            traceback.print_exc(file=sys.stdout)

    models_dir = f"{os.path.dirname(videos_dir)}/models"
    for model_url in model_urls:
        scrap_model(driver, model_url, models_dir)
    return is_video_found


def scraping_recent_lansky(lansky_studios):
    driver = webdriver.Firefox(executable_path = geckodriver_path)
    driver.set_page_load_timeout(20)
    driver.minimize_window()

    print('\nscraping recent lansky videos...')
    
    exception = None
    
    try:
        for studio_name in lansky_studios:
            main_page = f'https://www.{studio_name}.com'
            base_dir = f'{studio_name}_content'
    
            videos_dir = f"{base_dir}/videos"
            check_directory(videos_dir)
    
            driver.get(main_page)
            clock_next = None
            for _ in range(3): # try a few times
                try:
                    clock_next = driver.find_elements_by_xpath("//p[@data-test-component='ClockDateTitle']")
                    break
                except InvalidSessionIdException as ex:
                    exception = ex
                    break
                except Exception as ex:
                    print(f"Error during ClockDateTitle search ({studio_name}): {ex!r}")
                    time.sleep(timeout_sec)
            if clock_next:
                print(f"watch next on {main_page} at {clock_next[0].get_attribute('innerHTML')}")
            else:
                divs_below_model_list = driver.find_elements_by_xpath("//div[@data-test-component='ModelList']/following-sibling::div")
                for potential_footer_video in divs_below_model_list:
                    if potential_footer_video.find_elements_by_tag_name('h2') and potential_footer_video.find_elements_by_tag_name('a'):
                        href = potential_footer_video.find_element_by_tag_name('a').get_attribute('href')
                        if not 'members.' in href:
                            print('newest scene:', href)
                            process_video_url(driver, href, videos_dir, studio_name, force=False)
                            break
                        else:
                            continue
    
            hero = driver.find_elements_by_xpath("//div[@data-test-component='VideoHero']")
            if hero and hero[0].find_elements_by_tag_name('a'):
                href = hero[0].find_element_by_tag_name('a').get_attribute('href')
                if not 'members.' in href:
                    print('hero scene:', href)
                    process_video_url(driver, href, videos_dir, studio_name, force=False)
    except Exception as ex:
        print(f"Exception: {ex!r}")
        traceback.print_exc(file=sys.stdout)
        
    driver.quit()
    if exception:
        raise exception


cache_failed_video_refs = []
first_time_scraping_older_lansky = True
already_processed_pages_by_studio = defaultdict(list)

def scraping_older_lansky(lansky_studios):
    global first_time_scraping_older_lansky
    driver = webdriver.Firefox(executable_path = geckodriver_path)
    driver.set_page_load_timeout(20)
    driver.minimize_window()
    
    print('\nscraping older lansky videos...')
    
    success = True
    fails_count = 0
    exception = None
    
    try:
        for studio_name in list(lansky_studios):
            main_page = f'https://www.{studio_name}.com'
            base_dir = f'{studio_name}_content'
    
            videos_dir = f"{base_dir}/videos"
            check_directory(videos_dir)
    
            fails_count = 0
            page, last_page = 1, 100
            while page <= last_page:
                if page in already_processed_pages_by_studio[studio_name]:
                    page += 1
                    continue
                try:
                    url = f'{main_page}/videos?page={page}&size=12'
                    driver.get(url)
                    wait_for_js(driver)
                    time.sleep(timeout_sec)
    
                    if page == 1:
                        last_ref = driver.find_element_by_xpath("//a[@data-test-component='PaginationLast']").get_attribute('href')
                        last_page = int(re.search('page=(\d+)', last_ref).group(1))
                        print(f"{studio_name} page count is {last_page}")
    
                    save_html(driver.page_source, f"{videos_dir}/videos{page}.html")
                    vid_containers = driver.find_elements_by_xpath(f"//div[@data-test-component='VideoThumbnailContainer']")
                    refs = [container.find_element_by_tag_name('a').get_attribute('href') for container in vid_containers]
                    if not refs:
                        break
                    already_filled_number = 0
                    already_processed_number = 0
                    for ref in refs:
                        already_processed_number += 1
                        if ref in cache_failed_video_refs:
          
                            success = False
                            continue
                        is_ok = process_video_url(driver, ref, videos_dir, studio_name, force=False)
                        if not is_ok:
                            success = False
                            fails_count += 1
                            cache_failed_video_refs.append(ref)
                            if first_time_scraping_older_lansky:
                                break
                        already_filled_number += (is_ok == 'already filled')
                    if len(refs) == already_processed_number:
                        already_processed_pages_by_studio[studio_name].append(page)
                    if len(refs) == already_filled_number and first_time_scraping_older_lansky:
                        page += random.randint(0, 4)
                        
                    if fails_count > 2:
                        print(f"{studio_name}: too many fails, move on")
                        break
                    
                    page += 1
                except InvalidSessionIdException as ex:
                    exception = ex
                    break
                except Exception as ex:
                    print(f"Exception during processing page #{page} of {studio_name}: {ex!r}")
                    traceback.print_exc(file=sys.stdout)
                    fails_count += 1
            if not fails_count:
                if success:
                    print(f"{studio_name} is successfuly scrapped!")
                lansky_studios.remove(studio_name)
            if exception:
                break
    except Exception as ex:
        print(f"Exception: {ex!r}")
        traceback.print_exc(file=sys.stdout)
        
    driver.quit()
    first_time_scraping_older_lansky = False
    if exception:
        raise exception
    return success


def main():
    try:
        global lansky_studios
        studios_str = input(f'What studios should be scraped: \'all\' or some combination of {list(lansky_studios_short_and_names.keys())}\n')
        if not studios_str or studios_str.lower() == 'all':
            pass
        else:
            lansky_studios = [lansky_studios_short_and_names[s] for s in studios_str.split() if s in lansky_studios_short_and_names]
        print(f'{lansky_studios} will be scraped')


        scraping_recent_lansky(lansky_studios)
        
        while not scraping_older_lansky(lansky_studios):
            random.shuffle(lansky_studios)

    except Exception as ex:
        print(f"Exception: {ex!r}")
        traceback.print_exc(file=sys.stdout)
    else:
        if not cache_failed_video_refs:
            print("success")
        else:
            print(f"failed to scrap: {cache_failed_video_refs}")

    print('finished')
    


if __name__ == '__main__':
    main()

