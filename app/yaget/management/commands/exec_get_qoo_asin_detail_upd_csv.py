# -*- coding:utf-8 -*-
import time
import sys, codecs

from django.core.management.base import BaseCommand
import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import re
import lxml.html
import logging
#import logging.handlers
import logging.config
from logging import getLogger, config
import traceback
import subprocess
from time import sleep
import urllib.request
import os, socket
import io,sys
from threading import Timer
import requests

from yaget.integrations.chrome_driver import CommonChromeDriver
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import (
    YaShopListUrl,
    YaShopItemList,
    QooAsinDetail,
)
from yaget.AmaSPApi import AmaSPApi, AmaSPApiAsinDetail, AmaSPApiQooAsinDetail
from yaget.integrations.batch_status import BatchStatusUpd

# 2022/7/13 指定したASINのリスト（CSV）を読み込んで、対象のASIN詳細を全部取ってきて保存する。
# リクエスト制限を気にしないと。
# ListMatchingProducts
# 時間あたりのリクエストクォータ:20リクエスト
# 回復レート:5秒あたり1回のリクエスト
# 最大リクエストクォータ:1時間あたり720リクエスト

#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# log設定はconfigに
# logging.config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail.config", disable_existing_loggers=False)

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

USER_DATA_DIR = '/app/yaget/userdata/'

#logging.config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail_upd_csv.config", disable_existing_loggers=False)
#logging.config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail_upd_csv.config", disable_existing_loggers=True)
# logger.setLevel(20)  # info
#logger = getLogger(__name__)
#logger.setLevel(logging.DEBUG)


# ログローテ設定

rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/management/commands/log/exec_qoo_asin_detail_upd_csv.log',
    encoding='utf-8',
    maxBytes=3000000,
    backupCount=5
)
fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
rh.setFormatter(fh_formatter)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(ch_formatter)

logger = getLogger(__name__)
logger.addHandler(rh)
logger.addHandler(ch)


# logger.setLevel(logging.DEBUG)


# 共通変数
mydwsrc_dir = "/app/yaget/ama_dwsrc"


