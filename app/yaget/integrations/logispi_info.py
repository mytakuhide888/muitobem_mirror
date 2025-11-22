# -*- coding:utf-8 -*-
import time
import sys, codecs

import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import datetime
import re
import lxml.html
#import logging
import requests
import logging.config
import traceback
from time import sleep
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.models import YaBuyersItemList, YaBuyersItemDetail, WowmaCatTagOyaList, WowmaTagChildList
from yaget.integrations.wowma_access import WowmaAccess
import selenium
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/ya_buyers_list_logging.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

#logger.setLevel(20)

# 共通変数
mydwsrc_dir = "/app/yaget/yabuyers/dwsrc"
mydwimg_dir = "/app/yaget/yabuyers/dwimg/"
myupdcsv_dir = "/app/yaget/yabuyers/updcsv/"

UPLOAD_DIR = '/app/yaget/wowma_buyers/dwcsv/'
DONE_CSV_DIR = '/app/yaget/wowma_buyers/donecsv/'
USER_DATA_DIR = '/app/yaget/wowma_buyers/userdata/'

def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class LogispiInfo(object):
    def __init__(self, logger):
        self.logger = logger
        help = 'get logispi_info'
        self.logger.info('logispi_info in. init')
        self.common_chrome_driver = None
        self.upd_csv = []
        self.wowma_access = WowmaAccess(self.logger)
        self.bubrandinfo_obj = BuyersBrandInfo(self.logger)

    # 指定されたURLをリクエスト
    def _get_page_no_tor(self, url):
        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                self.common_chrome_driver.driver.get(url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.info(traceback.format_exc())
                self.logger.info('webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                sleep(3)
            else:
                break

    # ロジスピにログインしておく
    # ※　common_chrome_driver　の初期化はここでやってるので、バッチ呼び出しの場合は必ずこれを呼ぶこと
    def login_logispi(self):
        try:
            self.logger.info('login_logispi start.')

            self.common_chrome_driver = CommonChromeDriver(self.logger)
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)

            # ロジスピのtopページ
            start_url = 'https://logisp-production.web.app/'
            self._get_page_no_tor(start_url)
            sleep(3)

            # ログインページにログイン情報入力
            user_email = 'kuurie7@gmail.com'
            user_pw = 'Maropi888'
            # self.common_chrome_driver.driver.find_element_by_id("id").send_keys(user_email)
            self.common_chrome_driver.driver.execute_script('document.getElementsByName("email")[0].value="%s";' % user_email)
            self.common_chrome_driver.driver.execute_script('document.getElementsByName("password")[0].value="%s";' % user_pw)
            self.common_chrome_driver.driver.find_element_by_name("email").submit()

            # self.common_chrome_driver.driver.execute_script("login_check()")
            sleep(5)

            # ページ遷移したかどうか
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_login.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()

            self.logger.info('login_logispi end.')

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("ロジスピのログインに失敗しました。")

        return True

    # ロジスピの商品詳細ページに遷移して、カートに一つ入れる。要ログイン済みであること
    """
    shop_info_list:
        "shop_name": shop_info.shop_name,
        "from_name": shop_info.from_name,
        "from_name_kana": shop_info.from_name_kana,
        "from_postcode": shop_info.from_postcode,
        "from_state": shop_info.from_state,
        "from_address_1": shop_info.from_address_1,
        "from_address_2": shop_info.from_address_2,
        "from_phone": shop_info.from_phone,
        "mail": shop_info.mail,

    order_receiver_list
        "sender_name": wow_order.sender_name,
        "sender_kana": wow_order.sender_kana,
        "sender_zipcode": wow_order.sender_zipcode,
        "sender_address": wow_order.sender_address,
        "sender_phone_number_1": wow_order.sender_phone_number_1,
        "sender_phone_number_2": wow_order.sender_phone_number_2,

    payment_method
        (0, 'ポイント支払い'), (1, 'au pay'), (2, 'クレジットカード'), (3, 'ゆうちょ振り込み')
    """
    def get_buyers_detail_page(self, detail_url, shop_info_list, order_receiver_list, payment_method):
        try:
            self.logger.info('get_buyers_detail_page start.')

            #self.common_chrome_driver = CommonChromeDriver(self.logger)
            #self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)

            # ロジスピの詳細ページをロード
            self._get_page_no_tor(detail_url)

            # カートに入れるを押す
            sleep(3)
            self.common_chrome_driver.driver.execute_script("send('','')")
            self.logger.info(' カートに入れる ok')

            # バスケットに入ったら購入を続けるボタンを押下
            sleep(3)
            self.common_chrome_driver.driver.execute_script("sslorder()")
            self.logger.info(' 購入ボタンを押す ok')

            # 確認ページ
            # 以下は aupay の選択。もしポイント払いを増やすなら　payment_method　をチェックすること
            sleep(5)
            #self.logger.info(' 購入ページ[{}]'.format(str(self.common_chrome_driver.driver.page_source)))
            payment_total = str(self.common_chrome_driver.driver.find_element_by_xpath(
                "//p[@class='basketTotalPrice']").text).replace(',','').replace('円','')
            self.logger.info(' 購入価格[{}]'.format(payment_total))
            # 確認ページで順次入力していく

            self.common_chrome_driver.driver.find_element_by_id("sender_name").clear()

            self.logger.info(' sender[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_name").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_name").send_keys(shop_info_list['from_name'])

            self.logger.info(' sender[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_name").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_kana").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_kana").send_keys(shop_info_list['from_name_kana'])

            self.logger.info(' sender_kana[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_kana").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_1").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_1").send_keys(
                shop_info_list['from_phone'].split('-')[0])

            self.logger.info(' sender_tel1_1[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_tel1_1").get_attribute('value'))
            )

            sleep(1)

            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_2").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_2").send_keys(
                shop_info_list['from_phone'].split('-')[1])

            self.logger.info(' sender_tel1_2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_tel1_2").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_3").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_3").send_keys(
                shop_info_list['from_phone'].split('-')[2])

            self.logger.info(' sender_tel1_3[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_tel1_3").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_email").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_email").send_keys(shop_info_list['mail'])

            self.logger.info(' sender_email[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_email").get_attribute('value'))
            )

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("sender_post").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_post").send_keys(
                shop_info_list['from_postcode'].replace('-',''))

            self.logger.info(' sender_post[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_post").get_attribute('value'))
            )

            #self.common_chrome_driver.driver.find_element_by_id("sender_area").clear()
            #self.common_chrome_driver.driver.find_element_by_id("sender_area").send_keys(shop_info_list['from_state'])
            sender_area = self.common_chrome_driver.driver.find_element_by_id("sender_area")
            select_sender_area = Select(sender_area)
            select_sender_area.select_by_visible_text(shop_info_list['from_state'])

            self.logger.info(' sender_area[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_area").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_addr").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_addr").send_keys(shop_info_list['from_address_1'])

            self.logger.info(' sender_addr[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_addr").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_addr2").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_addr2").send_keys(shop_info_list['from_address_2'])

            self.logger.info(' sender_addr2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_addr2").get_attribute('value'))
            )

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("receiver_user_type_N").click()
            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("receiver_name").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_name").send_keys(order_receiver_list['sender_name'])
            self.common_chrome_driver.driver.find_element_by_id("receiver_kana").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_kana").send_keys(order_receiver_list['sender_kana'])

            self.logger.info(' receiver_name[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_name").get_attribute('value'))
            )
            self.logger.info(' receiver_kana[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_kana").get_attribute('value'))
            )


            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_1").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_1").send_keys(
                order_receiver_list['sender_phone_number_1'].split('-')[0])

            self.logger.info(' receiver_tel_1[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_tel_1").get_attribute('value'))
            )

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_2").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_2").send_keys(
                order_receiver_list['sender_phone_number_1'].split('-')[1])

            self.logger.info(' receiver_tel_2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_tel_2").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_3").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_3").send_keys(
                order_receiver_list['sender_phone_number_1'].split('-')[2])

            self.logger.info(' receiver_tel_3[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_tel_3").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("receiver_post").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_post").send_keys(
                order_receiver_list['sender_zipcode'].replace('-',''))

            self.logger.info(' receiver_post[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_post").get_attribute('value'))
            )


            #self.common_chrome_driver.driver.find_element_by_id("receiver_area").clear()
            #self.common_chrome_driver.driver.find_element_by_id("receiver_area").send_keys(
            #    order_receiver_list['sender_address'].split(' ')[0])
            receiver_area = self.common_chrome_driver.driver.find_element_by_id("receiver_area")
            select_receiver_area = Select(receiver_area)

            # 東京都だったら、23区かそうじゃないかを選ばないといけない
            tmp_rec_area = order_receiver_list['sender_address'].split(' ')[0]
            tmp_rec_sub_area = order_receiver_list['sender_address'].split(' ')[1] # 区を抽出したい

            if tmp_rec_area == '東京都':
                tokyo_area = ['足立区','墨田区','荒川区','世田谷区','板橋区','台東区','江戸川区','千代田区','大田区',
                              '中央区','葛飾区','豊島区','北区','中野区','江東区','練馬区','品川区','文京区','渋谷区',
                              '港区','新宿区','目黒区','杉並区']
                for tmp_area in tokyo_area:
                    if tmp_area in tmp_rec_sub_area:
                        tmp_rec_area = '東京(23区内)'
                if tmp_rec_area == '東京都': # 23区内じゃなければ23区外に
                    tmp_rec_area = '東京(23区外)'

            #select_receiver_area.select_by_visible_text(order_receiver_list['sender_address'].split(' ')[0])
            select_receiver_area.select_by_visible_text(tmp_rec_area)

            self.logger.info(' receiver_area[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_area").get_attribute('value'))
            )

            my_tmp_list = order_receiver_list['sender_address'].split(' ')
            for i, my_tmp in enumerate(my_tmp_list):
                self.logger.info(' tmp[{}][{}]'.format(i,my_tmp))

            my_receiver_addr = ''
            my_receiver_addr_2 = '　'

            # split(' ')[1] が空文字の場合は、[2]以降を持ってくる
            tmp_flg = 0
            for i, my_tmp in enumerate(my_tmp_list):
                if len(my_tmp_list) > 2:
                    if i == 1 and my_tmp == '':
                        tmp_flg = 1
                    if tmp_flg == 0 and i == 1:
                        my_receiver_addr = my_tmp
                    if tmp_flg == 0 and i > 1:
                        my_receiver_addr_2 += my_tmp + ' '
                    if tmp_flg == 1 and i == 2:
                        my_receiver_addr = my_tmp
                    if tmp_flg == 1 and i > 2:
                        my_receiver_addr_2 += my_tmp + ' '
                else:
                    if i == 1:
                        my_receiver_addr = my_tmp
                    my_receiver_addr_2 = '　'

            self.common_chrome_driver.driver.find_element_by_id("receiver_addr").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_addr").send_keys(my_receiver_addr)
            #order_receiver_list['sender_address'].split(' ')[1])

            self.logger.info(' receiver_addr[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").send_keys(my_receiver_addr_2)

            """
            if len(order_receiver_list['sender_address'].split(' ')) > 2:
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").clear()
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").send_keys(
                    order_receiver_list['sender_address'].split(' ')[2])
            else:
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").clear()
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").send_keys('-')
            """

            sleep(1)
            self.logger.info(' receiver_addr2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").get_attribute('value'))
            )

            # raise Exception
            # ページ遷移したかどうか
            """
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_detail_1.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()
            """
            self.common_chrome_driver.driver.execute_script("send();") # 次ページへ
            #self.common_chrome_driver.driver.find_element_by_name("next_step_button").click()

            sleep(7)

            # 確認ページに来たはず
            # ページ遷移したかどうか
            """
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_detail_kakunin.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()
            """

            #self.logger.info(' 確認ページ[{}]'.format(str(self.common_chrome_driver.driver.page_source)))
            self.logger.info(' 確認ページに遷移した')

            # 確認ページにて
            """
            self.logger.info('kakunin_total:[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_class_name('totalPriceItems-price').value))
            """

            # self.common_chrome_driver.driver.find_element_by_class_name('basketTotalMesseage').text))

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_name("paymethod").click()
            sleep(1)

            self.common_chrome_driver.driver.execute_script("send();") # 次ページへ
            sleep(5)

            # 最終確認画面
            self.logger.info('kakunin_total_最終:[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_class_name('basketTotalTax').text))

            # nextStep(); を押せば注文確定。
            self.common_chrome_driver.driver.execute_script("nextStep();")
            # ロジスピの発注番号と購入価格を取得して返却する class名とかは要確認！
            return self.common_chrome_driver.driver.find_element_by_class_name('large_font_size').text, payment_total

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("ロジスピの商品詳細ページアクセスに失敗しました。url:[{}]".format(detail_url))

        # うまくいけばここには来ないが
        return False
