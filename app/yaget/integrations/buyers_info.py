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

class BuyersInfo(object):
    def __init__(self, logger):
        self.logger = logger
        help = 'get from ya buyers list.'
        self.logger.info('buyers_info in. init')
        self.common_chrome_driver = None
        self.upd_csv = []
        self.wowma_access = WowmaAccess(self.logger)
        #self.bubrandinfo_obj = BuyersBrandInfo(self.logger)

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

    # バイヤーズにログインしておく
    # ※　common_chrome_driver　の初期化はここでやってるので、バッチ呼び出しの場合は必ずこれを呼ぶこと
    def login_buyers(self):
        try:
            self.logger.info('login_buyers start.')

            self.common_chrome_driver = CommonChromeDriver(self.logger)
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)


            # バイヤーズのtopページ
            start_url = 'https://buyerz.shop/'
            self._get_page_no_tor(start_url)

            # ログインボタンを押す
            sleep(1)
            self.common_chrome_driver.driver.execute_script("ssl_login('login')")
            sleep(3)

            # ログインページにログイン情報入力
            user_email = 'doublenuts8@gmail.com'
            user_pw = 'NagoY888'
            #self.common_chrome_driver.driver.find_element_by_id("id").send_keys(user_email)
            self.common_chrome_driver.driver.execute_script('document.getElementsByName("id")[0].value="%s";' % user_email)
            self.common_chrome_driver.driver.execute_script('document.getElementsByName("passwd")[0].value="%s";' % user_pw)
            self.common_chrome_driver.driver.execute_script("login_check()")
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

            self.logger.info('login_buyers end.')

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("バイヤーズのログインに失敗しました。")

        return True

    # バイヤースの商品詳細ページに遷移して、カートに一つ入れる。要ログイン済みであること
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

            # バイヤーズの詳細ページをロード
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
            # バイヤーズの発注番号と購入価格を取得して返却する class名とかは要確認！
            return self.common_chrome_driver.driver.find_element_by_class_name('large_font_size').text, payment_total

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("バイヤーズの商品詳細ページアクセスに失敗しました。url:[{}]".format(detail_url))

        # うまくいけばここには来ないが
        return False

    # 出品手数料を考慮して利益の出る価格を算出する。
    def get_benefit_price(self, normal_price, commission):
        benefit_price = 500
        if normal_price < 500:
            benefit_price = 300
        elif 500 <= normal_price < 1000:
            benefit_price = 400
        elif 1000 <= normal_price < 2000:
            benefit_price = 500
        elif 2000 <= normal_price < 3000:
            benefit_price = 500
        elif 3000 <= normal_price < 4000:
            benefit_price = 550
        elif 4000 <= normal_price < 5000:
            benefit_price = 600
        else:
            benefit_price = 800

        return int(round(((int(normal_price) * commission) + benefit_price), -2)) + 80

    # ###################################################################
    # ★★★　各バッチなどからも基本的にこいつを呼び出して登録しよう。★★★
    # 詳細ページにアクセスして、DBに登録がなければ新規登録、あれば最新の情報に更新する。
    # こいつはDBを最新化するだけ。wowma、qoo10の更新はしない
    # ss_url: リンク元リストページURL
    # gsrc: リストーページ中の商品サムネイル画像URL
    def get_wowma_buyers_detail(self, d_url, gid, gcd, ss_url, gsrc, my_ct):
        self.logger.debug('get_wowma_buyers_detail in.')

        # ページ取得
        self._get_page_no_tor(d_url)

        """
        # 詳細ページのソースを保存したければここをON
        tdatetime = dt.now()
        tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
        tfilename = tstr + '_y_src_' + str(pcount) + '.txt'
        tfpath = mydwsrc_dir + '/detail/' + tfilename
        # f = open(tfpath, mode='w')
        f = codecs.open(tfpath, 'w', 'utf-8')

        f.write(self.common_chrome_driver.driver.page_source)
        # f.write(src_1)
        f.close()
        """
        #self.common_chrome_driver.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい

        # 画像リンクを別ウィンドウ呼び出しで格納する
        #dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href'].click() # 拡大画像のポップアップリンク
        #self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").click()
        #self.logger.debug(' popup_href[' + str(dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href']) + ']') # 拡大画像のポップアップリンク
        self.logger.debug(' popup_href[' + str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").get_attribute('href')) + ']')
        self.logger.debug(' popup_href_resub[' + re.sub('javascript:', "", str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").get_attribute('href'))) + ']')
        tmpscriptln = re.sub('javascript:', "", str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").get_attribute('href')))
        # tmpgalt = re.sub('◆新品◆', "", tmpgalt)

        self.logger.debug(' popup_text[' + str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a")) + ']')
        self.common_chrome_driver.driver.execute_script(tmpscriptln)

        sleep(3)

        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            handles = self.common_chrome_driver.driver.window_handles
            if len(handles) == 2:
                break
            else:
                sleep(3)

        self.logger.debug('window handles:len[' + str(len(handles)) + ']')
        #self.common_chrome_driver.driver.switch_to_window(handles[1]) # switch_to_window は古い。switch_to.window が正しい
        self.common_chrome_driver.driver.switch_to.window(handles[1])
        self.logger.debug('source ---' + self.common_chrome_driver.driver.page_source + '---')

        tmpimglist = []
        cnt = 0

        # 画像のurlは20まで登録できるようにする
        # 変数名は動的に
        # 0初期化
        tmp_g_img_src = [""] * 20

        tmp_cnt = 0
        for i in self.common_chrome_driver.driver.find_elements_by_xpath("//div[@id='M_mainImage']/div/img"):
            #self.logger.debug('tmpimgs:len[' + str(len(tmpimgs)) + ']')
            tmpgsrc = i.get_attribute('src')
            self.logger.debug('tmpgsrc[' + str(i) + ']:src[' + str(tmpgsrc) + ']')
            self.logger.info('gid:[' + str(gid) + '] tmpgsrc[' + str(i) + ']:src[' + str(tmpgsrc) + ']')
            tmpimglist.append(tmpgsrc)

            tmp_g_img_src[tmp_cnt] = str(tmpgsrc).rsplit("?", 1)[0]
            #tmp_g_img_src[tmp_cnt] = str(tmpgsrc)
            tmp_cnt += 1

            # 画像保存してみる
            myresponce = requests.get(tmpgsrc)
            if cnt == 0:
                tmpimgfname = str(gid)
            else:
                tmpimgfname = str(gid) + '_' + str(cnt)
            with open(mydwimg_dir + "{}.jpg".format(tmpimgfname), "wb") as myf:
                myf.write(myresponce.content)

            cnt += 1
            if tmp_cnt == 19:
                break

        # 親のウィンドウに戻る
        self.common_chrome_driver.driver.close()
        #self.common_chrome_driver.driver.switch_to_window(handles[0])
        self.common_chrome_driver.driver.switch_to.window(handles[0])

        # 商品詳細の各要素を取得する

        #tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        #tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 商品名
        tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='itemInfo']/h2").text

        try:
            tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/h2").text
        except:
            self.logger.info('get_wowma_buyers_detail no page. gid:[{}]'.format(tmpgid))
            return False

        # 商品詳細
        try:
            tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/div[1]/div").text
        except:
            """
            この場合、商品詳細が取れないことがある
            https://buyerz.shop/shopdetail/000000024392/ct1075/page1/order/

            //div[@id='itemInfo']/div[1]/div
            が通常だが、親の
            //div[@id='itemInfo']/div[1]
            にtextが入ってることが。これはこれで処理するか。
            """
            try:
                tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                    "//div[@id='itemInfo']/div[1]").text
            except:
                # ここまで来て取れなければ、ページが終了していると判断する。
                self.logger.info('get_wowma_buyers_detail maybe no page. 1 gid:[{}]]'.format(tmpgid))
                return False



        # 商品詳細の原文から、変換不能文字だけ変えてしまう
        # 変換する文字。shift-jis変換でコケた文字はここに登録
        # for exchange_words in self.bubrandinfo_obj._MY_EXCHANGE_WORDS:
        
        #for exchange_words in BuyersBrandInfo._MY_EXCHANGE_WORDS:
        #    tmpgdetail = re.sub(exchange_words[0], exchange_words[1], tmpgdetail)

        # =================================
        # 不要文字削除
        ng_flg = 0
        tmpyct_flg = 0
        # 商品名より削除
        tmpgname_obj = None
        tmpgdetail_obj = None

        tmpgname_obj = self.bubrandinfo_obj.chk_goods_title(tmpgname)
        #tmpgname_obj = BuyersBrandInfo.chk_goods_title(tmpgname)

        # wowmaの商品名はひとまずこれにする。
        tmp_wow_gname = self.bubrandinfo_obj.cut_str(tmpgname_obj[0], 100)
        #tmp_wow_gname = BuyersBrandInfo.cut_str(tmpgname_obj[0], 100)

        # 商品名のmaxは100文字とする
        # qoo10の商品名もひとまずこれにする。
        tmp_qoo_gname = self.bubrandinfo_obj.cut_str(tmpgname_obj[0], 100)
        #tmp_qoo_gname = BuyersBrandInfo.cut_str(tmpgname_obj[0], 100)

        if tmpgname_obj[1] == 1:
            ng_flg = 1

        # 不要文字削除
        # 商品説明より削除
        tmp_wow_worn_key = ""  # もし注意文言があればここに格納する
        tmp_qoo_worn_key = ""  # もし注意文言があればここに格納する
        tmpgdetail_obj = self.bubrandinfo_obj.chk_goods_detail(tmpgdetail)
        #tmpgdetail_obj = BuyersBrandInfo.chk_goods_detail(tmpgdetail)

        # wowma は < >をエスケープ
        tmp_wow_gdetail = tmpgdetail_obj[0]
        tmp_wow_gdetail = re.sub('<', '&lt;', tmp_wow_gdetail)
        tmp_wow_gdetail = re.sub('>', '&gt;', tmp_wow_gdetail)

        # qoo10はそのまま
        tmp_qoo_gdetail = tmpgdetail_obj[0]
        if tmpgdetail_obj[1] == 1:
            ng_flg = 1

        if tmpgdetail_obj[1] == 5:
            ng_flg = 1

        if tmpgdetail_obj[1] == 6:
            tmpyct_flg = 6  # NGワードが商品詳細に含まれる、要確認
            if tmpgdetail_obj[2]:
                tmp_wow_worn_key = tmpgdetail_obj[2]
                tmp_qoo_worn_key = tmpgdetail_obj[2]

        # ===============================
        # 通常価格
        tmpgspprice = int(re.sub("\\D", "",
                             self.common_chrome_driver.driver.find_element_by_xpath(
                                 "//li[@id='M_usualValue']/span").text))

        # wowmaの価格を算出
        # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
        tmp_wow_price = self.get_benefit_price(tmpgspprice, 1.15)

        # qoo10の価格を算出
        # qoo10も10%が手数料なので上乗せして、それに利益率を加える。
        # メガ割用に、1.2に
        tmp_qoo_price = self.get_benefit_price(tmpgspprice, 1.3)

        # ===============================
        # 在庫数の抽出
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//span[@class='M_item-stock-smallstock']")) == 0:
            # 在庫が取れないときは在庫切れか
            self.logger.debug('get_wowma_buyers_detail cant get [M_item-stock-smallstock].')
            tmpgretail = "0"
        else:
            tmpgretail = str(re.sub("\\D", "",
                                self.common_chrome_driver.driver.find_element_by_xpath(
                                    "//span[@class='M_item-stock-smallstock']").text))
        # wowmaは、チェック前は未出品にする
        tmp_wow_upd_status = 0  # 未掲載
        tmp_wow_on_flg = 0  # 確認待

        # qooは、チェック前は未出品にする
        tmp_qoo_upd_status = 1  # 取引待機= 1、取引可能= 2、取引廃止= 3）
        tmp_qoo_on_flg = 0  # 確認待

        # もし商品名や商品詳細のチェックでNGになっていたらブラックリスト入にする。
        if ng_flg == 1:
            tmp_wow_on_flg = 2  # NG
            tmp_qoo_on_flg = 2  # NG

        # 2021/1/19 テストのため、ブラックリストのチェックはいったん外して 0 （未出品にする）
        #tmp_wow_on_flg = 0
        #tmp_qoo_on_flg = 0

        tmpgcode = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='detailInfo']/ul/li[4]").text

        # ===================================================
        # カテゴリコード　チェック
        # カテゴリコードはとりあえず一つ。パンくずの末尾をとってみる
        # URL指定した際の、バイヤーズのカテゴリコードは my_ct で渡されている。
        tmpyct, tmpyct_flg, tmpyct_qoo, tmpyct_qoo_flg = self.get_wow_qoo_ctcd(
            my_ct, tmpgname, tmp_wow_gdetail, tmp_qoo_gdetail)

        """
        2021/10/10
        これまでは、パンくずに記載のあるカテゴリから引いてみたが
        URL指定の際に、既に指定されるカテゴリコードをリストと紐付けて一意で取ってみる形に。
        # wowmaのカテゴリチェック
        tmpyct_obj = self.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        tmpyct = tmpyct_obj[0]
        tmpyct_flg = tmpyct_obj[1]
        """


        """
        tmpyct_obj = self.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        if tmpyct_obj:
            if tmpyct_obj[1] == 1:
                # サブカテゴリならそのまま採用
                tmpyct = tmpyct_obj[0]
                tmpyct_flg = 1
            elif tmpyct_obj[1] == 2:
                # 大カテゴリなら次を探索
                tmpyct = tmpyct_obj[0]
                tmpyct_flg = 2
            else:
                # その他カテゴリなら次を探索
                tmpyct = tmpyct_obj[0]
                tmpyct_flg = 3

            self.logger.debug('===> tmpct_obj[0]:[{}]'.format(tmpyct_obj[0]))
            self.logger.debug('===> tmpct_obj[1]:[{}]'.format(tmpyct_obj[1]))

        else:
            tmpyct = ""
            tmpyct_flg = 3

        # qoo10のカテゴリチェック
        tmpyct_qoo_obj = self.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
        tmpyct_qoo = tmpyct_qoo_obj[0]
        tmpyct_qoo_flg = tmpyct_qoo_obj[1]
        """

        """
        tmpyct_qoo_obj = self.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
        if tmpyct_qoo_obj:
            if tmpyct_qoo_obj[1] == 1:
                # サブカテゴリなら採用
                tmpyct_qoo = tmpyct_qoo_obj[0]
                tmpyct_qoo_flg = 1
            elif tmpyct_qoo_obj[1] == 2:
                # 大カテゴリなら次を探索
                tmpyct_qoo = tmpyct_qoo_obj[0]
                tmpyct_qoo_flg = 2
            else:
                # その他カテゴリなら次を探索
                tmpyct_qoo = tmpyct_qoo_obj[0]
                tmpyct_qoo_flg = 3

            self.logger.debug('===> tmpyct_qoo_obj[0]:[{}]'.format(tmpyct_qoo_obj[0]))
            self.logger.debug('===> tmpyct_qoo_obj[1]:[{}]'.format(tmpyct_qoo_obj[1]))

        else:
            tmpyct_qoo = ""
            tmpyct_qoo_flg = 3
        """


        """
        for ii in self.common_chrome_driver.driver.find_elements_by_xpath("//p[@class='pankuzu']/a"):
            # カテゴリ一致するかリスト引いて、マッチしたらそいつをセットしてループは抜ける
            tmpct = ii.get_attribute('href')  # 文字はちゃんと整形して

            self.logger.debug('===> tmpct 1:[{}]'.format(tmpct))

            # index は無視
            if re.search('index', tmpct):
                self.logger.debug('===> tmpct:index hit. continue')
                continue

            tmpct = re.sub('https://buyerz.shop/shopbrand/', "", tmpct)
            tmpct = re.sub('/', "", tmpct)

            self.logger.debug('===> tmpct:[{}]'.format(tmpct))

            # wowmaのカテゴリチェック
            tmpyct_obj = self.buinfo_obj.chk_wow_ct(tmpct, tmpgname)
            if tmpyct_obj:
                if tmpyct_obj[1] == 1:
                    # サブカテゴリなら採用
                    tmpyct = tmpyct_obj[0]
                    tmpyct_flg = 1
                    break
                elif tmpyct_obj[1] == 2:
                    # 大カテゴリなら次を探索
                    tmpyct = tmpyct_obj[0]
                    tmpyct_flg = 2
                else:
                    # その他カテゴリなら次を探索
                    tmpyct = tmpyct_obj[0]
                    tmpyct_flg = 3

                self.logger.debug('===> tmpct_obj[0]:[{}]'.format(tmpyct_obj[0]))
                self.logger.debug('===> tmpct_obj[1]:[{}]'.format(tmpyct_obj[1]))

            else:
                tmpyct = ""
                tmpyct_flg = 3

            # qoo10のカテゴリチェック
            tmpyct_qoo_obj = self.buinfo_obj.chk_qoo_ct(tmpct, tmpgname)
            if tmpyct_qoo_obj:
                if tmpyct_qoo_obj[1] == 1:
                    # サブカテゴリなら採用
                    tmpyct_qoo = tmpyct_qoo_obj[0]
                    tmpyct_qoo_flg = 1
                    break
                elif tmpyct_qoo_obj[1] == 2:
                    # 大カテゴリなら次を探索
                    tmpyct_qoo = tmpyct_qoo_obj[0]
                    tmpyct_qoo_flg = 2
                else:
                    # その他カテゴリなら次を探索
                    tmpyct_qoo = tmpyct_qoo_obj[0]
                    tmpyct_qoo_flg = 3

                self.logger.info('===> tmpyct_qoo_obj[0]:[{}]'.format(tmpyct_qoo_obj[0]))
                self.logger.info('===> tmpyct_qoo_obj[1]:[{}]'.format(tmpyct_qoo_obj[1]))

            else:
                tmpyct_qoo = ""
                tmpyct_qoo_flg = 3
        """

        """
        if tmpyct_flg == 0 or tmpyct_flg == 3:
            tmpyct_key_obj = self.chk_ct_by_keyword_for_wowma(tmpgdetail, tmpgname)
            if tmpyct_key_obj:
                tmpyct = str(tmpyct_key_obj)
                tmpyct_flg = 2

        if tmpyct_qoo_flg == 0 or tmpyct_qoo_flg == 3:
            tmpyct_key_qoo_obj = self.chk_ct_by_keyword_for_qoo(tmpgdetail, tmpgname)
            if tmpyct_key_qoo_obj:
                tmpyct_qoo = str(tmpyct_key_qoo_obj)
                tmpyct_qoo_flg = 2


        # ここでtmpyctが取れてない（""のまま）だったらNGか。
        if tmpyct == "":
            self.logger.info('get_wowma_buyers_detail cant match tmpyct.')
            # self.logger.info('----- > _get_wowma_buyers_detail_for_ecauto cant match tmpyct.')
            # return False
        if tmpyct_qoo == "":
            self.logger.info('get_wowma_buyers_detail cant match tmpyct_qoo.')
        # 2021/1/19 仮に、tmpyct にはwowmaのカテゴリコードを割り当てておく
        #tmpyct = "500501"
        #tmpyct_qoo = "500501"
        """

        # ==========================
        # 配送IDの設定をする
        # 本来は、カテゴリコード設定の際に判定しなければいけないが仮に固定で以下。送料無料
        #tmpdeliveryid = 100003
        #tmp_qoo_deliveryid = 100003
        # バイヤーズの配送コードから、wowmaとqoo10の配送区分（無料かどうか）、配送コードを取得
        # 配送コードは 2(送料無料) か3（個別送料）
        tmp_postage_obj = self.bubrandinfo_obj.get_delivery_info(tmpgname_obj[0])
        tmp_postage_segment = tmp_postage_obj[0]

        tmpdeliveryid = tmp_postage_obj[1]
        tmp_qoo_deliveryid = tmp_postage_obj[2]


        # ==========================
        # 個別送料の判定をする。
        # カテゴリコードをチェックなりして、判断。基本は送料込み。
        # 2021/1/19 今はデフォで送料込み
        #tmp_postage_segment = 2
        tmp_postage = 0

        # qoo10関係  ====================================================================================================
        # 個別送料の判定をする。
        # とりあえず仮
        tmp_qoo_shipping_no = 0  # qoo送料コード 0:送料無料
        tmp_qoo_postage = 0
        tmp_qoo_item_qty = "1"  # 商品数量
        tmp_qoo_adult_yn = "N"  #アダルトフラグ

        # 代表画像
        tmp_qoo_standard_img = tmp_g_img_src[0]

        # 検索キーワード　商品詳細から取れたらいいが今は仮。
        tmp_qoo_keyword = ""

        # アフターサービス情報　今は仮
        tmp_qoo_contact_info = ""

        #self.logger.debug('gid:[' + str(tmpgid) + ']')
        self.logger.debug('d-gid:[' + str(gid) + ']')
        self.logger.debug('d-gname:[' + str(tmpgname) + ']')
        self.logger.debug('d-gdetail:[' + str(tmpgdetail) + ']')
        self.logger.debug('d-gspprice:[' + str(tmpgspprice) + ']')
        self.logger.debug('d-gretail:[' + str(tmpgretail) + ']')
        self.logger.debug('d-gcode:[' + str(tmpgcode) + ']')
        self.logger.debug('d-tmpct:[' + str(my_ct) + ']')

        # qoo10 のqoo販売者コードを設定
        # 販売者コードは、ショップ名とかで付け替えるようにしたいが。
        # [Q][先頭ショップ番号1桁][ショップ名略称3文字 ボアソルテはBOA、YUKIショップは YUK]
        tmp_qoo_seller_code = ''
        tmp_qoo_seller_code_pre = 'Q2YUK'
        tmp_qoo_seller_code_num = 10000001
        tmp_obj_matched = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        #tmp_obj_matched = YaBuyersItemDetail.objects.get(gid=tmpgid)
        if tmp_obj_matched:
            self.logger.debug('chk qoo_seller_code matched')
            # 登録済みの商品だったら
            tmp_qoo_seller_code = tmp_obj_matched.qoo_seller_code
            if tmp_qoo_seller_code:
                # 設定済みならそのまま使う。
                pass
            else:
                # 未設定なら登録済みのコードから探して+1して採番
                tmp_obj_before = YaBuyersItemDetail.objects.order_by("-qoo_seller_code").first()
                if tmp_obj_before:
                    if tmp_obj_before.qoo_seller_code:
                        # すでに入力済みなら
                        tmp_qoo_seller_code_before = int(str(tmp_obj_before.qoo_seller_code)[5:])
                        tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_before + 1)
                    else:
                        # ひっかかるはずだが、ないってことは初番から入れていく
                        tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)
                else:
                    # ひっかかるはずだが、ないってことは初番から入れていく
                    tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)
        else:
            self.logger.info('chk qoo_seller_code un_matched')
            # 未登録ならqoo販売者コードを新規に採番する
            tmp_obj_before = YaBuyersItemDetail.objects.order_by("-qoo_seller_code").first()
            if tmp_obj_before:
                if tmp_obj_before.qoo_seller_code:
                    # すでに入力済みなら
                    tmp_qoo_seller_code_before = int(str(tmp_obj_before.qoo_seller_code)[5:])
                    tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_before + 1)
                else:
                    # ひっかかるはずだが、ないってことは初番から入れていく
                    tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)
            else:
                # ひっかかるはずだが、ないってことは初番から入れていく
                tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)

        # 検索キーワードをそれぞれ設定
        tmp_qoo_keyword = self.set_qoo_keyword(my_ct, tmpgname, int(tmpyct_qoo))
        tmp_wow_keyword = self.set_wow_keyword(my_ct, tmpgname, tmpyct)

        # wowma は検索タグIDを設定。
        tmp_wow_tagid = self.get_wow_tagid_list(my_ct, tmpgname, tmpyct)

        #tmp_qoo_seller_code = None
        # DBに保存
        self.logger.info('start save YaBuyersItemDetail')
        new_obj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        if not new_obj:
            # いったん、問答無用で上書きアップデートする
            self.logger.info('start save YaBuyersItemDetail add.')
            obj, created = YaBuyersItemDetail.objects.update_or_create(
                gid=tmpgid,
                gcode=gcd,
                glink=d_url,
                ss_url=ss_url,
                gsrc=gsrc,
                gname=tmpgname,
                gdetail=tmpgdetail,
                gnormalprice=tmpgspprice,
                stock=int(tmpgretail) if tmpgretail != '' else 0,
                wow_gname=tmp_wow_gname,
                wow_gdetail=tmp_wow_gdetail,
                wow_worn_key=tmp_wow_worn_key,
                wow_price=tmp_wow_price,
                wow_fixed_price=0,
                wow_postage_segment=tmp_postage_segment,  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
                wow_postage=tmp_postage,  # wowmaの個別送料
                wow_ctid=tmpyct,  # wowmaのカテゴリID
                wow_delivery_method_id=tmpdeliveryid,  # wowmaの配送方法ID
                wow_on_flg=tmp_wow_on_flg,
                wow_upd_status=tmp_wow_upd_status,
                wow_keyword=tmp_wow_keyword,
                wow_tagid=tmp_wow_tagid,
                qoo_gname=tmp_qoo_gname,
                qoo_gdetail=tmp_qoo_gdetail,
                qoo_keyword=tmp_qoo_keyword,
                qoo_contact_info=tmp_qoo_contact_info,
                qoo_worn_key=tmp_qoo_worn_key,
                qoo_price=tmp_qoo_price,
                qoo_fixed_price=0,
                qoo_postage_segment=tmp_postage_segment,  # qoo10の# 送料設定区分 1:送料別/2:送料込み/3:個別送料
                qoo_shipping_no=tmp_qoo_shipping_no,  # qooの# qoo送料コード 0:送料無料
                qoo_postage=tmp_qoo_postage,  # qooの個別送料
                qoo_ctid=int(tmpyct_qoo) if tmpyct_qoo != '' else 0,  # qooのカテゴリID
                qoo_delivery_method_id=tmp_qoo_deliveryid,  # qooの配送方法ID
                qoo_item_qty=int(tmp_qoo_item_qty) if tmp_qoo_item_qty != '' else 0,  #商品数量
                qoo_on_flg=tmp_qoo_on_flg,
                qoo_adult_yn=tmp_qoo_adult_yn,
                qoo_upd_status=tmp_qoo_upd_status,
                qoo_seller_code=tmp_qoo_seller_code,
                qoo_standard_img=tmp_qoo_standard_img,
                g_img_src_1=tmp_g_img_src[0],
                g_img_src_2=tmp_g_img_src[1],
                g_img_src_3=tmp_g_img_src[2],
                g_img_src_4=tmp_g_img_src[3],
                g_img_src_5=tmp_g_img_src[4],
                g_img_src_6=tmp_g_img_src[5],
                g_img_src_7=tmp_g_img_src[6],
                g_img_src_8=tmp_g_img_src[7],
                g_img_src_9=tmp_g_img_src[8],
                g_img_src_10=tmp_g_img_src[9],
                g_img_src_11=tmp_g_img_src[10],
                g_img_src_12=tmp_g_img_src[11],
                g_img_src_13=tmp_g_img_src[12],
                g_img_src_14=tmp_g_img_src[13],
                g_img_src_15=tmp_g_img_src[14],
                g_img_src_16=tmp_g_img_src[15],
                g_img_src_17=tmp_g_img_src[16],
                g_img_src_18=tmp_g_img_src[17],
                g_img_src_19=tmp_g_img_src[18],
                g_img_src_20=tmp_g_img_src[19],
            )
            obj.save()
        else:
            self.logger.info('start save YaBuyersItemDetail start update.')
            new_obj.gcode = gcd
            new_obj.glink = d_url
            new_obj.ss_url = ss_url
            new_obj.gsrc = gsrc
            new_obj.gname = tmpgname
            new_obj.gdetail = tmpgdetail
            new_obj.gnormalprice = int(tmpgspprice) if tmpgspprice != '' else 0
            new_obj.stock = int(tmpgretail) if tmpgretail != '' else 0
            new_obj.wow_gname = tmp_wow_gname
            new_obj.wow_gdetail = tmp_wow_gdetail
            new_obj.wow_worn_key = tmp_wow_worn_key
            new_obj.wow_price = tmp_wow_price
            new_obj.wow_fixed_price = 0
            new_obj.wow_postage_segment = tmp_postage_segment  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
            new_obj.wow_postage = tmp_postage  # wowmaの個別送料
            new_obj.wow_ctid = tmpyct  # wowmaのカテゴリID
            new_obj.wow_delivery_method_id = tmpdeliveryid  # wowmaの配送方法ID
            new_obj.wow_on_flg = tmp_wow_on_flg
            new_obj.wow_upd_status = tmp_wow_upd_status
            new_obj.wow_keyword = tmp_wow_keyword
            new_obj.wow_tagid = tmp_wow_tagid
            new_obj.qoo_gname = tmp_qoo_gname
            new_obj.qoo_gdetail = tmp_qoo_gdetail
            new_obj.qoo_keyword = tmp_qoo_keyword
            new_obj.qoo_contact_info = tmp_qoo_contact_info
            new_obj.qoo_worn_key = tmp_qoo_worn_key
            new_obj.qoo_price = tmp_qoo_price
            new_obj.qoo_fixed_price = 0
            new_obj.qoo_shipping_no = tmp_qoo_shipping_no  # qooの# qoo送料コード 0:送料無料
            new_obj.qoo_postage = tmp_qoo_postage  # qooの個別送料
            new_obj.qoo_ctid = int(tmpyct_qoo) if tmpyct_qoo != '' else 0  # qooのカテゴリID
            new_obj.qoo_delivery_method_id = tmp_qoo_deliveryid  # qooの配送方法ID
            new_obj.qoo_item_qty = int(tmp_qoo_item_qty) if tmp_qoo_item_qty != '' else 0  # 商品数量
            new_obj.qoo_on_flg = tmp_qoo_on_flg
            new_obj.qoo_adult_yn = tmp_qoo_adult_yn
            new_obj.qoo_upd_status = tmp_qoo_upd_status
            new_obj.qoo_seller_code = tmp_qoo_seller_code
            new_obj.qoo_standard_img = tmp_qoo_standard_img
            new_obj.g_img_src_1 = tmp_g_img_src[0]
            new_obj.g_img_src_2 = tmp_g_img_src[1]
            new_obj.g_img_src_3 = tmp_g_img_src[2]
            new_obj.g_img_src_4 = tmp_g_img_src[3]
            new_obj.g_img_src_5 = tmp_g_img_src[4]
            new_obj.g_img_src_6 = tmp_g_img_src[5]
            new_obj.g_img_src_7 = tmp_g_img_src[6]
            new_obj.g_img_src_8 = tmp_g_img_src[7]
            new_obj.g_img_src_9 = tmp_g_img_src[8]
            new_obj.g_img_src_10 = tmp_g_img_src[9]
            new_obj.g_img_src_11 = tmp_g_img_src[10]
            new_obj.g_img_src_12 = tmp_g_img_src[11]
            new_obj.g_img_src_13 = tmp_g_img_src[12]
            new_obj.g_img_src_14 = tmp_g_img_src[13]
            new_obj.g_img_src_15 = tmp_g_img_src[14]
            new_obj.g_img_src_16 = tmp_g_img_src[15]
            new_obj.g_img_src_17 = tmp_g_img_src[16]
            new_obj.g_img_src_18 = tmp_g_img_src[17]
            new_obj.g_img_src_19 = tmp_g_img_src[18]
            new_obj.g_img_src_20 = tmp_g_img_src[19]

            new_obj.save()
        """
        # csvに登録
        tmp_csv_row_dict = {
            'gid': str(gid),
            'gname': str(tmpgname),
            'gdetail': str(tmpgdetail),
            'gspprice': str(tmpgspprice),
            'gretail': str(tmpgretail),
            'gcode': str(tmpgcode),
            'tmpct': str(tmpct),
        }
        self.upd_csv.append(tmp_csv_row_dict)
        """

        """
        tdatetime = dt.now()
        tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
        tfilename = tstr + '_y_src_' + str(pcount) + '.txt'
        tfpath = mydwsrc_dir + '/detail/' + tfilename
        # f = open(tfpath, mode='w')
        f = codecs.open(tfpath, 'w', 'utf-8')

        f.write(self.common_chrome_driver.driver.page_source)
        # f.write(src_1)
        f.close()
        """

        # 要素の検証が終わるまで 10 秒待つ
        """
        element = WebDriverWait(self.common_chrome_driver.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'M_imageWrap'))
        )
        self.logger.debug('get_wowma_buyers_detail popup_text[' + element.text + ']')
        """

        #f_read = codecs.open(tfpath, 'r', 'utf-8')
        #s = f_read.read()
        #dom = lxml.html.fromstring(s)

        #dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href'].click() # 拡大画像のポップアップリンク
        #dom.xpath("//div[@id='viewButton']")[0].find('a').click() # 拡大画像のポップアップリンク
        """
        dom.xpath("//div[@id='viewButton']")[0].find('a').click() # 拡大画像のポップアップリンク
        # 要素の検証が終わるまで 10 秒待つ
        element = WebDriverWait(self.common_chrome_driver.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'M_imageWrap'))
        )
        self.logger.debug('get_wowma_buyers_detail popup_text[' + element.text + ']')
        """

        """
        # 以下要注意・・・まだできてない
        tmpdivs = dom.xpath("//div[@id='detail']") # これ以降調査のこと

        self.logger.debug('start break item detail.')

        for i, j in enumerate(tmpdivs):
            tmp_td_obj = list(j)
            # print(i)
            self.logger.debug('list. i[' + str(i) + ']')
            for ii, jj in enumerate(tmp_td_obj):
                tmpglink = jj.find_class('imgWrap')[0].find('a').attrib['href']
                tmpgsrc = jj.find_class('imgWrap')[0].find('a/img').attrib['src']
                tmpgid = jj.find_class('detail')[0].find_class('else')[0].find('li')[1].text # gコード
                tmpgname = jj.find_class('detail')[0].find_class('name')[0].find('a').text # 商品名
                #tmpgother = re.sub("\\D", "", str(tmpglink).rsplit("/", 1)[1])  # gコード

                self.logger.debug('glink:[' + str(tmpglink) + ']')
                self.logger.debug('gsrc:[' + str(tmpgsrc) + ']')
                self.logger.debug('gid:[' + str(tmpgid) + ']')
                self.logger.debug('gname:[' + str(tmpgname) + ']')
                if ii == 2:
                    break

                # 不要文字削除
                #tmpgalt = re.sub('◆新品◆', "", tmpgalt)

                # ひとまず、リストの一件毎で詳細まで処理してみよう
                # ユニークにするのに、gidの形式がこれでいいかどうか確認すること
        """

        """
                if not YaBuyersItemList.objects.filter(gid=tmpgid).exists():
                    obj, created = YaBuyersItemList.objects.update_or_create(
                        listurl=ss_url,
                        gid=tmpgid,
                        glink=tmpglink,
                        gname=tmpgname,
                        g_img_src=tmpgsrc,
                    )
                    obj.save()
                    # detailはここで取得してみる
                    if self.get_wowma_buyers_detail(tmpglink) = False:
                        # 途中でコケたら止めておこう
                        return False
        """

        self.logger.debug('get_wowma_buyers_detail out.')
        return True

    # https://qiita.com/tomson784/items/88a3fd2398a41932762a 参照
    # 指定された商品詳細のURLに対して在庫チェックする
    # 渡される ss_url は　https://buyerz.shop/shopbrand/ct113/　の形式
    # 登録の手順としては、
    # 1.  バイヤーズから商品情報取得 この時点ではまだ未掲載。フラグを立てる。まだ出品NG　のフラグを
    # 2.  画面から、掲載可否を判断して商品詳細などを編集する。OKなら出品OKのフラグをたてる。NGならブラックリストいり
    # 3.  wow_on_flg、qoo_on_flg　を在庫切れなら 3 で更新する。価格も更新
    # 4.  この処理の後で、wowmaとqoo10は後でまとめて更新をかける。
    def chk_wowma_buyers_stock(self, ss_url, gid, gcode):
        # self.stdout.write('ss_url:' + ss_url)
        # self.stdout.write(self.style.SUCCESS('my_s_url:' + s_url))
        self.logger.info('_chk_wowma_buyers_stock in ssurl:[' + str(ss_url) + ']')

        tmp_wow_on_flg = 0
        tmp_qoo_on_flg = 0

        if not self.common_chrome_driver:
            self.common_chrome_driver = CommonChromeDriver(self.logger)
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)

        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                # ss_url = 'https://buyerz.shop/shop/shopbrand.html?page=1&search=&sort=&money1=&money2=&prize1=&company1=&content1=&originalcode1=&category=&subcategory='
                self.common_chrome_driver.driver.get(ss_url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.info(traceback.format_exc())
                self.logger.info('_chk_wowma_buyers_stock webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                # self.restart_chrome()
                sleep(3)
            else:
                break

        s = self.common_chrome_driver.driver.page_source
        dom = lxml.html.fromstring(s)

        # 在庫チェックではいまのところ、画像の再取得は行わない。以下はコメントアウト

        tmpimglist = []
        cnt = 0

        # 商品詳細の各要素を取得する

        # tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        # tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 在庫チェックの際は、商品名と商品詳細は更新する。
        # wowma用に編集したものはそのままにしておく
        # 商品名
        # ※このタイミングで取得できないときはページが消えている。在庫切れとして処理しないと。
        try:
            tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/h2").text
        except selenium.common.exceptions.NoSuchElementException as no_such_elem:
            self.logger.info('_chk_wowma_buyers_stock no page. insert stock=0]')
            tmp_myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
            if tmp_myobj:
                # DBを更新
                # 価格はそのまま、在庫は0
                tmp_myobj.stock = 0
                tmp_myobj.wow_on_flg = 3
                tmp_myobj.qoo_on_flg = 3
                tmp_myobj.save()

                # かつ、ここでwowmaとqoo10は更新しないと。
                return True
            else:
                return False

        # 商品詳細
        try:
            tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/div[1]/div").text
        except:
            """
            この場合、商品詳細が取れないことがある
            https://buyerz.shop/shopdetail/000000024392/ct1075/page1/order/

            //div[@id='itemInfo']/div[1]/div
            が通常だが、親の
            //div[@id='itemInfo']/div[1]
            にtextが入ってることが。これはこれで処理するか。
            """
            try:
                tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                    "//div[@id='itemInfo']/div[1]").text
            except:
                # ここまで来て取れなければ、ページが終了していると判断する。
                self.logger.info('_chk_wowma_buyers_stock maybe no page. insert stock=0 gid:[{}]]'.format(tmpgid))
                tmp_myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
                if tmp_myobj:
                    # DBを更新
                    # 価格はそのまま、在庫は0
                    tmp_myobj.stock = 0
                    tmp_myobj.wow_on_flg = 3
                    tmp_myobj.qoo_on_flg = 3
                    tmp_myobj.save()

                    # かつ、ここでwowmaとqoo10は更新しないと。
                    return True
                else:
                    return False

        # ===============================
        # 通常価格
        tmpgspprice = int(re.sub("\\D", "",
                                 self.common_chrome_driver.driver.find_element_by_xpath(
                                     "//li[@id='M_usualValue']/span").text))

        # wowmaの価格を算出
        # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
        tmp_wow_price = self.get_benefit_price(tmpgspprice, 1.15)

        # qoo10の価格を算出
        # qoo10も10%が手数料なので上乗せして、それに利益率を加える。
        tmp_qoo_price = self.get_benefit_price(tmpgspprice, 1.3)
        self.logger.info('_chk_wowma_buyers_stock tmp_wow_price[' + str(tmp_wow_price) + ']')

        # ===============================
        # 在庫数の抽出
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//span[@class='M_item-stock-smallstock']")) == 0:
            # 在庫が取れないときは在庫切れか
            self.logger.debug('_chk_wowma_buyers_stock cant get [M_item-stock-smallstock].')
            tmpgretail = "0"
        else:
            tmpgretail = re.sub("\\D", "",
                                self.common_chrome_driver.driver.find_element_by_xpath(
                                    "//span[@class='M_item-stock-smallstock']").text)
            if tmpgretail == '':
                tmpgretail = "0"
            else:
                # 在庫あり
                tmp_wow_on_flg = 1
                tmp_qoo_on_flg = 1

        if tmpgretail == "0":
            tmp_wow_on_flg = 3
            tmp_qoo_on_flg = 3

        # DBに保存
        myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        if myobj:
            self.logger.info('start save YaBuyersItemDetail add.')

            # 既存DBのフラグによってどうステータスを更新するか
            # 出品はまだNG。（画面から編集してない）が、DBの在庫などは更新していい
            # 元のwow_on_flgが、0か2だったら在庫更新はせずそのまま
            if myobj.wow_on_flg == 0 or myobj.wow_on_flg == 2:
                tmp_wow_on_flg = myobj.wow_on_flg
            if myobj.qoo_on_flg == 0 or myobj.qoo_on_flg == 2:
                tmp_qoo_on_flg = myobj.qoo_on_flg

            # DBを更新
            myobj.gnormalprice = int(tmpgspprice)
            myobj.stock = int(tmpgretail)
            myobj.wow_price = tmp_wow_price
            myobj.qoo_price = tmp_qoo_price
            myobj.wow_on_flg = tmp_wow_on_flg
            myobj.qoo_on_flg = tmp_qoo_on_flg
            myobj.save()
        else:
            # ここで指定された商品は必ずDBにあるはずだが、なかった？　何もしない
            self.logger.debug('_chk_wowma_buyers_stock 指定の商品がDBに登録なし？ gid[{}]'.format(tmpgid))

        self.logger.debug('end of _chk_wowma_buyers_stock')

        return True

    # バイヤーズのカテゴリコードが取れていない場合、商品詳細ページのURLから取得する
    # ヒットしなければ空文字のまま
    def get_buyers_ctcd_from_url(self, glink):
        tmp_item = glink.split('/')
        for item in tmp_item:
            if item.startswith('ct'):
                return item
        return ''

    # バイヤーズのカテゴリコードからwowmaとqoo10のカテゴリコードを取得する
    # リターンは wowma_ctid, wowma_flg, qoo_ctid, qoo_flg の4つにしよう
    def get_wow_qoo_ctcd(self, my_ct, tmpgname, tmp_wow_gdetail, tmp_qoo_gdetail):

        # wowmaのカテゴリチェック
        tmpyct_obj = self.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        wowma_catid = tmpyct_obj[0]
        wowma_flg = tmpyct_obj[1]

        # qoo10のカテゴリチェック
        tmpyct_qoo_obj = self.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
        qoo_catid = tmpyct_qoo_obj[0]
        qoo_flg = tmpyct_qoo_obj[1]

        if wowma_flg == 0 or wowma_flg == 3:
            tmpyct_key_obj = self.chk_ct_by_keyword_for_wowma(tmp_wow_gdetail, tmpgname)
            if tmpyct_key_obj:
                wowma_catid = str(tmpyct_key_obj)
                wowma_flg = 2

        if qoo_flg == 0 or qoo_flg == 3:
            tmpyct_key_qoo_obj = self.chk_ct_by_keyword_for_qoo(tmp_qoo_gdetail, tmpgname)
            if tmpyct_key_qoo_obj:
                qoo_catid = str(tmpyct_key_qoo_obj)
                qoo_flg = 2

        if wowma_catid == 0:
            self.logger.info('get_wow_qoo_ctcd cant match wowma_catid.')
        if qoo_catid == 0:
            self.logger.info('get_wow_qoo_ctcd cant match qoo_catid.')

        return wowma_catid, wowma_flg, qoo_catid, qoo_flg

    # カテゴリコードをチェックしてマッチしたらwowmaのカテゴリコードと優先順（1,2,3)を返す
    # 優先順は、1が最優先。一つ決まればOK、決まらなければ続けてチェックする
    def chk_wow_ct(self, ctcode, gname, gdetail):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            try:
                result_y_ct = str(__class__._MY_CT_CODES_SMALL[ctcode]["wowma_catid"])
            except KeyError:

                # 10桁サブカテゴリにマッチしなかった。
                # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                # ct119 「ファッション > レディース」とか。
                if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        #
                        if re.search(mykey, gname):
                            # レディースかメンズは、wowmaではひとまず判定しない
                            if int(myvalue["wowma_catid"]) > 0:
                                return int(myvalue["wowma_catid"]), 1

                            """
                            if myvalue['sex'] == '1':  # sex に 1が設定されてるカテゴリキーワードだけ
                                if re.search('レディース', gname):
                                    return myvalue["female"], 1  # マッチしたとして 1を返却
                                elif re.search('メンズ', gname):
                                    return myvalue["male"], 1
                                else:
                                    return myvalue["wowma_catid"], 1
                            else:
                                return myvalue["wowma_catid"], 1
                            """

                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        if re.search(mykey, gdetail):
                            # レディースかメンズは、wowmaではひとまず判定しない
                            if int(myvalue["wowma_catid"]) > 0:
                                return int(myvalue["wowma_catid"]), 1

                    # ここに来ると設定ミス？
                    self.logger.debug('buyers_info cant match chk_ct.　warning code')
                    return 0, 3

                try:
                    # 5桁の大カテゴリにマッチするか
                    result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["wowma_catid"])
                except KeyError:
                    try:
                        # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["wowma_catid"])
                    except KeyError:
                        # だめならFalse (0と3を返すようにした)
                        return 0, 3
                    # 大カテゴリにマッチしたらいちおう3を返す
                    return result_y_ct, 3
                # 大カテゴリにマッチしたらいちおう２を返す
                return result_y_ct, 2

            # サブカテゴリにマッチしたら正解
            return result_y_ct, 1

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return 0, 3

    # カテゴリコードをチェックしてマッチしたらqoo10のカテゴリコードと優先順（1,2,3)を返す
    # 優先順は、1が最優先。一つ決まればOK、決まらなければ続けてチェックする
    def chk_qoo_ct(self, ctcode, gname, gdetail):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            try:
                result_y_ct = str(__class__._MY_CT_CODES_SMALL[ctcode]["qoo_catid"])
            except KeyError:
                # 10桁サブカテゴリにマッチしなかった。
                # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                # ct119 「ファッション > レディース」とか。
                if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        #
                        if re.search(mykey, gname):
                            # レディースかメンズは、qooではひとまず判定しない
                            if int(myvalue["qoo_catid"]) > 0:
                                self.logger.info('chk_qoo_ct:1: catid決定したはず[{}]'.format(myvalue["qoo_catid"]))
                                return myvalue["qoo_catid"], 1

                            """
                            if myvalue['sex'] == '1':  # sex に 1が設定されてるカテゴリキーワードだけ
                                if re.search('レディース', gname):
                                    return myvalue["female"], 1  # マッチしたとして 1を返却
                                elif re.search('メンズ', gname):
                                    return myvalue["male"], 1
                                else:
                                    return myvalue["wowma_catid"], 1
                            else:
                                return myvalue["wowma_catid"], 1
                            """

                    # 商品名で見つからなかったら商品説明も見る
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        if re.search(mykey, gdetail):
                            # レディースかメンズは、qooではひとまず判定しない
                            if int(myvalue["qoo_catid"]) > 0:
                                self.logger.info('chk_qoo_ct:2: catid決定したはず[{}]'.format(myvalue["qoo_catid"]))
                                return myvalue["qoo_catid"], 1

                    # ここに来ると設定ミス？ _MY_CT_CODES_SMALL_WARN　で指定されてるけど見つけられなかったらFalse
                    self.logger.info('buyers_info cant match 500 qoo_chk_ct.code[{}]'.format(ctcode))
                    return 0, 3

                try:
                    # 5桁の大カテゴリにマッチするか
                    result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["qoo_catid"])
                except KeyError:
                    try:
                        # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["qoo_catid"])
                    except KeyError:
                        # だめならFalse
                        return 0, 3
                    # 大カテゴリにマッチしたらいちおう3を返す
                    return result_y_ct, 3
                # 大カテゴリにマッチしたらいちおう２を返す
                return result_y_ct, 2

            # サブカテゴリにマッチしたら正解
            self.logger.info('chk_qoo_ct:10: smallカテに一致。[{}]'.format(result_y_ct))
            return result_y_ct, 1

        except Exception as e:
            self.logger.info(traceback.format_exc())
            return 0, 3

    # カテゴリコードをチェックしてマッチしたらヤフオクのカテゴリコードと優先順（1,2,3)を返す
    # 優先順は、1が最優先。一つ決まればOK、決まらなければ続けてチェックする
    def chk_ct(self, ctcode, gname):

        try:
            # まず、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
            if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                    #
                    if re.search(mykey, gname):
                        # レディースかメンズも判定する
                        if myvalue['sex'] == '1':  # sex に 1が設定されてるカテゴリキーワードだけ
                            if re.search('レディース', gname):
                                return myvalue["female"], 1  # マッチしたとして 1を返却
                            elif re.search('メンズ', gname):
                                return myvalue["male"], 1
                            else:
                                return myvalue["y_ct"], 1
                        else:
                            return myvalue["y_ct"], 1

                # ここに来ると設定ミス？
                self.logger.debug('buyers_info cant match chk_ct.　warning code')
                return False

            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            try:
                result_y_ct = str(__class__._MY_CT_CODES_SMALL[ctcode]["y_ct"])
            except KeyError:
                try:
                    # 5桁の大カテゴリにマッチするか
                    result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["y_ct"])
                except KeyError:
                    try:
                        # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["y_ct"])
                    except KeyError:
                        # だめならNone
                        return None
                    # 大カテゴリにマッチしたらいちおう3を返す
                    return result_y_ct, 3
                # 大カテゴリにマッチしたらいちおう２を返す
                return result_y_ct, 2

            # サブカテゴリにマッチしたら正解
            return result_y_ct, 1

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # qoo10用の検索ワードをセットして返す。商品名のキーワードに含まれないキーワードリストを
    # 30文字 x 10個までセットして半角スペース区切りに。
    # qoo10に登録するときは注意のこと
    def set_qoo_keyword(self, ctcode, gname, qoo_ctid):

        ret_str = ''
        if ctcode == '':
            # wow_ctid から検索しないと。キーワードマッチの場合であろう
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                if re.search(mykey, gname):
                    # レディースかメンズは、wowmaではひとまず判定しない
                    if myvalue["s_keyword"]:
                        ret_str = self.get_keyword_set(myvalue["s_keyword"], gname, 3)
                        self.logger.debug('set_qoo_keyword found keyword 1')
                        return ret_str
            # 抜けてしまうと失敗。空文字返す
            return ret_str
        else:
            try:
                # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                self.logger.info('moto_key:[{}]'.format(moto_keyword))
                ret_str = self.get_keyword_set(moto_keyword, gname, 10)
                self.logger.info('ret_str:[{}]'.format(ret_str))
                # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
                """
                try:
                    # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                    moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                    ret_str = self.get_keyword_set(moto_keyword, gname, 10)
                except KeyError:
    
                    # 10桁サブカテゴリにマッチしなかった。
                    # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                    # ct119 「ファッション > レディース」とか。
                    if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                        for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                            #
                            if re.search(mykey, gname):
                                # レディースかメンズは、wowmaではひとまず判定しない
                                if int(myvalue["wowma_catid"]) > 0:
                                    return myvalue["wowma_catid"], 1
    
                        # ここに来ると設定ミス？
                        self.logger.debug('buyers_info cant match chk_ct.　warning code')
                        return False
    
                    try:
                        # 5桁の大カテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["wowma_catid"])
                    except KeyError:
                        try:
                            # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                            result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["wowma_catid"])
                        except KeyError:
                            # だめならNone
                            return ''
                        # 大カテゴリにマッチしたらいちおう3を返す
                        return result_y_ct, 3
                    # 大カテゴリにマッチしたらいちおう２を返す
                    return result_y_ct, 2
    
                # サブカテゴリにマッチしたら、商品名と比較して含まれてないキーワードをセットする
                return result_y_ct, 1
                """
                #ret_str = ''

            except Exception as e:
                self.logger.debug(traceback.format_exc())
                return ret_str  # 空文字を一応返す

        return ret_str
    # wowma用の検索ワードをセットして返す。商品名のキーワードに含まれないキーワードリストを
    # 20文字 x 3個までセットして半角スペース区切りに。
    # wowmaに登録するときは注意のこと
    def set_wow_keyword(self, ctcode, gname, wow_ctid):

        ret_str = ''
        if ctcode == '':
            # wow_ctid から検索しないと。キーワードマッチの場合であろう
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                if re.search(mykey, gname):
                    # レディースかメンズは、wowmaではひとまず判定しない
                    if myvalue["s_keyword"]:
                        ret_str = self.get_keyword_set(myvalue["s_keyword"], gname, 3)
                        self.logger.debug('set_wow_keyword found keyword 1')
                        return ret_str
            # 抜けてしまうと失敗。空文字返す
            return ret_str
        else:
            try:
                # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                ret_str = self.get_keyword_set(moto_keyword, gname, 3)
                # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
                """
                try:
                    # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                    moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                    ret_str = self.get_keyword_set(moto_keyword, gname, 3)
                except KeyError:
    
                    # 10桁サブカテゴリにマッチしなかった。
                    # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                    # ct119 「ファッション > レディース」とか。
                    if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                        for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                            #
                            if re.search(mykey, gname):
                                # レディースかメンズは、wowmaではひとまず判定しない
                                if int(myvalue["wowma_catid"]) > 0:
                                    return myvalue["wowma_catid"], 1
    
                        # ここに来ると設定ミス？
                        self.logger.debug('buyers_info cant match chk_ct.　warning code')
                        return False
    
                    try:
                        # 5桁の大カテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["wowma_catid"])
                    except KeyError:
                        try:
                            # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                            result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["wowma_catid"])
                        except KeyError:
                            # だめならNone
                            return ''
                        # 大カテゴリにマッチしたらいちおう3を返す
                        return result_y_ct, 3
                    # 大カテゴリにマッチしたらいちおう２を返す
                    return result_y_ct, 2
    
                # サブカテゴリにマッチしたら、商品名と比較して含まれてないキーワードをセットする
                return result_y_ct, 1
                """
                #ret_str = ''

            except KeyError:
                #self.logger.debug(traceback.format_exc())
                #return ret_str  # 空文字を一応返す
                # 10桁サブカテゴリにマッチしなかった。
                # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                # ct119 「ファッション > レディース」とか。
                if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        #
                        if re.search(mykey, gname):
                            # レディースかメンズは、wowmaではひとまず判定しない
                            if myvalue["s_keyword"]:
                                ret_str = self.get_keyword_set(myvalue["s_keyword"], gname, 3)
                                return ret_str

                    # ここに来ると設定ミス？
                    self.logger.debug('buyers_info cant match chk_ct.　warning code')
                    return False

        return ret_str

    # wowma用のタグIDをセットして返す。商品名のキーワードにマッチする検索タグを
    # 64個までセットして半角スペース区切りに。
    # wowmaに登録するときは注意のこと
    # タグとカテゴリとのマッピングはこちら wow_cat
    # https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=2027093015
    def get_wow_tagid_list(self, ctcode, gname, wowma_catid):
        self.logger.info('get_wow_tagid_list:in ctcode:[{}]'.format(ctcode))

        ret_str = ''
        new_list = []
        try:

            if ctcode == '':
                wow_ctcd = wowma_catid
            else:
                try:
                    wow_ctcd = __class__._MY_CT_CODES_SMALL[ctcode]["wowma_catid"]
                except:
                    # _MY_CT_CODES_SMALL に登録してない、キーワードマッチさせるカテゴリは
                    # ここで KeyErrorが起きる。その場合は空文字を返却して終了
                    self.logger.info(
                        'get_wow_tagid_list:1_1 ctcdがマッチしないので検索タグは空で。ctcd:[{}]'.format(ctcode))
                    return ret_str

            self.logger.info('get_wow_tagid_list:1 wow_ctcd:[{}]'.format(wow_ctcd))

            # WowmaCatTagOyaList, WowmaTagChildList
            oya = WowmaCatTagOyaList.objects.filter(
                wow_cat_id=wow_ctcd,
            ).first()
            if oya:
                self.logger.info('get_wow_tagid_list:2 登録済み親idと一致 gname:[{}]'.format(gname))
            else:
                self.logger.info('get_wow_tagid_list:3 親idと一致せず。処理終了')
                return

            # 商品名から、紐付けるキーワード（ブラック　とか）を抽出
            tmp_list_keyword = gname.split(" ")

            # 10040000 10270000 10280000 とか。
            tmp_list_moto = oya.tag_grp.split(" ")

            # 紐付いている親タグから、小タグを探す
            list_cnt = 0
            for tag_moto in tmp_list_moto:
                child_list = WowmaTagChildList.objects.filter(
                    oya_id=tag_moto,
                ).all()

                child_find_flg = 0
                for child in child_list:
                    # キーワードと、子タグ名称
                    # まず、キーワードとマッチする子タグは優先して登録
                    if child.child_name in tmp_list_keyword:
                        new_list.append(str(child.child_id))
                        child_find_flg = 1
                        list_cnt += 1
                        if child.rel_flg == 0:  # 一つの商品に複数の子タグを登録できない場合はここで終わり
                            break
                        if list_cnt > 63:
                            break
                if child_find_flg == 0:
                    # まだ見つかってなければ、まるごと登録してしまう
                    for child in child_list:
                        # キーワードと、子タグ名称
                        # まず、キーワードとマッチする子タグは優先して登録
                        if child.rel_flg == 0:  # 一つの商品に複数の子タグを登録できない
                            new_list.append(str(child.child_id))  # 一つだけ登録してbreak
                            list_cnt += 1
                            break
                        else:
                            new_list.append(str(child.child_id))  # 紐付いてるだけ登録してゆく
                            list_cnt += 1
                            if list_cnt > 63:
                                break

                # ここでも最大登録数のチェックはしておく
                if list_cnt > 63:
                    break

            # 全部がっちゃんこして半角スペース区切りにして返却
            ret_str = ' '.join(new_list)

            self.logger.info('get_wow_tagid_list:4 返却するタグ:[{}]'.format(ret_str))
            return ret_str.strip()

        except Exception as e:
            self.logger.info(traceback.format_exc())
            self.logger.debug(traceback.format_exc())
            return

        return

    # wowmaの商品登録・更新時に返却されたロットナンバーをDBにセットする
    def set_wow_lotnum(self, gid, lotnum):
        self.logger.info('set_wow_lotnum:in gid:[{}] lotnum[{}]'.format(gid,lotnum))
        # DBに保存
        ret_obj = YaBuyersItemDetail.objects.filter(gid=gid).first()
        if ret_obj:
            # DBを更新
            ret_obj.wow_lotnum = lotnum
            ret_obj.save()
            self.logger.info('set_wow_lotnum seved. :lotnum:[{}]'.format(ret_obj.wow_lotnum))
        return

    # 指定された個数だけ、キーワードセットを取得する。半角スペース区切り
    def get_keyword_set(self, moto_key, delete_key, ret_num):
        ret_str = ""
        tmp_list_moto = moto_key.split(" ")
        tmp_list_del = delete_key.split(" ")
        new_list = []

        my_cnt = 0
        for moto in tmp_list_moto:
            if moto not in tmp_list_del:
                new_list.append(moto)
                my_cnt += 1
                if my_cnt >= ret_num:
                    break

        ret_str = ' '.join(new_list)
        return ret_str.strip()

    # カテゴリコード一覧を返す
    def get_ct(self):
        return __class__._MY_CT_CODES

    # wowma向けの商品取得対象URL一覧を返す
    def get_url_list_for_wowma(self):
        return __class__._MY_URLS_WOWMA

    # 文字列内でキーワードがマッチしたらカテゴリコードを返す
    def chk_ct_by_keyword_for_wowma(self, mystr, mytitle):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            #result_y_ct = str(__class__._MY_CT_CODES_KEYWORD[ctcode]["y_ct"])
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                #
                if re.search(mykey, mystr):

                    return int(myvalue["wowma_catid"])

                    """
                    # レディースかメンズも判定する
                    if myvalue['sex'] == '1': # sex に 1が設定されてるカテゴリキーワードだけ
                        if re.search('レディース', mytitle):
                            return myvalue["female"]
                        elif re.search('メンズ', mytitle):
                            return myvalue["male"]
                        else:
                            return myvalue["y_ct"]
                    else:
                        return myvalue["y_ct"]
                    """

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # 文字列内でキーワードがマッチしたらカテゴリコードを返す
    def chk_ct_by_keyword_for_qoo(self, mystr, mytitle):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            #result_y_ct = str(__class__._MY_CT_CODES_KEYWORD[ctcode]["y_ct"])
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                #
                if re.search(mykey, mystr):
                    return myvalue["qoo_catid"]

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # 文字列内でキーワードがマッチしたらカテゴリコードを返す
    def chk_ct_by_keyword(self, mystr, mytitle):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            #result_y_ct = str(__class__._MY_CT_CODES_KEYWORD[ctcode]["y_ct"])
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                #
                if re.search(mykey, mystr):

                    # レディースかメンズも判定する
                    if myvalue['sex'] == '1': # sex に 1が設定されてるカテゴリキーワードだけ
                        if re.search('レディース', mytitle):
                            return myvalue["female"]
                        elif re.search('メンズ', mytitle):
                            return myvalue["male"]
                        else:
                            return myvalue["y_ct"]
                    else:
                        return myvalue["y_ct"]

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # wowmaで取得対象にする、バイヤーズのカテゴリコードの一覧を返却する
    # ctflg ：　サブカテゴリのチェックフラグ。"small" が少カテゴリで登録OK、送料無料
    #           "sale" が500円均一など、追加でカテゴリのチェックや商品内容の確認が必要なもの
    #           "pack" がゆうパックなど、送料が別のもの。送料は個別でここに設定するか？
    # shipping : 送料を文字列で。"0" や "500" など

    """
    _MY_URLS_WOWMA = {
        "ct1076": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
    }
    """

    _MY_URLS_WOWMA = {
        "ct676": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > ジャケット、上着 > ライダース > Lサイズ
        "ct677": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー
        "ct678": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ
        "ct679": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ
        "ct680": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ
        "ct681": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > シャツ > 半袖 > 半袖シャツ一般 > Mサイズ
        "ct682": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > シャツ > 長袖 > 長袖シャツ一般 > Mサイズ
        "ct685": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > カーディガン
        "ct803": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > シャツ > その他の袖丈
        "ct804": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > トレーナー > Mサイズ
        "ct805": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ
        "ct806": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ
        "ct807": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > 水着 > Mサイズ
        "ct120": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ
        "ct689": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ライダース
        "ct690": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > その他
        "ct691": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ
        "ct692": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャケット、ブレザー > Mサイズ
        "ct693": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ
        "ct694": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ
        "ct695": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > スカジャン
        "ct696": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジージャン > Mサイズ
        "ct1022": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ
        "ct163": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ
        "ct1108": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ
        "ct698": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ
        "ct699": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > その他
        "ct700": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct1102": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他
        "ct704": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他
        "ct701": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > イラスト、キャラクター
        "ct702": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈
        "ct1107": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct703": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct1111": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > 柄もの
        "ct1112": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > 文字、ロゴ
        "ct705": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct706": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct707": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct708": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct1045": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct1044": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct709": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct710": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct711": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct715": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct712": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct713": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct714": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 半袖 > Mサイズ
        "ct716": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 袖なし、ノースリーブ > ノースリーブシャツ一般
        "ct717": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > キャミソール
        "ct719": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > チュニック > 袖なし、ノースリーブ > Mサイズ
        "ct1110": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > チューブトップ、ベアトップ
        "ct162": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct720": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct721": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct722": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct723": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct724": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct725": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct726": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct727": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct122": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ
        "ct728": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ
        "ct1008": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > レギンス、トレンカ
        "ct1009": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ
        "ct1010": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ
        "ct1047": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ
        "ct738": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct739": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct740": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct741": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ミニスカート > その他
        "ct742": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ミニスカート > タイトスカート > Mサイズ
        "ct743": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他
        "ct744": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > プリーツスカート > Mサイズ
        "ct745": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > フレアースカート、ギャザースカート > Mサイズ
        "ct746": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > タイトスカート > Mサイズ
        "ct747": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他
        "ct748": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct754": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > フレアースカート、ギャザースカート > Mサイズ
        "ct156": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ
        "ct749": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ
        "ct750": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ
        "ct751": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ
        "ct752": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ
        "ct753": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct755": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct756": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct757": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct758": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct759": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct760": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct761": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct762": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct1453": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct765": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツウエア > 女性用 > 上下セット > ジャージ > その他
        "ct763": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > その他
        "ct767": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct1109": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > その他
        "ct768": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct769": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct770": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ショーツ > Mサイズ > スタンダード
        "ct771": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > スリップ > Mサイズ
        "ct772": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct773": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他
        "ct774": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ
        "ct779": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > その他
        "ct780": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > セパレート > Mサイズ > 三角ビキニ
        "ct781": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > その他
        "ct782": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > その他
        "ct1038": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツ別 > サーフィン > ウエア > ラッシュガード > 女性用 > Mサイズ
        "ct775": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > トップス > 長袖Tシャツ > 140（135～144cm）
        "ct776": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > ボトムス > パンツ、ズボン一般 > 140（135～144cm）
        "ct1031": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（女の子用） > その他
        "ct777": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > コート > コート一般 > 130（125～134cm）
        "ct778": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > セット、まとめ売り
        "ct1016": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他
        "ct1032": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他
        "ct784": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男の子用） > その他
        "ct785": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > ロンパース > 80（75～84cm）
        "ct786": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > トップス > Tシャツ > 長袖 > 男女兼用 > 90（85～94cm）
        "ct787": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > その他
        "ct788": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > コート、ジャンパー > コート > 男女兼用 > 90（85～94cm）
        "ct789": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > スタイ、よだれかけ
        "ct790": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > 水着 > 女の子用 > 90（85～94cm）
        "ct791": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > その他
        "ct792": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > マタニティウエア > その他
        "ct795": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct1028": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > 男性用
        "ct1029": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct1030": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct796": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > コスプレ衣装
        "ct797": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式
        "ct798": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式
        "ct799": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > アクセサリー、小物
        "ct1000": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > インナー
        "ct800": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct801": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他
        "ct826": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他
        "ct828": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > キャップ > その他
        "ct829": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > ニット帽
        "ct1026": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他
        "ct830": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ
        "ct831": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ
        "ct832": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ
        "ct833": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > テンガロンハット、ウエスタンハット
        "ct834": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > 麦わら帽子
        "ct1024": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > キャスケット
        "ct1025": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ベレー帽
        "ct1154": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > 帽子
        "ct1050": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他
        "ct1051": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ショート
        "ct1052": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ロング
        "ct1053": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他
        "ct1054": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他
        "ct1017": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他
        "ct1018": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアゴム、シュシュ
        "ct1019": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他
        "ct1020": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ
        "ct1021": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ
        "ct1011": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他
        "ct1012": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツサングラス > その他
        "ct1013": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他
        "ct1014": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > めがね、コンタクト > 老眼鏡
        "ct1015": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他
        "ct1055": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > その他
        "ct1056": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他
        "ct1061": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > その他
        "ct1062": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他
        "ct1057": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ピアス > その他
        "ct1064": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1074": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1075": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1076": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1077": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1078": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1079": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1058": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1065": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1080": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1081": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1066": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1082": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1083": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > チョーカー > その他
        "ct1084": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1085": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1086": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > ダイヤモンド > その他
        "ct1087": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1059": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1068": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1088": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1089": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > バングル > その他
        "ct1090": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1069": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1091": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1092": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他
        "ct1093": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他
        "ct1094": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他
        "ct1060": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他
        "ct1070": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他
        "ct1071": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他
        "ct1095": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > ゴールド > その他
        "ct1096": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他
        "ct1097": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他
        "ct1158": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ブローチ > その他
        "ct794": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般
        "ct819": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ストール > ストール一般
        "ct821": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 男性用
        "ct822": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ストール > ストール一般
        "ct820": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般
        "ct823": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般
        "ct824": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ストール > ストール一般
        "ct810": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ハンドバッグ > その他
        "ct848": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > バックパック、かばん > リュックサック > バックパック
        "ct849": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック
        "ct850": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > ショルダーバッグ
        "ct851": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > 自転車、サイクリング > バッグ > メッセンジャーバッグ
        "ct852": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズバッグ > ボディバッグ
        "ct853": {"ctflg": "small", "shipping": "0"}, #オークション > 事務、店舗用品 > バッグ、スーツケース > スーツケース、トランク > スーツケース、トランク一般
        "ct854": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > クラッチバッグ、パーティバッグ
        "ct855": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ハンドバッグ > その他
        "ct856": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > トートバッグ
        "ct858": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ポーチ
        "ct1005": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ショルダーバッグ > その他
        "ct1006": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ショルダーバッグ > その他
        "ct1007": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ショルダーバッグ > その他
        "ct1462": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > ボストンバッグ
        "ct1463": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > エコバッグ
        "ct838": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズ腕時計 > デジタル > その他
        "ct839": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディース腕時計 > デジタル > その他
        "ct840": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他
        "ct841": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他
        "ct808": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他
        "ct842": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他
        "ct843": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > 長財布（小銭入れあり）
        "ct844": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > 二つ折り財布（小銭入れあり）
        "ct836": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他
        "ct845": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > 長財布（小銭入れあり）
        "ct846": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > 二つ折り財布（小銭入れあり）
        "ct837": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他
        "ct847": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他
        "ct811": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズシューズ > その他
        "ct859": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズシューズ > その他
        "ct860": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースシューズ > その他
        "ct861": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビーシューズ > スニーカー > 14cm～
        "ct1104": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースシューズ > その他
        "ct793": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > スカーフ、ポケットチーフ > 女性用
        "ct1027": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 手袋 > 女性用 > その他
        "ct1033": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ベルト > 男性用 > その他
        "ct809": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > キーケース
        "ct1023": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用
        "ct908": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家具、インテリア > 鏡台、ドレッサー
        "ct909": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他
        "ct910": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他
        "ct911": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct912": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct913": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > テーブルクロス
        "ct914": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 食器 > 洋食器 > プレート、皿 > その他
        "ct915": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct1098": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 調理器具 > その他
        "ct1106": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > バス > その他
        "ct1037": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > スリッパ
        "ct916": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > タオル > その他
        "ct917": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > タオル > バスタオル
        "ct919": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > エプロン
        "ct920": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct1105": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct63": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct54": {"ctflg": "small", "shipping": "0"}, #オークション > コンピュータ > 周辺機器 > その他
        "ct56": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 家庭用電化製品 > その他
        "ct922": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 冷暖房、空調 > 加湿器、除湿器 > 加湿器 > その他
        "ct923": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 冷暖房、空調 > 扇風機
        "ct1977": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他
        "ct981": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他
        "ct513": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct926": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone X用
        "ct927": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用
        "ct928": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用
        "ct929": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用
        "ct930": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct1330": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1331": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct1332": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1333": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1334": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1335": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct1336": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1337": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct1338": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1339": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1340": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1341": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct1342": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1343": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct1344": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1345": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1346": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1347": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct924": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct931": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用
        "ct932": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用
        "ct933": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用
        "ct934": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct935": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct925": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct936": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用
        "ct937": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用
        "ct938": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用
        "ct939": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct940": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct68": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct941": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用
        "ct942": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用
        "ct943": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用
        "ct944": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct945": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct65": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct946": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用
        "ct947": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用
        "ct948": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用
        "ct949": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct950": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct75": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct951": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct952": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct953": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct954": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct955": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct72": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct956": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct957": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct958": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct959": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct960": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct69": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct961": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用
        "ct962": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用
        "ct963": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用
        "ct964": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct965": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct76": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct966": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct967": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct968": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct969": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct970": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct516": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct971": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct972": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct973": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct974": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct975": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct78": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー
        "ct976": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct977": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct978": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct979": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct980": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct32": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct10": {"ctflg": "small", "shipping": "0"}, #オークション > 事務、店舗用品 > 文房具 > その他
        "ct57": {"ctflg": "small", "shipping": "0"}, #オークション > 事務、店舗用品 > 文房具 > その他
        "ct17": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他
        "ct982": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他
        "ct95": {"ctflg": "small", "shipping": "0"}, #オークション > 食品、飲料 > ダイエット食品 > その他
        "ct1103": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 美容、健康 > 美容機器 > ネイルケア
        "ct13": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他
        "ct1046": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > アウトドアウエア > 服飾小物 > その他
        "ct73": {"ctflg": "small", "shipping": "0"}, #医療・介護・医薬品＞介護・福祉＞その他生活グッズ＞サポーター
        "ct983": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他
        "ct984": {"ctflg": "small", "shipping": "0"}, #ダイエット・健康＞抗菌・除菌グッズ＞マスク＞その他マスク
        "ct987": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他
        "ct999": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 水遊び > ビーチボール
        "ct12": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct64": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > アクセサリー > エンブレム > その他
        "ct66": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > カーナビ > 液晶保護フィルム、カバー > その他
        "ct991": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct992": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct67": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct1116": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > マタニティウエア
        "ct993": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他
        "ct995": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > こま > 一般
        "ct83": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 服
        "ct988": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他
        "ct989": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他
        "ct87": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 手入れ用品
        "ct990": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > その他
        "ct91": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > その他
        "ct996": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 知育玩具 > その他
        "ct994": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 食玩、おまけ　> その他
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct169": {"ctname": "オークション > ファッション > レディースファッション＞その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct998": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct1099": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct71": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct74": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct1114": {"ctname": "オークション > ベビー用品", "y_ct": "24202", "wowma_catid": "", "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580",
                  "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct170": {"ctname": "オークション > おもちゃ、ゲーム", "y_ct": "25464", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct18": {"ctname": "オークション > 自動車、オートバイ > 工具", "y_ct": "24650", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }

    # 以下はキーワードマッチを取得する一時的なリスト。本番用は↑を使う
    """
    _MY_URLS_WOWMA = {
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct169": {"ctname": "オークション > ファッション > レディースファッション＞その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct998": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct1099": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct71": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct74": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct1114": {"ctname": "オークション > ベビー用品", "y_ct": "24202", "wowma_catid": "", "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580",
                  "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct170": {"ctname": "オークション > おもちゃ、ゲーム", "y_ct": "25464", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct18": {"ctname": "オークション > 自動車、オートバイ > 工具", "y_ct": "24650", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }
    """







    # 10桁のサブカテゴリをこちらに。優先
    # ここで指定したカテゴリは、_MY_CT_CODES_KEYWORD　のキーワードにヒットさせて判定する
    _MY_CT_CODES_SMALL_WARN = {
        "ct113": {"ctname": "my_key", "y_ct": "", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
        "ct117": {"ctname": "my_key", "y_ct": "", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580",
                  "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }

    """
    _MY_CT_CODES_SMALL_WARN = {
        "ct113": {"ctname": "オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057466", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
        "ct117": {"ctname": "オークション > ファッション > メンズファッション > シャツ > その他の袖丈", "y_ct": "2084054038", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
    }
    """

    # 10桁のサブカテゴリをこちらに。優先
    # バイヤーズカテゴリのシート、　https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=492800307
    # ↓ 2021/10/10 qoo10のカテゴリ含めた最新は以下[qoo_リスト抽出用]
    # https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=1688672388
    # 「cat_wowma_1_edit」シート　R列　を参考に
    _MY_CT_CODES_SMALL = {
        "ct676": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ライダース > Lサイズ", "y_ct": "2084243906","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct677": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー", "y_ct": "2084303393","sex": "0","male": "","female": "","wowma_catid": "404909","wowma_catname": "スポーツ・アウトドア＞水泳＞男性用スイムウェア・競泳水着","qoo_catid": "300002279","qoo_catname": "メンズファッション_アウター_パーカー・トレーナー","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct678": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct679": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct680": {"ctname": "オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057466","sex": "0","male": "","female": "","wowma_catid": "500524","wowma_catname": "メンズファッション＞ジャケット・アウター＞トレンチコート","qoo_catid": "300000059","qoo_catname": "メンズファッション_アウター_Aライン・ピーコート","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct681": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 半袖 > 半袖シャツ一般 > Mサイズ", "y_ct": "2084064183","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ","s_keyword": "メンズ 長袖 カジュアル ビジネス レディース ワンピース 下着 秋冬 冬 白 厚手 ストライプ 柄 ブランド 無地 ノーアイロン ビジネスカジュアル セット スリム 紺色 黒 チェック 形状記憶 襟付き オフィス コーデュロイ vネック 3l ヒートテック 4l ランニング ノースリーブ ロング きれいめ ミニ キッズ 赤 青 アイロン 暖かい アイロン不要 アニメ インナー 犬 イタリアンカラー 衣装 インク 裏起毛 ウィメンズ"},
        "ct682": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 長袖 > 長袖シャツ一般 > Mサイズ", "y_ct": "2084064178","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ","s_keyword": "メンズ 長袖 カジュアル ビジネス レディース ワンピース 下着 秋冬 冬 白 厚手 ストライプ 柄 ブランド 無地 ノーアイロン ビジネスカジュアル セット スリム 紺色 黒 チェック 形状記憶 襟付き オフィス コーデュロイ vネック 3l ヒートテック 4l ランニング ノースリーブ ロング きれいめ ミニ キッズ 赤 青 アイロン 暖かい アイロン不要 アニメ インナー 犬 イタリアンカラー 衣装 インク 裏起毛 ウィメンズ"},
        "ct685": {"ctname": "オークション > ファッション > メンズファッション > カーディガン", "y_ct": "2084007052","sex": "0","male": "","female": "","wowma_catid": "501103","wowma_catname": "メンズファッション＞学生服＞スクールニット・カーディガン","qoo_catid": "300002278","qoo_catname": "メンズファッション_アウター_カーディガン","s_keyword": "メンズ 冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct803": {"ctname": "オークション > ファッション > メンズファッション > シャツ > その他の袖丈", "y_ct": "2084054038","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ","s_keyword": "メンズ 長袖 カジュアル ビジネス レディース ワンピース 下着 秋冬 冬 白 厚手 ストライプ 柄 ブランド 無地 ノーアイロン ビジネスカジュアル セット スリム 紺色 黒 チェック 形状記憶 襟付き オフィス コーデュロイ vネック 3l ヒートテック 4l ランニング ノースリーブ ロング きれいめ ミニ キッズ 赤 青 アイロン 暖かい アイロン不要 アニメ インナー 犬 イタリアンカラー 衣装 インク 裏起毛 ウィメンズ"},
        "ct804": {"ctname": "オークション > ファッション > メンズファッション > トレーナー > Mサイズ", "y_ct": "2084057461","sex": "0","male": "","female": "","wowma_catid": "500712","wowma_catname": "メンズファッション＞トップス＞トレーナー・スウェット","qoo_catid": "300002279","qoo_catname": "メンズファッション_アウター_パーカー・トレーナー","s_keyword": "メンズ 裏起毛 ブランド おしゃれ 冬 長袖 オーバーサイズ レディース ゆったり チャンピオン 韓国 キッズ ジュニア 白 上下 160 グレー 5l 4l 3l オシャレ 6l 厚手 無地 大きい 黒 ザ ベビー ベージュ パーカー 2xl 緑 茶 男の子 女の子 150 140 130 ユッタリ ロング かわいい 赤 青 アニメ イラスト 犬 犬柄 インナー"},
        "ct805": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619","sex": "0","male": "","female": "","wowma_catid": "500808","wowma_catname": "メンズファッション＞パンツ・ボトムス＞スラックス","qoo_catid": "300002302","qoo_catname": "メンズファッション_ビジネス・フォーマル_パンツ・スラックス","s_keyword": "メンズ 冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct806": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ", "y_ct": "2084053072","sex": "0","male": "","female": "","wowma_catid": "500801","wowma_catname": "メンズファッション＞パンツ・ボトムス＞その他パンツ・ボトムス","qoo_catid": "300000066","qoo_catname": "メンズファッション_インナー・靴下_ボクサーパンツ","s_keyword": "メンズ 冬 メンズ防寒 レディース ー タンクトップ レディース レディースよネック府 レディース暖かい レディース上下 サッカー キッズ 裏起毛 長袖 ジュニア the north freon pocket専用 電熱 上下セット 13箇所発熱 電熱パンツ"},
        "ct807": {"ctname": "オークション > ファッション > メンズファッション > 水着 > Mサイズ", "y_ct": "2084051835","sex": "0","male": "","female": "","wowma_catid": "501201","wowma_catname": "メンズファッション＞水着＞その他水着","qoo_catid": "300002298","qoo_catname": "メンズファッション_その他メンズファッション_水着","s_keyword": "レディース メンズ フィットネス 体型カバー レディース 競泳 セパレート 男性 ビキニ ワンピース タンキニ セット ラッシュガード 上下 練習用 インナー アリーナ スピード 50代 40代 50代大きい 60代 3l 体型カバーsale エレッセ スピードセパレート arena 半袖 フィラ セパレートミズノ ショート ボックス fina認証 ジム 上 男性用 穴あき アンダーショーツ アンダー 赤ちゃん インナーショーツ いんなーパンツ tバック インナーパンツ 上着 上だけ うえだけ 上に羽織る"},
        "ct120": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471","sex": "0","male": "","female": "","wowma_catid": "320708","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ペチコート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "レディース メンズ 冬 ハンガー 掛け レディース冬 ビジネス おしゃれ かわいい ロング カシミヤ 黒 綺麗 防寒 カジュアル チェスター ベージュ ブランド ショート スリム 木製 ハンガーラック 壁掛け 玄関 山崎実業 壁 軽い ダウン aライン スタンド フック 傷つけない 突っ張り レディース冬 レディース冬物 レディース冬軽い レディース冬ロング レディース冬ブランド ダッフル レディース冬モコモコ ビジネスカジュアル トレンチ ハーフ ウール"},
        "ct689": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ライダース", "y_ct": "2084243900","sex": "0","male": "","female": "","wowma_catid": "510330","wowma_catname": "レディースファッション＞アウター＞ライダースジャケット","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct690": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct691": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084057481","sex": "0","male": "","female": "","wowma_catid": "510324","wowma_catname": "レディースファッション＞アウター＞ブルゾン","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct692": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャケット、ブレザー > Mサイズ", "y_ct": "2084057476","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct693": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0","male": "","female": "","wowma_catid": "510309","wowma_catname": "レディースファッション＞アウター＞スタンドカラージャケット・コート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct694": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471","sex": "0","male": "","female": "","wowma_catid": "320708","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ペチコート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 ハンガー 掛け レディース冬 ビジネス おしゃれ かわいい ロング カシミヤ 黒 綺麗 防寒 カジュアル チェスター ベージュ ブランド ショート スリム 木製 ハンガーラック 壁掛け 玄関 山崎実業 壁 軽い ダウン aライン スタンド フック 傷つけない 突っ張り レディース冬 レディース冬物 レディース冬軽い レディース冬ロング レディース冬ブランド ダッフル レディース冬モコモコ ビジネスカジュアル トレンチ ハーフ ウール"},
        "ct695": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > スカジャン", "y_ct": "2084052541","sex": "0","male": "","female": "","wowma_catid": "510307","wowma_catname": "レディースファッション＞アウター＞スカジャン","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct696": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジージャン > Mサイズ", "y_ct": "2084054383","sex": "0","male": "","female": "","wowma_catid": "510317","wowma_catname": "レディースファッション＞アウター＞デニムジャケット","qoo_catid": "300000041","qoo_catname": "レディースファッション_アウター_ジャンパー・ブルゾン","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct1022": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct163": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー","s_keyword": "長袖 vネック ハイネック ワッフル 厚手 ボーダー おしゃれ 秋冬 大きい レディース タートルネック 冬 きれいめ 白 ゆったり 秋 ショート スーツ オフィス 綿 秋冬もの 4l 3l 7分袖 モノトーン キッズ ロングスリーブ ベビー コットン 赤 アシンメトリー アーノルド パーマー あったか 青 インナー 裏起毛 ウール 裏起毛冬レディース 柄 襟付き 柄レディース 映画 女の子 オーバーサイズ オフショル オレンジ 重ね着"},
        "ct1108": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー","s_keyword": "長袖 vネック ハイネック ワッフル 厚手 ボーダー おしゃれ 秋冬 大きい レディース タートルネック 冬 きれいめ 白 ゆったり 秋 ショート スーツ オフィス 綿 秋冬もの 4l 3l 7分袖 モノトーン キッズ ロングスリーブ ベビー コットン 赤 アシンメトリー アーノルド パーマー あったか 青 インナー 裏起毛 ウール 裏起毛冬レディース 柄 襟付き 柄レディース 映画 女の子 オーバーサイズ オフショル オレンジ 重ね着"},
        "ct698": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー","s_keyword": "長袖 vネック ハイネック ワッフル 厚手 ボーダー おしゃれ 秋冬 大きい レディース タートルネック 冬 きれいめ 白 ゆったり 秋 ショート スーツ オフィス 綿 秋冬もの 4l 3l 7分袖 モノトーン キッズ ロングスリーブ ベビー コットン 赤 アシンメトリー アーノルド パーマー あったか 青 インナー 裏起毛 ウール 裏起毛冬レディース 柄 襟付き 柄レディース 映画 女の子 オーバーサイズ オフショル オレンジ 重ね着"},
        "ct699": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > その他", "y_ct": "2084051324","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct700": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1102": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct704": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct701": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > イラスト、キャラクター", "y_ct": "2084051314","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct702": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1107": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct703": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1111": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > 柄もの", "y_ct": "2084051321","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1112": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > 文字、ロゴ", "y_ct": "2084051317","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct705": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 量産型 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct706": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct707": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct708": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct1045": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct1044": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct709": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct710": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct711": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct715": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct712": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct713": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct714": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 半袖 > Mサイズ", "y_ct": "2084064237","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct716": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 袖なし、ノースリーブ > ノースリーブシャツ一般", "y_ct": "2084027443","sex": "0","male": "","female": "","wowma_catid": "510812","wowma_catname": "レディースファッション＞トップス＞ノースリーブ","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct717": {"ctname": "オークション > ファッション > レディースファッション > キャミソール", "y_ct": "2084064258","sex": "0","male": "","female": "","wowma_catid": "510806","wowma_catname": "レディースファッション＞トップス＞キャミソール","qoo_catid": "300000012","qoo_catname": "レディースファッション_トップス_キャミソール・タンクトップ","s_keyword": "レディース 綿100 レース セット ロング 可愛い シルク カップ付き 激安 赤 大きい 白 上下 中学生 綿 4l 5l 冬 黒 ピンク 見せる インナー ワンピース 秋冬 ミニ サテン ロングレディース タイト 授乳 産後 ベルメゾン 2枚セット あったか 犬印 セットアップ 透け 長め シルク100 シルクサテン 暖かい 汗取り 穴あき 温かい あったかい いちご 裏起毛 薄手 ウイング"},
        "ct719": {"ctname": "オークション > ファッション > レディースファッション > チュニック > 袖なし、ノースリーブ > Mサイズ", "y_ct": "2084231772","sex": "0","male": "","female": "","wowma_catid": "510810","wowma_catname": "レディースファッション＞トップス＞チュニック","qoo_catid": "300002253","qoo_catname": "レディースファッション_トップス_チュニック","s_keyword": "レディース 冬 オシャレ 裏起毛 ニット 大きい 暖かい 3l 冬フリース 冬小さいサイズ 秋冬 きれいめ 60代 50代 ミセス ピンク ハイネック ブランド チェック エプロン おしゃれ 保育士 長袖 エプロン割烹着 レディース冬物 ワンピース ワンピース秋冬 ミニ オフショルダー 40代 黒 冬用 大きいサイズニット ブラウス ブラウス長袖 ブラウス秋冬 白 赤 あったか 秋 インナー ルームウェア ウエスト ウール 裏ボア 冬裏起毛 柄 防水 襟付き エプロン長袖"},
        "ct1110": {"ctname": "オークション > ファッション > レディースファッション > チューブトップ、ベアトップ", "y_ct": "2084243344","sex": "0","male": "","female": "","wowma_catid": "510816","wowma_catname": "レディースファッション＞トップス＞ベアトップ・チューブトップ","qoo_catid": "320001136","qoo_catname": "下着・レッグウェア_キャミソール・ペチコート_ベアトップ・チューブトップ","s_keyword": "レース スパンコール セット ブラジャー フリル ショーツ オレンジ 透明ストラップ ダンス 子供 ひも外せる 120 140 110 肌色 子ども カップなし ラメ フラダンス おすすめ 5l 赤 穴あき 水着 盛れる ワンピース 暖かい 青 温かい あったかい あったか インナー 衣装 裏起毛 薄手 エナメル 柄 演奏会 エクササイズ おおきいサイズ 落ちない 大きい おしゃれ"},
        "ct162": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct720": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct721": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct722": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct723": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct724": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct725": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct726": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct727": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct122": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct728": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct1008": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161","sex": "0","male": "","female": "","wowma_catid": "511011","wowma_catname": "レディースファッション＞パンツ＞スパッツ・レギンス","qoo_catid": "300000047","qoo_catname": "レディースファッション_パンツ_レギンス","s_keyword": "レディース 冬 タイツ 裏起毛 スポーツ マタニティ munny パンツ 7分丈 綿 柄 オシャレ 5分丈 ヨガ 防寒 ランニング 7部丈 靴下屋 ベージュ レディースユニクロ 肌色 レザー おおきいサイズ 300デニール 皮 ゆったり デニム 2l 裏起毛ひざ下 寒 ７分 大きい スポーツ5分丈 裏起毛s チェック ジュニア コールドギア キッズ 2.0 トレーニング/men ヒートギア べるみす 着圧 あったか 暖かい 穴あき 厚手 赤ちゃん"},
        "ct1009": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "レディース レッドキャップ 裏起毛 冬 ストレッチ ゆったり 冬用 カーゴ 874 大きい 青 チノパン デニム 作業用 グレー 防風 作業 ハイウエスト ネイビー pt20 pt50 白 防水 アヴィレックス 赤 アメカジ 厚手 アウトドア カーゴパンツ ズボン 作業服 ゆったりポケット 綿 裏ボア 頑丈 ポケット多い 洗えるベルト付き オレンジ おしゃれ オリーブ カーキ カジュアル レッドきゃっぷ 黒 紺 作業着 スリム"},
        "ct1010": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "レディース レッドキャップ 裏起毛 冬 ストレッチ ゆったり 冬用 カーゴ 874 大きい 青 チノパン デニム 作業用 グレー 防風 作業 ハイウエスト ネイビー pt20 pt50 白 防水 アヴィレックス 赤 アメカジ 厚手 アウトドア カーゴパンツ ズボン 作業服 ゆったりポケット 綿 裏ボア 頑丈 ポケット多い 洗えるベルト付き オレンジ おしゃれ オリーブ カーキ カジュアル レッドきゃっぷ 黒 紺 作業着 スリム"},
        "ct1047": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct738": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct739": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct740": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct741": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > その他", "y_ct": "2084007171","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct742": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > タイトスカート > Mサイズ", "y_ct": "2084222253","sex": "0","male": "","female": "","wowma_catid": "510605","wowma_catname": "レディースファッション＞スカート＞タイトスカート","qoo_catid": "300002247","qoo_catname": "レディースファッション_スーツ_スカートスーツ","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct743": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct744": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > プリーツスカート > Mサイズ", "y_ct": "2084222283","sex": "0","male": "","female": "","wowma_catid": "510612","wowma_catname": "レディースファッション＞スカート＞プリーツスカート","qoo_catid": "300002859","qoo_catname": "レディースファッション_スカート_ミディアムスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct745": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > フレアースカート、ギャザースカート > Mサイズ", "y_ct": "2084222278","sex": "0","male": "","female": "","wowma_catid": "510603","wowma_catname": ""},
    }