def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.logger = logger
        # self.logger = logging.getLogger(__name__)
        # logging.config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail_upd_csv.config", disable_existing_loggers=False)
        self.logger.setLevel(logging.DEBUG)
        # self.logger = logging.getLogger(__name__)

        self._ama_spapi_qoo_ojb = None
        self.common_chrome_driver = None

        help = 'get asin info for qoo10'
        # self.logger.info('exec_get_qoo_asin_detail_upd_csv Command in. init')
        self.logger.debug('exec_get_qoo_asin_detail_upd_csv Command in(debug). init')
        logger.debug('exec_get_qoo_asin_detail_upd_csv Command in(debug)_ only logger. init')
        self.test_msg()

    # 本内容は、test_amsrc_1.py のselenium の使い方にある。

    def test_msg(self):
        self.logger.debug('exec_get_qoo_asin_detail_upd_csv Command > test_msg ok')

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('--csv_no', nargs='?', default='', type=str)
        # parser.add_argument('csv_no', nargs='+')
        # parser.add_argument('csv_no')
        parser.add_argument('--pk', type=int)
        parser.add_argument('--asin')

    def get_asin_by_keyword(self, bid, gid, keyword):
        try:
            # SP-API呼び出しでマッチするASINの詳細を取ってみたい。
            self.logger.debug('get_asin_by_keyword in. init   AmaSPApiQooAsinDetail:')
            ama_spapi_ojb = AmaSPApiQooAsinDetail(self.logger, bid, gid, keyword)
            self.logger.debug('start  get_asin_by_keyword gid:[' + str(gid) + ']')
            if ama_spapi_ojb.spapi_list_item_by_keyword() is True:
                # セットするDBはyahoo shopping 輸入用でいちおう分ける。bidに、ショップ名が入るだけ
                #ama_spapi_ojb.set_shop_import_list_matched_product_all()

                # 以下は組み替えないといけない。xml分解してDB格納してる。
                # セットするDBはyahoo shopping 輸入用でいちおう分ける。bidに、ショップ名が入るだけ
                #ama_spapi_ojb.set_shop_import_list_matched_product_all()


                # 一通り格納できたら少しwait
                self.logger.debug('set_shop_import_list_matched_product_all:ok')
                time.sleep(1)
        except Exception as e:
            t, v, tb = sys.exc_info()
            self.logger.debug('get_asin_by_keyword except:{0}'.format(str(traceback.format_exception(t, v, tb))))
            self.logger.debug('get_asin_by_keyword except_add:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            print("get_asin_by_keyword message:{0}".format(str(e)))
        return

    # Yahoo輸入版＋csvでカテゴリ指定した場合。db_entryを渡す
    def get_asin_by_keyword_from_csv(self, bid, gid, keyword, db_entry):
        try:

            # MWS呼び出しでマッチするASINを取ってみたい。
            self.logger.debug('get_asin_by_keyword_from_csv in. init   AmaSPApi:')
            ama_spapi_ojb = AmaSPApi(self.logger, bid, gid, keyword, db_entry)
            self.logger.debug('start  get_asin_by_keyword_from_csv gid:[' + str(gid) + ']')
            if ama_spapi_ojb.spapi_list_item_by_keyword() is True:
                # 一通り格納できたら少しwait
                self.logger.debug('spapi_list_item_by_keyword: ok')
                time.sleep(2)
            else:
                # エラー？
                self.logger.debug('spapi_list_item_by_keyword: ng?')
                time.sleep(2)

            """
            if ama_spapi_ojb.get_list_matching_products() is True:
                # セットするDBはyahoo shopping 輸入用でいちおう分ける。bidに、ショップ名が入るだけ
                ama_spapi_ojb.set_shop_import_list_matched_product_all()
            """
        except Exception as e:
            t, v, tb = sys.exc_info()
            self.logger.info('get_asin_by_keyword_from_csv except:{0}'.format(str(traceback.format_exception(t, v, tb))))
            # self.logger.info('get_asin_by_keyword_from_csv except add:{0}'.format(str(traceback.format_exception(t,v,tb))))
            self.logger.info('get_asin_by_keyword_from_csv except_add:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            print("get_asin_by_keyword_from_csv message:{0}".format(str(e)))
        return

    def get_asin_from_ama_site(self, asin, url):
        # 指定されたasinに対してamazonのサイトでスクレイピングをかける

        self.logger.debug('get_asin_from_ama_site in. init.')

        try:
            # ss_url = 'https://buyerz.shop/shop/shopbrand.html?page=1&search=&sort=&money1=&money2=&prize1=&company1=&content1=&originalcode1=&category=&subcategory='
            my_url = 'https://www.amazon.co.jp/dp/' + asin + '/ref=nav_logo'
            # my_url = 'https://www.amazon.co.jp/s?k=' + asin

            self.logger.debug('get_asin_from_ama_site url:[{}]'.format(my_url))

            self.common_chrome_driver = CommonChromeDriver(self.logger)
            #self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            self.common_chrome_driver.init_chrome_with_tor()

            self.common_chrome_driver.driver.delete_all_cookies()

            self.common_chrome_driver.driver.get(my_url)
            s = self.common_chrome_driver.driver.page_source
            #self.logger.debug(s)


            # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')

            # 以下はソースをローカルに保存する場合
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = 'ama_src.txt'
            #tfilename = tstr + '_y_src_' + str(tmpitemcd[0]) + '.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename


            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()
            # self.common_chrome_driver.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい

            # 保存したファイル読み込み
            f_read = codecs.open(tfpath, 'r', 'utf-8')
            s = f_read.read()
            dom = lxml.html.fromstring(s)
            self.logger.debug('===> start read dom.')

            # ※検索結果から詳細ページに遷移してみる  span[contains(@id,'a-autoid-')
            # self.logger.debug(dom.xpath("//div[contains(@class,'s-product-image-container')]")[0].text)

            # タイトル
            self.logger.debug(dom.xpath("//span[@id='productTitle']")[0].text)

            # meta description
            self.logger.debug('===> meta description')
            self.logger.debug(dom.xpath("//meta[@name='description']")[0].get('content'))

            # 商品の詳細（ない場合もある）
            self.logger.debug('===> product detail')
            product_overview_features = dom.xpath("//div[@id='productOverview_feature_div']/div/table/tbody/tr")
            if len(product_overview_features) > 0:
                self.logger.debug('===> product_overview_features len[{}]'.format(len(product_overview_features)))
                for i_0, j_0 in enumerate(product_overview_features):
                    j_0_items = j_0.findall('td')
                    if len(j_0_items) > 0:
                        for i_0_0, j_0_0 in enumerate(j_0_items):
                            # self.logger.debug('===> j_0_0_items item[{}]'.format(j_0_0))
                            self.logger.debug('===> product_overview_features item[{}] text[{}]'.format(i_0_0,j_0_0.find('span').text))

            # 商品特徴
            feature_bullets = dom.xpath("//div[@id='feature-bullets']/ul/li/span")
            self.logger.debug('===> feature_bullets len[{}]'.format(len(feature_bullets)))
            for i_1, j_1 in enumerate(feature_bullets):
                self.logger.debug('===> feature_bullets item[{}] text[{}]'.format(i_1,j_1.text))

            # 画面下部_詳細情報（ない場合もある）
            productDetails_techSpec_section_1 = dom.xpath("//table[@id='productDetails_techSpec_section_1']/tbody/tr")
            if len(productDetails_techSpec_section_1) > 0:
                self.logger.debug('===> productDetails_techSpec_section_1 len[{}]'.format(len(productDetails_techSpec_section_1)))
                for i_2, j_2 in enumerate(productDetails_techSpec_section_1):
                    self.logger.debug('===> productDetails_techSpec_section_1 item[{}] th_text[{}]'.format(i_2,j_2.find('th').text))
                    self.logger.debug('===> productDetails_techSpec_section_1 item[{}] td_text[{}]'.format(i_2,j_2.find('td').text))

            # 画面下部_商品の説明
            # https://www.amazon.co.jp/dp/B08FC6K5J2/ref=b2b_gw_d_bmx_gp_41ac8gqo_sccl_5/358-8809905-4375650
            productDescription = self.logger.debug(dom.xpath("//div[@id='productDescription']/p/span"))
            if productDescription and len(productDescription) > 0:
                self.logger.debug('===> productDescription len[{}]'.format(len(productDescription)))
                for i_3, j_3 in enumerate(productDescription):
                    self.logger.debug('===> productDescription item[{}] text[{}]'.format(i_3,j_3.text))

            # サムネイル画像
            # span id = a-autoid-10-announce という具合だが、連番はどこからついているか分からない。
            img_tags = dom.xpath("//span[contains(@id,'a-autoid-') and contains(@id,'-announce')]/img/@src")
            if len(img_tags) > 0:
                self.logger.debug('===> img_tags len[{}]'.format(len(img_tags)))
                for i_4, j_4 in enumerate(img_tags):
                    self.logger.debug('===> img_tags item[{}] td_text[{}]'.format(i_4,j_4))
                    chk_str = re.sub(r'(.+?_AC_)(.+?)(_.jpg)', r'\1L1500\3', j_4)
                    self.logger.debug('===> img_tags chk_str[{}]'.format(chk_str))


            # 画像リンクを別ウィンドウ呼び出しで格納する
            # dom.xpath("//div[@id='productTitle']")[0].find('a').attrib['href'].click() # 拡大画像のポップアップリンク
            # self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").click()
            # self.logger.debug(' popup_href[' + str(dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href']) + ']') # 拡大画像のポップアップリンク

            # 終わったらファイル閉じ
            f_read.close()
            if self.common_chrome_driver.driver is not None:
                self.common_chrome_driver.driver.close()  # closeはフォーカスがあたってるブラウザを閉じるらしい                self.logger.debug(traceback.format_exc())

        except Exception as e:
            if self.common_chrome_driver.driver is not None:
                self.common_chrome_driver.driver.close()  # closeはフォーカスがあたってるブラウザを閉じるらしい                self.logger.debug(traceback.format_exc())
            self.logger.info('webdriver error occurred start retry..')

        # 現状はとくにDBに保存もしてない。取ってみてるだけ・・・
        self.logger.info('get_asin_from_ama_site end.')
        return

    # Qoo10用に指定されたASINの詳細情報を取得する
    # 取り込み時は国内SP-APIより。
    # ブラックリストでチェックもかける。
    def get_asin_info_for_qoo10(self, asin):
        try:
            # SP-API呼び出しでマッチするASINを取ってみたい。
            self.logger.debug('get_asin_info_for_qoo10 in. init.')

            # 現状は必要ない
            # my_url = 'https://www.amazon.co.jp/dp/' + asin + '/ref=nav_logo'
            # self.get_asin_from_ama_site(asin, my_url)

            # SP-APIとスクレイピングを重ねて情報取得するのはこちら
            # 使うクラスは AmaSPApiQooAsinDetail
            # 2057行目以降の　spapi_get_catalog_item_for_all　を呼んでるので注意
            if self._ama_spapi_qoo_ojb.spapi_get_catalog_item_for_all(
                    'jp', asin) is True:
                # 一通り格納できたら少しwait
                self.logger.debug('get_asin_info_for_qoo10: spapi_get_catalog_item_for_all ok')
                time.sleep(2)
            else:
                # エラー？
                self.logger.debug('get_asin_info_for_qoo10: spapi_get_catalog_item_for_all ng?')
                time.sleep(2)

        except Exception as e:
            t, v, tb = sys.exc_info()
            self.logger.info('get_asin_info_for_qoo10 except:{0}'.format(str(traceback.format_exception(t, v, tb))))
            self.logger.info('get_asin_info_for_qoo10 except_add:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            print("get_asin_info_for_qoo10 message:{0}".format(str(e)))

        self.logger.debug('get_asin_info_for_qoo10 out.')
        return

    # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):
        try:
            self.logger.info('exec_get_asin_detail_upd_csv handle is called (self) info')
            self.logger.debug('exec_get_asin_detail_upd_csv handle is called (self) debug')
            logger.debug('exec_get_asin_detail_upd_csv handle is called (self) debug(only_logger)')
            print('exec_get_asin_detail_upd_csv handle is called (self) debug(only_logger)')

            self.batch_status = BatchStatusUpd('exec_get_qoo_asin_detail_upd_csv')
            self.batch_status.start()

            # for myopt in options:
            #    self.logger.debug('opt:' + str(myopt))

            self.logger.debug('csv_no:' + options['csv_no'])
            self.logger.debug('asin:' + str(options['asin']))

            self._ama_spapi_qoo_ojb = AmaSPApiQooAsinDetail(self.logger)


            # self.common_chrome_driver = CommonChromeDriver(self.logger)

            # self.common_chrome_driver.driverにセット
            # self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            # self.common_chrome_driver.init_chrome_with_tor()


            # asin が指定されたら一つだけ実行
            if options['asin']:
                self.logger.debug('asin has been set. asin:{}'.format(options['asin']))
                # db_entry = QooAsinDetail.objects.get(asin=options['asin'])
                db_entry = QooAsinDetail.objects.filter(pk=options['asin']).first()

                if db_entry is None:
                    # まだ登録されてないASINの場合は、csv_noは0で登録する
                    db_entry, created = QooAsinDetail.objects.get_or_create(
                        asin=options['asin'],
                        defaults={
                            'csv_no': int(0),
                        },
                    )
                    if not created:
                        db_entry.csv_no = 0
                        db_entry.asin = options['asin']
                        db_entry.save()
                    self.logger.debug('db asin is new. created')

                else:
                    # 登録されてるはず
                    self.logger.debug('db ok.status:' + str(db_entry.status))

                ss_url = db_entry.url
                db_entry.status = 1  # 処理中に
                db_entry.save()
                self.get_asin_info_for_qoo10(str(options['asin']))

                # ここまで来たらそのURLは処理完了ということにしよう
                db_entry = QooAsinDetail.objects.filter(pk=options['asin']).first()
                db_entry.status = 2  # 完了に
                db_entry.save()

            else:
                # DBから指定されたcsv_noに該当するURLを取得し、
                # 順繰りに処理してゆく
                self.logger.debug('asin is null.')

                # db_entries = YaShopImportSpapiShopUrls.objects.all().filter(csv_no=options['csv_no'][0]).order_by("y_cat_1")
                db_entries = QooAsinDetail.objects.all()\
                    .filter(csv_no=options['csv_no'])\
                    .order_by("asin")

                if not db_entries:
                    # 指定されたcsv_no がNGだった
                    self.logger.debug('db_entries is null error return.')
                    print('[get_asin_detail_by_spapi_upd_csv handle]---> entered csv_no is illegal')
                    return
                else:
                    self.logger.debug('db_entries is ok.')
                    self.logger.debug('db_entries len:[' + str(len(db_entries)) + ']')


                    # DBから取れたレコードを順に処理
                    for db_entry in db_entries:
                        # 入り口がss_url、ペーネが存在する間は順に取得する
                        self.logger.debug('db_entry start.')
                        ss_url = db_entry.url
                        db_entry.status = 1  # 処理中に
                        db_entry.save()

                        #next_page = self._get_ya_shop_url_from_csv(ss_url, db_entry)

                        # ここまで来たらそのURLは処理完了ということにしよう
                        db_entry.status = 2  # 処理完了に
                        db_entry.save()



            # self.batch_status.end()
            self.logger.debug('get_asin_detail_by_spapi_upd_csv handle end')
            # self.stdout.write(self.style.SUCCESS('end of ya_get_src Command!'))

        except Exception as e:
            #self.logger.info(traceback.format_exc())
            self.logger.debug(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())

            """
            t, v, tb = sys.exc_info()
            self.logger.info('###### ya_imp_spqpi_upd_csv except occurred. :{0}'.format(str(traceback.format_exception(t, v, tb))))
            self.logger.info('ya_imp_spqpi_upd_csv except_add:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            print("ya_imp_spqpi_upd_csv message:{0}".format(str(e)))
            """
        self.batch_status.end()
        return
