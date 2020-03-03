# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 16:30:55 2019

@author: Aleh
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from urllib.request import urlretrieve
import sys
import os
import time
import codecs
import shutil
import glob
import json
import traceback
import re

timeout_sec = 2


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
    if (glob.glob(video_dir + '/*.mp4') or not studio_name in free_demo_studios) and \
        os.path.exists(f"{video_dir}/video.json") and os.path.exists(f"{video_dir}/video.html") and \
        os.path.exists(f"{video_dir}/images/05.jpg") and os.path.exists(f"{video_dir}/images/07.jpg") and \
        os.path.exists(f"{video_dir}/images/02.jpg") and os.path.exists(f"{video_dir}/images/06.jpg"):
        print(f"'{video_dir}' was already filled")
        if not force:
            return

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
                inner_json = json.loads(inner_state_script[inner_state_script.index('{'):].split(';')[0])
                for video in inner_json['videos']:
                    if 'chapters' in video:
                        print('\n------------------------------------------------')
                        print(video['modelsSpaced'], '-', video['title'], 'by', video['directorNames'])
                        print(video['description'])
                        print(video['tags'])
                        print('------------------------------------------------\n')
                        with open(f"{video_dir}/video.json", "w") as out_file:
                            json.dump(video, out_file, indent=4, sort_keys=True)
                        break
                break
    parse_metadata()

    buttons = driver.find_elements_by_tag_name('button')
    for button in buttons:
        if button.get_attribute('title') == "Quality":

            for i in range(10):
                try:
                    button.click()
                    break
                except Exception as ex:
                    print(f"button.click() error: {ex!r}")
                    time.sleep(1)

            time.sleep(1)
            lis = driver.find_elements_by_tag_name('li')
            for li in lis:
                #print(li.get_attribute('innerHTML'))
                if '1080p' in li.get_attribute('innerHTML'):
                    try:
                        li.click()
                    except Exception:
                        time.sleep(1)
                        li.click() # try one more time
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
                        except Exception:
                            print("failed #", _)
                        else:
                            break
                    if 'members.' in driver.current_url:
                        print('redirected to', driver.current_url)
                        break
                except Exception:
                    print(f'failed to click image #{i+1}')

    models = driver.find_element_by_xpath("//div[@data-test-component='VideoModels']").\
        find_elements_by_tag_name('a')
    model_urls = [m.get_attribute('href') for m in models]

    scrap_images()

    models_dir = f"{os.path.dirname(videos_dir)}/models"
    for model_url in model_urls:
        scrap_model(driver, model_url, models_dir)


def main():
    try:
        global lansky_studios
        studios_str = input(f'What studios should be scraped: \'all\' or some combination of {list(lansky_studios_short_and_names.keys())}\n')
        if not studios_str or studios_str.lower() == 'all':
            pass
        else:
            lansky_studios = []
            for s in studios_str.split():
                if s in lansky_studios_short_and_names:
                    lansky_studios.append(lansky_studios_short_and_names[s])
        print(f'{lansky_studios} will be scraped')


        driver = webdriver.Firefox(executable_path = geckodriver_path)
        driver.set_page_load_timeout(20)
        driver.minimize_window()

        print('\nscraping recent lansky videos...')
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
                except Exception as ex:
                    print(f"Error during ClockDateTitle search ({studio_name}): {ex!r}")
                    time.sleep(timeout_sec)
                else:
                    break
            if clock_next:
                print(f"watch next on {main_page} at {clock_next[0].get_attribute('innerHTML')}")
            else:
                footer_video = driver.find_elements_by_xpath("//div[@data-test-component='ModelList']/following-sibling::div")
                if footer_video and footer_video[0].find_elements_by_tag_name('a'):
                    href = footer_video[0].find_element_by_tag_name('a').get_attribute('href')
                    if not 'members.' in href:
                        print('newest scene:', href)
                        process_video_url(driver, href, videos_dir, studio_name, force=True)

            hero = driver.find_elements_by_xpath("//div[@data-test-component='VideoHero']")
            if hero and hero[0].find_elements_by_tag_name('a'):
                href = hero[0].find_element_by_tag_name('a').get_attribute('href')
                if not 'members.' in href:
                    print('hero scene:', href)
                    process_video_url(driver, href, videos_dir, studio_name, force=True)

        print('\nscraping older lansky videos...')
        for studio_name in lansky_studios:
            main_page = f'https://www.{studio_name}.com'
            base_dir = f'{studio_name}_content'

            videos_dir = f"{base_dir}/videos"
            check_directory(videos_dir)

            page, last_page = 1, 100
            while page <= last_page:
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
                    for href in refs:
                        process_video_url(driver, href, videos_dir, studio_name)
                    page += 1
                except Exception as ex:
                    print(f"Exception during processing page #{page} of {studio_name}: {ex!r}")
                    traceback.print_exc(file=sys.stdout)

    except Exception as ex:
        print(f"Exception: {ex!r}")
        traceback.print_exc(file=sys.stdout)
    else:
        print("success")

    print('finished')
    driver.quit()


if __name__ == '__main__':
    main()

