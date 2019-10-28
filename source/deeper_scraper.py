# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 16:30:55 2019

@author: Aleh
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import sys
import os
import time
from urllib.request import urlretrieve
import codecs

timeout_sec = 5

def save_html(html, file_path):
    with codecs.open(file_path, "w", "utf-8") as file_object:
        file_object.write(html)

def wait_for_js(driver):
    wait = WebDriverWait(driver, timeout_sec)
    try:
        wait.until(lambda driver: driver.execute_script('return jQuery.active') == 0)
        print("jQuery.active == 0")
    except:
        pass
    try:
        wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
        print("document.readyState == complete")
    except:
        pass

main_page = 'https://www.deeper.com'
autoplay_postfix = "?autoplay=true"
geckodriver_path = 'geckodriver.exe'
base_dir = 'deeper_content'

driver = webdriver.Firefox(executable_path = geckodriver_path)
driver.set_page_load_timeout(50)
driver.maximize_window()

try:
    videos_dir = f"{base_dir}/videos"
    if not os.path.exists(videos_dir):
        os.makedirs(videos_dir)
    for page in range(1, 100): # TODO: take max page from the web
        url = f'{main_page}/videos?page={page}&size=12'
        driver.get(url)
        wait_for_js(driver)
        time.sleep(timeout_sec)
        save_html(driver.page_source, f"{videos_dir}/videos{page}.html")
        vid_containers = driver.find_elements_by_xpath(f"//div[@data-test-component='VideoThumbnailContainer']")
        refs = [container.find_element_by_tag_name('a').get_attribute('href') for container in vid_containers]
        if not refs:
            break
        for href in refs:
            vid_url = href + autoplay_postfix
            driver.get(vid_url)
            wait_for_js(driver)
            time.sleep(timeout_sec)
            buttons = driver.find_elements_by_tag_name('button')
            for button in buttons:
                if button.get_attribute('title') == "Quality":
                    button.click()
                    time.sleep(1)
                    lis = driver.find_elements_by_tag_name('li')
                    for li in lis:
                        #print(li.get_attribute('innerHTML'))
                        if '1080p' in li.get_attribute('innerHTML'):
                            li.click()
                            time.sleep(1)
                            videos = driver.find_elements_by_tag_name('video')
                            for video in videos:
                                vid_url = video.get_attribute('src')
                                if '1080P.mp4' in vid_url:
                                    vid_name = vid_url.split('/')[-1].split('?')[0]
                                    save_path = f"{videos_dir}/{vid_name}"
                                    save_html(driver.page_source, save_path.split('.')[0] + '.html')
                                    if os.path.exists(save_path):
                                        print(f"{save_path} was already downloaded")
                                    else:
                                        urlretrieve(vid_url, save_path)
                                        print(f"{save_path} is downloaded")
                                    break


                            break
                    break
except:
    print(sys.exc_info()[0])
else:
    print("success")

print('finished')
driver.quit()