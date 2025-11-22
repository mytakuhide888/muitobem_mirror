# -*- coding:utf-8 -*-
import time
import sys, codecs

import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import datetime
import os, socket
from threading import Timer
import random

#import logging
import logging.config
import traceback
from time import sleep
import subprocess

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
# 次にクリックしたページがどんな状態になっているかチェックする
from selenium.webdriver.support import expected_conditions as EC

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
#logging.config.fileConfig(fname="/app/common/log/chrome_driver_logging.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

# 共通変数

def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class CommonChromeDriver(object):
    def __init__(self, logger):
        self.logger = logger
        self.logger.debug(' ===> common_chrome_driver. init')
        self.driver = None

    # 本内容は、test_amsrc_1.py のselenium の使い方にある。

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

    # torリスタート
    def restart_tor(self):
        try:
            # tor をリスタートしてIP切り替える
            args = ['sudo', 'service', 'tor', 'restart']
            subprocess.call(args)
            sleep(1)
            proxies = {
                'http': 'socks5://127.0.0.1:9050',
                'https': 'socks5://127.0.0.1:9050'
            }
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
        return

    # headless chromeをtorセットして初期化する
    def init_chrome_with_tor(self):
        try:
            # まずchromeのごみを消して、httpdリスタートしてみる
            args = ['sudo', 'killall', 'chrome']
            subprocess.call(args)
            #sleep(1)

            args = ['sudo', 'killall', 'chromedriver']
            subprocess.call(args)
            #sleep(1)

            args = ['sudo', 'service', 'nginx', 'restart']
            subprocess.call(args)
            sleep(1)

            # tor をリスタートしてIP切り替える
            args = ['sudo', 'service', 'tor', 'restart']
            subprocess.call(args)
            sleep(1)
            proxies = {
                'http': 'socks5://127.0.0.1:9050',
                'https': 'socks5://127.0.0.1:9050'
            }

            options = Options()

            user_agent = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36 OPR/84.0.4316.14',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
            ]
            UA = user_agent[random.randrange(0, len(user_agent), 1)]
            options.add_argument('--user-agent=' + UA)

            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')
            options.add_argument('--proxy-server=socks5://127.0.0.1:9050')

            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            #self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()

        return

    # headless chromeをtorなしで初期化する
    def init_chrome_with_no_tor(self, user_data_dir):
        try:
            # まずchromeのごみを消して、httpdリスタートしてみる
            args = ['sudo', 'killall', 'chrome']
            subprocess.call(args)
            #sleep(1)

            args = ['sudo', 'killall', 'chromedriver']
            subprocess.call(args)
            #sleep(1)

            args = ['sudo', 'service', 'nginx', 'restart']
            subprocess.call(args)
            sleep(1)

            options = Options()
            user_agent = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36 OPR/84.0.4316.14',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
            ]
            UA = user_agent[random.randrange(0, len(user_agent), 1)]
            options.add_argument('--user-agent=' + UA)
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')
            # ログイン情報保持用にuserプロファイルを保持
            options.add_argument('--user-data-dir=' + user_data_dir)

            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            #self.driver = webdriver.Chrome(chrome_options=options)

            # 初期化時にcookieをクリアしてみる
            self.driver.delete_all_cookies()

        except Exception as e:
            #print(e)
            #print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()

        return

    # headless chromeをcloseする
    def quit_chrome_with_tor(self):
        try:
            # self.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい
            self.driver.quit()  # quitは全ウィンドウを閉じてwebdriverセッションを終了する
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()

        return

    def restart_chrome(self):
        try:
            if self.driver:
                self.driver.quit()  # quitは全ウィンドウを閉じてwebdriverセッションを終了する

            # まずchromeのごみを消して、httpdリスタートしてみる
            args = ['sudo', 'killall', 'chrome']
            subprocess.call(args)
            sleep(1)

            args = ['sudo', 'killall', 'chromedriver']
            subprocess.call(args)
            sleep(1)

            args = ['sudo', 'service', 'nginx', 'restart']
            subprocess.call(args)
            sleep(3)

            # nginx restart
            self.logger.debug('eb_restart_chrome restart nginx')
            #self.force_timeout()
            sleep(1)

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')
            options.add_argument('--proxy-server=socks5://127.0.0.1:9050')

            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            #self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()

        self.logger.debug('eb_restart_chrome end')
        return

    def restart_chrome_no_tor(self, user_data_dir):
        try:
            if self.driver:
                self.driver.quit()  # quitは全ウィンドウを閉じてwebdriverセッションを終了する

            # まずchromeのごみを消して、httpdリスタートしてみる
            args = ['sudo', 'killall', 'chrome']
            subprocess.call(args)
            sleep(1)

            args = ['sudo', 'killall', 'chromedriver']
            subprocess.call(args)
            sleep(1)

            args = ['sudo', 'service', 'nginx', 'restart']
            subprocess.call(args)
            sleep(3)

            # nginx restart
            self.logger.debug('eb_restart_chrome restart nginx')
            #self.force_timeout()
            sleep(1)

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')
            options.add_argument('--user-data-dir=' + user_data_dir)

            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            #self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            #print(e)
            #print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()

        self.logger.debug('eb_restart_chrome end')
        return
