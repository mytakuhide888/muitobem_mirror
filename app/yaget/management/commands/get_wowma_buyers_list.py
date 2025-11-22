# -*- coding:utf-8 -*-
"""
★ buyers_info の_MY_URLS_WOWMA　に登録されたバイヤーズのカテゴリにアクセスして
出品できる商品を取得、DBに格納する。

・取得した商品は、確認が必要なので　wow_on_flg、qoo_on_flg　を　（０　確認待ち）にしておく。
　CSVをダウンロードして、OKだったらアップして１にたおすこと。

・巡回中、在庫が０の商品は取り込まない。

"""
import time
import sys, codecs

from django.core.management.base import BaseCommand
import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import datetime
import re
import lxml.html
#import logging
import logging.config
import traceback
from time import sleep
import urllib.request
import os, socket
from threading import Timer
import requests
import csv
import glob
import shutil

sys.path.append('/app/yaget/management/commands')
from yaget.integrations.buyers_info import BuyersInfo, BuyersBrandInfo
from yaget.integrations.wowma_access import WowmaAccess
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.integrations.batch_status import BatchStatusUpd

# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import YaBuyersItemList, YaBuyersItemDetail


#from yaget.AmaMws import AmaMwsProducts

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/wowma_buyers_list_logging.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

#logger.setLevel(20)

# 共通変数
mydwsrc_dir = "/app/yaget/wowma_buyers/dwsrc"
mydwimg_dir = "/app/yaget/wowma_buyers/dwimg/"
myupdcsv_dir = "/app/yaget/wowma_buyers/updcsv/"

from_dwsrc_dir = "/app/eb_sample/enditem_file/to_upload"

UPLOAD_DIR = '/app/yaget/wowma_buyers/dwcsv/'
DONE_CSV_DIR = '/app/yaget/wowma_buyers/donecsv/'

USER_DATA_DIR = '/app/yaget/wowma_buyers/userdata/'

def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class Command(BaseCommand):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        help = 'get from wowma buyers list.'
        self.logger.debug('get_wowma_buyers_list Command in. init')
        self.common_chrome_driver = None
        self.driver = None
        self.upd_csv = []
        self.my_wowma_target_ct_list = []
        self.batch_status = None

    # 本内容は、test_amsrc_1.py のselenium の使い方にある。

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('s_url', nargs='+')

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

    # バイヤーズで取り込み対象のカテゴリ全てのリンクに対してアクセスし、
    # 登録されている商品情報をDBに書き込むまで。
    def _exec_get_buyers_list(self):

        # self.my_wowma_target_ct_list にあるカテゴリの分だけ順に処理するか
        #             result_y_ct = str(_MY_CT_CODES[ctcode]["y_ct"])
        for my_ct, my_value in self.my_wowma_target_ct_list.items():
         #   for ss_url in options['s_url']:
            # 入り口がss_url、ペーネが存在する間は順に取得する
            # 形式は　https://buyerz.shop/shopbrand/ct113/
            ss_url = "https://buyerz.shop/shopbrand/" + str(my_ct) + "/"
            pcount = 1
            while True:
                next_page = self._get_wowma_buyers_list(ss_url, str(my_ct), pcount)

                # いったん１ページ目で終わり
                next_page = False
                if not bool(next_page):
                    break
                # next_page が次ページのurlであることを期待している
                ss_url = next_page
                pcount += 1

            # 全部取得が完了したらcsvをファイル出力
            #self.write_csv()

        return

    # https://qiita.com/tomson784/items/88a3fd2398a41932762a 参照
    # 指定されたURLに対してバイヤーズの商品群を取得する
    # 渡される ss_url は　https://buyerz.shop/shopbrand/ct113/　の形式
    # ペーネすると、　https://buyerz.shop/shopbrand/ct113/page2/order/
    def _get_wowma_buyers_list(self, ss_url, my_ct, pcount):
        # self.stdout.write('ss_url:' + ss_url)
        # self.stdout.write(self.style.SUCCESS('my_s_url:' + s_url))
        self.logger.debug('_get_wowma_buyers_list in pcount:[' + str(pcount) + ']')
        self.logger.debug('_get_wowma_buyers_list in ssurl:[' + str(ss_url) + ']')
        self.logger.debug('_get_wowma_buyers_list in my_ct:[' + str(my_ct) + ']')


        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                #ss_url = 'https://buyerz.shop/shop/shopbrand.html?page=1&search=&sort=&money1=&money2=&prize1=&company1=&content1=&originalcode1=&category=&subcategory='
                self.common_chrome_driver.driver.get(ss_url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.info(traceback.format_exc())
                self.logger.info('webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                #self.restart_chrome()
                sleep(3)
            else:
                break

        # もしソースを一時保持するならここをON
        """
        tdatetime = dt.now()
        tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
        tfilename = tstr + '_y_src_' + str(pcount) + '.txt'
        tfpath = mydwsrc_dir + '/' + tfilename
        # f = open(tfpath, mode='w')
        f = codecs.open(tfpath, 'w', 'utf-8')

        f.write(self.common_chrome_driver.driver.page_source)
        # f.write(src_1)
        f.close()
        self.common_chrome_driver.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい
        """



        ### 読み込んだファイルをDBにかく
        # obj = YaShopListUrl(targeturl=ss_url, filename=tfilename)
        # obj.save()

        ### XML解析してリスト用のDBへ
        # yahoo shoppingの参考
        # https://store.shopping.yahoo.co.jp/krplaza-shop/search.html?n=100#CentSrchFilter1

        # 以下は仮にファイルに一度データを落としてる。
        # 読み込めるようになったら、ファイルに書かずにソースをそのまま、下記のsに渡す
        # self.common_chrome_driver.driver.page_source を渡せば良い
        # tfpath = mydwsrc_dir + '/20190921_215216_y_src_1.txt'



        #f_read = codecs.open(tfpath, 'r', 'utf-8')
        #s = f_read.read()
        #dom = lxml.html.fromstring(s)

        # ソースを戻りから読み込み
        dom = lxml.html.fromstring(self.common_chrome_driver.driver.page_source)
        #self.common_chrome_driver.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい


        # a_list = dom.xpath("//div[@class='th']/table/tbody/tr/td")  # <div id="web">の子要素の<li>の子要素の<a>をすべて抽出
        # shop urlをとってみる
        # //*[@id="TopSPathList1"]/ol/li[1]/a
        """
        tmpslink = dom.xpath("//div[@id='TopSPathList1']/ol/li[1]/a/@href")
        print('tmpslink')
        print(tmpslink[0])
        tmpsname = dom.xpath("//div[@id='TopSPathList1']/ol/li[1]/a")
        print('tmpsname')
        print(tmpsname[0].text_content())
        """

        # 以下が個別の商品群
        # tmpdivs = dom.xpath("//div[@class='th']/table/tbody/tr/td/a")
        #tmpdivs = dom.xpath("//div[@id='r_searchList']/ul/li/div")
        tmpdivs = dom.xpath("//div[@class='innerBox']")
        tmpglink = ''

        self.logger.debug('start break item list.')
        self.logger.debug('tmpdivs:' + str(len(tmpdivs)))

        mydomain = 'https://buyerz.shop'

        for i, j in enumerate(tmpdivs):
            self.logger.debug('i:[' + str(i) + '] detail[' + str(len(j.find_class('detail'))) + ']')
            #tmp_td_obj = list(j)
            # print(i)
            #self.logger.debug('list. i[' + str(i) + ']')
            #tmpglink = mydomain + str(j.find_class('imgWrap')[0].find('a').attrib['href'])
            #tmpgsrc = j.find_class('imgWrap')[0].find('a/img').attrib['src']
            tmpurl_path = str(j.find_class('detail')[0].find_class('name')[0].find('a').attrib['href'])
            tmpglink = mydomain + tmpurl_path
            tmpgsrc = j.find_class('imgWrap')[0].find('a/img').attrib['src']

            """
            self.logger.debug('tmpgsrc[' + str(tmpgsrc) + ']')
            self.logger.debug('detail[' + str(j.find_class('detail')[0]) + ']')
            self.logger.debug('detail[' + str(len(j.find_class('detail')[0].find_class('else')))+ ']')
            self.logger.debug('detail[' + str(len(j.find_class('detail')[0].find_class('else')[0].find('ul'))) + ']')
            self.logger.debug('detail[' + str(j.find_class('detail')[0].find_class('else')[0].find('ul')[1].text) + ']')
            """

            """
            tmpgid_1 = j.find_class('detail')[0].text # gコード
            tmpgid_2 = j.find_class('detail')[0].find_class('else')[0].text # gコード
            tmpgid_3 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].text # gコード
            self.logger.debug('tmpgid_3:[' + str(tmpgid_3) + ']')
            tmpgid_4 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].find('li').text # gコード
            self.logger.debug('tmpgid_4:[' + str(tmpgid_4) + ']')
            tmpgid_5 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].findall('li')[0].text # gコード
            self.logger.debug('tmpgid_5:[' + str(tmpgid_5) + ']')
            tmpgid_6 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].findall('li')[1].text # gコード
            self.logger.debug('tmpgid_6:[' + str(tmpgid_6) + ']')
            """

            # tmpgcd: 商品コード zbza153 など
            tmpgcd = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].findall('li')[1].text # gコード
            tmpgname = j.find_class('detail')[0].find_class('name')[0].find('a').text # 商品名
            #tmpgother = re.sub("\\D", "", str(tmpglink).rsplit("/", 1)[1])  # gコード

            #tmpbrandcd = re.sub("\\D", "", tmpurl_path)
            #tmpbrandcd = re.sub("\\d", "", str(tmpurl_path).rsplit("/", 1)[1])
            tmpbrandcd = str(tmpurl_path).split("/")[2]
            # ブランドコードは111始まりとする これがyahoo上の商品コードになる
            # tmpgid: 商品id 000000025633 など
            #         管理のために、B111 を接頭にして 111000000025633 とする
            tmpgid = str("B111") + str(tmpbrandcd)

            # ブラックリストの商品に該当してたら処理はしない
            black_list_obj = YaBuyersItemDetail.objects.filter(gid=tmpgid).filter(black_list__isnull=False).first()
            if black_list_obj:
                self.logger.debug('_get_wowma_buyers_list ブラックリストに該当したので処理しない gid:[{}]'.format(tmpgid))
                continue

            self.logger.debug('tmpurl_path:[' + str(tmpurl_path) + ']')
            self.logger.debug('glink:[' + str(tmpglink) + ']')
            self.logger.debug('gsrc:[' + str(tmpgsrc) + ']')
            self.logger.debug('gid:[' + str(tmpgid) + ']')
            self.logger.debug('gcd:[' + str(tmpgcd) + ']')
            self.logger.debug('gname:[' + str(tmpgname) + ']')
            self.logger.debug('tmpbrandcd:[' + str(tmpbrandcd) + ']')

            """
            self.logger.debug('glink:[' + str(tmpglink) + ']')
            self.logger.debug('gsrc:[' + str(tmpgsrc) + ']')
            self.logger.debug('gid:[' + str(tmpgid) + ']')
            self.logger.debug('gname:[' + str(tmpgname) + ']')
            self.logger.debug('tmpbrandcd:[' + str(tmpbrandcd) + ']')
            """

            # 不要文字削除
            #tmpgalt = re.sub('◆新品◆', "", tmpgalt)

            # ひとまず、リストの一件毎で詳細まで処理してみよう
            # ユニークにするのに、gidの形式がこれでいいかどうか確認すること

            # if not YaBuyersItemList.objects.filter(gid=tmpgid).exists():
            # 仮に、tmpgidあるなしに関わらずupsertしてみることに。
            self.logger.debug('start save YaBuyersItemList add.')

            new_obj = YaBuyersItemList.objects.filter(gid=tmpgid).first()
            if not new_obj:
                obj, created = YaBuyersItemList.objects.update_or_create(
                    gid=tmpgid,
                    gcd=tmpgcd,
                    my_ct=my_ct,
                    listurl=ss_url,
                    glink=tmpglink,
                    gname=tmpgname,
                    g_img_src=tmpgsrc,
                )
                obj.save()
            else:
                new_obj.gcd = tmpgcd
                new_obj.my_ct = my_ct
                new_obj.listurl = ss_url
                new_obj.glink = tmpglink
                new_obj.gname = tmpgname
                new_obj.g_img_src = tmpgsrc
                new_obj.save()

            # detailはここで取得してみる
            #if self._get_ya_buyers_detail(tmpglink) == False:
            if not self._get_wowma_buyers_detail(tmpglink, tmpgid, tmpgcd, ss_url, tmpgsrc, my_ct):
                # 途中でコケたら止めておこう
                self.logger.info('_get_wowma_buyers_detail. failed.')
                return False

            """
            if self._get_wowma_buyers_detail(tmpglink, tmpbrandcd, i) == False:
                # 途中でコケたら止めておこう
                return False

            if i == 0:
                break

            """

        # とりあえず1ページだけ
        #return False
        # ペーねが存在したら取得、終わっていたらfalse　を返却
        """
        tmp_nextpage_obj = dom.xpath("//li[@class='next']/a")
        if tmp_nextpage_obj is not None:
            if len(tmp_nextpage_obj) > 0:
                tmp_nextpage_href = tmp_nextpage_obj[0].attrib['href']
                if tmp_nextpage_href is not None:
                    time.sleep(5)
                    return tmp_nextpage_href
                else:
                    return False
            else:
                return False
        else:
            return False
        """
        self.logger.debug('end of _get_wowma_buyers_list')

        return False

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
                sleep(2)
            else:
                break


    # 詳細ページにアクセスしてECAUTOのカテゴリ設定用に編集する
    # ※画像は保存しない
    def _get_wowma_buyers_detail_for_ecauto(self, row):
        self.logger.debug('_get_wowma_buyers_detail_for_ecauto in.')

        try:
            # アイテムコードを画像URL ( row[5] ）から取ってくる
            tmpitemcd = re.findall('_(.+)_', row[5])
            if len(tmpitemcd[0]) < 7:
                self.logger.debug('_get_wowma_buyers_detail_for_ecauto row[5] itemcd is illegal.')
                self.logger.info('-----> _get_wowma_buyers_detail_for_ecauto  row[5][{}] itemcd is illegal.'.format(tmpitemcd[0]))
                return False

            d_url = "https://buyerz.shop/shopdetail/" + str(tmpitemcd[0]) + "/"
            self.logger.debug('--- d_url:{}'.format(d_url))

            # ページ取得
            self._get_page_no_tor(d_url)

            # 以下はソースをローカルに保存する場合
            """
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_' + str(tmpitemcd[0]) + '.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()
            """

            #self.common_chrome_driver.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい

            # ==============================
            # 商品詳細の各要素を取得する
            ng_flg = 0

            # =====
            # 商品名なども取ってこれるが、ひとまずrow[2]の商品名、row[4]の商品説明をそのまま使う
            #tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
            #tmpgid = re.sub('/', "", tmpgid)
            #tmpgname = self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='itemInfo']/h2").text
            #tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='itemInfo']/div[1]/div").text
            tmpgname = row[2]
            tmpgdetail = row[4]


            """
            tmpgname = re.sub('hbab', "", tmpgname)
            tmpgdetail = re.sub('hbab', "", tmpgdetail)
            tmpgdetail = re.sub('※ご入金いただいたご注文に関しましては、1～2日以内に発送いたします。', "", tmpgdetail)
            tmpgdetail = re.sub('※追跡番号あり。ゆうパケット【送料無料】【税込み】', "", tmpgdetail)
            """

            if len(self.common_chrome_driver.driver.find_elements_by_xpath("//li[@id='M_usualValue']/span")) == 0:
                # 価格が取れないときは在庫切れか
                self.logger.debug('_get_wowma_buyers_detail_for_ecauto cant get [M_usualValue].')
                tmpgspprice = ""
            else:
                tmpgspprice = self.common_chrome_driver.driver.find_element_by_xpath("//li[@id='M_usualValue']/span").text

            if len(self.common_chrome_driver.driver.find_elements_by_xpath("//span[@class='M_item-stock-smallstock']")) == 0:
                # 在庫が取れないときは在庫切れか
                self.logger.debug('_get_wowma_buyers_detail_for_ecauto cant get [M_item-stock-smallstock].')
                tmpgretail = ""
            else:
                tmpgretail = self.common_chrome_driver.driver.find_element_by_xpath("//span[@class='M_item-stock-smallstock']").text

            if len(self.common_chrome_driver.driver.find_elements_by_xpath("//div[@id='detailInfo']/ul/li[4]")) == 0:
                # 商品コードが取れないのはエラー
                self.logger.debug('_get_wowma_buyers_detail_for_ecauto cant get [detailInfo].')
                #self.logger.info('-----> _get_wowma_buyers_detail_for_ecauto cant get [detailInfo].')
                #return False
                tmpgcode = ""
            else:
                tmpgcode = self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='detailInfo']/ul/li[4]").text

            # カテゴリコードはとりあえず一つ。パンくずの末尾をとってみる
            tmpyct = ""
            tmpyct_flg = 0
            for ii in self.common_chrome_driver.driver.find_elements_by_xpath("//p[@class='pankuzu']/a"):
                # カテゴリ一致するかリスト引いて、マッチしたらそいつをセットしてループは抜ける
                tmpct =  ii.get_attribute('href') # 文字はちゃんと整形して

                self.logger.debug('===> tmpct 1:[{}]'.format(tmpct))

                # index は無視
                if re.search('index', tmpct):
                    self.logger.debug('===> tmpct:index hit. continue')
                    continue

                tmpct = re.sub('https://buyerz.shop/shopbrand/', "", tmpct)
                tmpct = re.sub('/', "", tmpct)

                self.logger.debug('===> tmpct:[{}]'.format(tmpct))

                tmpyct_obj = self.buinfo_obj.chk_ct(tmpct, tmpgname)
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

            if tmpyct_flg == 0 or tmpyct_flg == 3:
                tmpyct_key_obj = self.buinfo_obj.chk_ct_by_keyword(tmpgdetail, tmpgname)
                if tmpyct_key_obj:
                    tmpyct = str(tmpyct_key_obj)
                    tmpyct_flg = 2

            # ここでtmpyctが取れてない（""のまま）だったらNGか。
            if tmpyct == "":
                self.logger.debug('_get_wowma_buyers_detail_for_ecauto cant match tmpyct.')
                #self.logger.info('----- > _get_wowma_buyers_detail_for_ecauto cant match tmpyct.')
                #return False

            # 不要文字削除
            # 商品名より削除
            tmpgname_obj = None
            tmpgdetail_obj = None
            tmpgname_obj = self.bubrandinfo_obj.chk_goods_title(tmpgname)
            tmpgname = tmpgname_obj[0]
            if tmpgname_obj[1] == 1:
                ng_flg = 1

            # 不要文字削除
            # 商品説明より削除
            tmpgdetail_obj = self.bubrandinfo_obj.chk_goods_detail(tmpgdetail)
            tmpgdetail = tmpgdetail_obj[0]
            if tmpgdetail_obj[1] == 1:
                ng_flg = 1

            if tmpgdetail_obj[1] == 5:
                ng_flg = 1

            if tmpgdetail_obj[1] == 6:
                tmpyct_flg = 6 # NGワードが商品詳細に含まれる、要確認

            #self.logger.debug('gid:[' + str(tmpgid) + ']')
            self.logger.debug('gname:[' + str(tmpgname) + ']')
            self.logger.debug('gdetail:[' + str(tmpgdetail) + ']')
            self.logger.debug('gspprice:[' + str(tmpgspprice) + ']')
            self.logger.debug('gretail:[' + str(tmpgretail) + ']')
            self.logger.debug('gcode:[' + str(tmpgcode) + ']')
            self.logger.debug('tmpyct:[' + str(tmpyct) + ']')
            self.logger.debug('tmpyct_flg:[' + str(tmpyct_flg) + ']')

            # csvに登録
            # ※ まず、csvから読み込んだ一行をそのままコピーしておいて、こちらの値で上書きしないと。以下じゃだめ

            # 以下は例
            row[1] = str(tmpyct)
            row[2] = str(tmpgname)

            # NG扱いのブランドを row[3]に反映する
            if ng_flg == 1:
                tmpyct_flg = 5 # NG扱いということにしよう
                row[1] = '1111111' # deleteの際、カテゴリIDに文字が入ってるとECAUTOでエラーになるので数字にしておく
                row[2] = 'delete'

            # 本来、row[3]は「説明の入力（0/1)」だが仮に入れてみる
            # 1,2,3 →　カテゴリコードの優先順。3は見直し必要
            # 5 → NG。削除必須
            # 6 →　NGワードが商品詳細に含まれてるので要確認。商品詳細の冒頭も確認すること
            row[3] = str(tmpyct_flg)
            row[4] = str(tmpgdetail)
            """
            tmp_csv_row_dict = {
                'gname': str(tmpgname),
                'gdetail': str(tmpgdetail),
                'gspprice': str(tmpgspprice),
                'gretail': str(tmpgretail),
                'gcode': str(tmpgcode),
                'tmpyct': str(tmpyct),
                'tmpyct_flg': str(tmpyct_flg),
            }
            self.upd_csv.append(tmp_csv_row_dict)
            """
            self.upd_csv.append(row)

            # upd_csv を書き込まないと？

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
            self.logger.debug('_get_wowma_buyers_detail_for_ecauto popup_text[' + element.text + ']')
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
            self.logger.debug('_get_wowma_buyers_detail_for_ecauto popup_text[' + element.text + ']')
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
                    # DB書き込み
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
                        if self._get_wowma_buyers_detail(tmpglink) = False:
                            # 途中でコケたら止めておこう
                            return False
            """
        except Exception as e:
            self.logger.info(traceback.format_exc())
            self.logger.info('===> 行の処理中にエラー。おかしいのでエラーの商品として登録します')
            tmpyct_flg = 9 # 9をNG扱いということにしよう
            row[2] = 'delete'
            row[3] = str(tmpyct_flg) # 本来、row[3]は「説明の入力（0/1)」だが仮に入れてみる
            self.upd_csv.append(row)

        self.logger.debug('_get_wowma_buyers_detail_for_ecauto out.')
        return True


    # 詳細ページにアクセス
    # ss_url: リンク元リストページURL
    # gsrc: リストーページ中の商品サムネイル画像URL
    def _get_wowma_buyers_detail(self, d_url, gid, gcd, ss_url, gsrc, my_ct):
        self.logger.debug('_get_wowma_buyers_detail in. debug')
        self.logger.info('=====> _get_wowma_buyers_detail in.処理開始するgid:[{}]'.format(gid))

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

        # ===============================
        # 在庫数の抽出
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//span[@class='M_item-stock-smallstock']")) == 0:
            # 在庫が取れないときは在庫切れか
            self.logger.debug('_get_wowma_buyers_detail cant get [M_item-stock-smallstock].')
            tmpgretail = "0"
        else:
            tmpgretail = str(re.sub("\\D", "",
                                self.common_chrome_driver.driver.find_element_by_xpath(
                                    "//span[@class='M_item-stock-smallstock']").text))

        # もし在庫数が0だったら、後続の処理はせずDB登録もしない
        if tmpgretail == "0":
            return True

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
        #self.common_chrome_driver.driver.switch_to_window(handles[1])
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
            tmpimglist.append(tmpgsrc)

            tmp_g_img_src[tmp_cnt] = str(tmpgsrc).rsplit("?", 1)[0]
            #tmp_g_img_src[tmp_cnt] = str(tmpgsrc)
            tmp_cnt += 1

            """
            # 画像保存してみる
            myresponce = requests.get(tmpgsrc)
            if cnt == 0:
                tmpimgfname = str(gid)
            else:
                tmpimgfname = str(gid) + '_' + str(cnt)
            with open(mydwimg_dir + "{}.jpg".format(tmpimgfname), "wb") as myf:
                myf.write(myresponce.content)
            """

            cnt += 1
            if tmp_cnt == 20:
                break

        # 親のウィンドウに戻る
        #self.common_chrome_driver.driver.switch_to_window(handles[0])
        self.common_chrome_driver.driver.close()
        #self.common_chrome_driver.driver.switch_to_window(handles[0])
        self.common_chrome_driver.driver.switch_to.window(handles[0])

        # 商品詳細の各要素を取得する

        #tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        #tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 商品名
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//div[@id='itemInfo']/h2")) == 0:
            # とれなかったらエラー
            self.logger.info('_get_wowma_buyers_detail 商品名が取れないので登録しない.gid:[{}]'.format(gid))
            return True
        else:
            tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/h2").text

        # 商品詳細
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//div[@id='itemInfo']/div[1]/div")) == 0:
            # この形式の要素がない場合がある。
            if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                    "//div[@id='itemInfo']/div[1]")) == 0:
                # この場合はさすがにエラー。この商品は飛ばす
                self.logger.info('_get_wowma_buyers_detail 商品詳細が取れないので登録しない.gid:[{}]'.format(gid))
                return True
            else:
                # 要素があれば格納
                tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                    "//div[@id='itemInfo']/div[1]").text
        else:
            # 要素があれば格納
            tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/div[1]/div").text

        # =================================
        # 不要文字削除
        ng_flg = 0
        tmpyct_flg = 0
        # 商品名より削除
        tmpgname_obj = None
        tmpgdetail_obj = None

        tmpgname_obj = self.bubrandinfo_obj.chk_goods_title(tmpgname)

        # wowmaの商品名はひとまずこれにする。
        tmp_wow_gname = self.bubrandinfo_obj.cut_str(tmpgname_obj[0], 100)

        # 商品名のmaxは100文字とする
        # qoo10の商品名もひとまずこれにする。
        tmp_qoo_gname = self.bubrandinfo_obj.cut_str(tmpgname_obj[0], 100)

        # NGな商品であれば商品名からチェック結果を反映
        if tmpgname_obj[1] == 1:
            ng_flg = 1

        # バイヤーズの配送コードから、wowmaとqoo10の配送区分（無料かどうか）、配送コードを取得
        # 配送コードは 2(送料無料) か3（個別送料）
        tmp_postage_obj = self.bubrandinfo_obj.get_delivery_info(tmpgname_obj[0])
        tmp_postage_segment = tmp_postage_obj[0]

        tmpdeliveryid = tmp_postage_obj[1]
        tmp_qoo_deliveryid = tmp_postage_obj[2]

        # 不要文字削除
        # 商品説明より削除
        tmp_wow_worn_key = "" # もし注意文言があればここに格納する
        tmp_qoo_worn_key = "" # もし注意文言があればここに格納する
        tmpgdetail_obj = self.bubrandinfo_obj.chk_goods_detail(tmpgdetail)
        tmp_wow_gdetail = tmpgdetail_obj[0]
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
        # 利益額を、価格帯で変えてみる。
        tmp_wow_price = self.buinfo_obj.get_benefit_price(tmpgspprice, 1.15)

        # qoo10の価格を算出
        # qoo10も10%が手数料なので上乗せして、それに利益率を加える。
        # 利益額を、価格帯で変えてみる。
        tmp_qoo_price = self.buinfo_obj.get_benefit_price(tmpgspprice, 1.3)

        # wowmaは、チェック前は未出品にする(wow_on_flg:0 確認待ち)
        tmp_wow_upd_status = 0  # 未掲載
        tmp_wow_on_flg = 0  # 確認待ち

        # qooは、チェック前は未出品にする(qoo_on_flg:0 確認待ち)
        tmp_qoo_upd_status = 1  # 取引待機= 1、取引可能= 2、取引廃止= 3）
        tmp_qoo_on_flg = 0  # 確認待ち

        # もし商品名や商品詳細のチェックでNGになっていたらブラックリスト入にする。
        if ng_flg == 1:
            tmp_wow_on_flg = 2  # NG
            tmp_qoo_on_flg = 2  # NG

        tmpgcode = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='detailInfo']/ul/li[4]").text

        # ===================================================
        # カテゴリコード　チェック
        # カテゴリコードはとりあえず一つ。パンくずの末尾をとってみる
        # URL指定した際の、バイヤーズのカテゴリコードは my_ct で渡されている。
        tmpyct = ""
        tmpyct_flg = 0
        tmpyct_qoo = ""
        tmpyct_qoo_flg = 0

        """
        2021/10/10
        これまでは、パンくずに記載のあるカテゴリから引いてみたが
        URL指定の際に、既に指定されるカテゴリコードをリストと紐付けて一意で取ってみる形に。
        """
        # wowmaのカテゴリチェック
        tmpyct_obj = self.buinfo_obj.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        if tmpyct_obj:
            if tmpyct_obj[1] == 1:
                # サブカテゴリならそのまま採用
                tmpyct = tmpyct_obj[0] # intで返ってるはず
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
            tmpyct = 0
            tmpyct_flg = 3

        # qoo10のカテゴリチェック
        tmpyct_qoo_obj = self.buinfo_obj.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
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
            tmpyct_qoo = 0
            tmpyct_qoo_flg = 3

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

        if tmpyct_flg == 0 or tmpyct_flg == 3:
            tmpyct_key_obj = self.buinfo_obj.chk_ct_by_keyword_for_wowma(tmpgdetail, tmpgname)
            if tmpyct_key_obj:
                tmpyct = tmpyct_key_obj  # intのはず
                tmpyct_flg = 2
            else:
                tmpyct = 0
                tmpyct_flg = 2


        if tmpyct_qoo_flg == 0 or tmpyct_qoo_flg == 3:
            tmpyct_key_qoo_obj = self.buinfo_obj.chk_ct_by_keyword_for_qoo(tmpgdetail, tmpgname)
            if tmpyct_key_qoo_obj:
                tmpyct_qoo = tmpyct_key_qoo_obj
                tmpyct_qoo_flg = 2
            else:
                tmpyct_qoo = 0
                tmpyct_qoo_flg = 2

        # ここでtmpyctが取れてない（""のまま）だったらNGか。
        # しかしもったいないので、0のままDBは登録し、もし手作業で分かるならcsvでアップロードしよう。2022/2/3
        if tmpyct == 0:
            self.logger.info('_get_wowma_buyers_detail cant match tmpyct. 0 desita')
            # self.logger.info('----- > _get_wowma_buyers_detail_for_ecauto cant match tmpyct.')
            # return False
        if tmpyct_qoo == 0:
            self.logger.info('_get_wowma_buyers_detail cant match tmpyct_qoo. 0 dsita')
        # 2021/1/19 仮に、tmpyct にはwowmaのカテゴリコードを割り当てておく
        #tmpyct = "500501"
        #tmpyct_qoo = "500501"

        # ==========================
        # 配送IDの設定をする
        # 本来は、カテゴリコード設定の際に判定しなければいけないが仮に固定で以下。送料無料
        #tmpdeliveryid = 100003
        #tmp_qoo_deliveryid = 100003


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
        self.logger.info('start set keyword.my_ct[{}] gname[{}]'.format(my_ct, tmpgname))
        tmp_qoo_keyword = self.buinfo_obj.set_qoo_keyword(my_ct, tmpgname, tmpyct_qoo)
        tmp_wow_keyword = self.buinfo_obj.set_wow_keyword(my_ct, tmpgname, tmpyct)

        # wowma は検索タグIDを設定。
        tmp_wow_tagid = self.buinfo_obj.get_wow_tagid_list(my_ct, tmpgname, tmpyct)
        self.logger.info('ok set qoo_keyword[{}] wow_key[{}] tagid[{}]'.format(tmp_qoo_keyword, tmp_wow_keyword,tmp_wow_tagid))

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
                bu_ctid=my_ct,
                gsrc=gsrc,
                gname=tmpgname,
                gdetail=tmpgdetail,
                gnormalprice=tmpgspprice,
                stock=int(tmpgretail),
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
                qoo_ctid=tmpyct_qoo,  # qooのカテゴリID
                qoo_delivery_method_id=tmp_qoo_deliveryid, # qooの配送方法ID
                qoo_item_qty=int(tmp_qoo_item_qty),  #商品数量
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
            self.logger.info('YaBuyersItemDetail gidが存在してるのでスルーします gid:[{}]'.format(tmpgid))
            #self.logger.info('start save YaBuyersItemDetail start update.')
            """
            new_obj.gcode = gcd
            new_obj.glink = d_url
            new_obj.ss_url = ss_url
            new_obj.gsrc = gsrc
            new_obj.gname = tmpgname
            new_obj.gdetail = tmpgdetail
            new_obj.gnormalprice = int(tmpgspprice)
            new_obj.stock = int(tmpgretail)
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
            new_obj.qoo_gname = tmp_qoo_gname
            new_obj.qoo_gdetail = tmp_qoo_gdetail
            new_obj.qoo_keyword = tmp_qoo_keyword
            new_obj.qoo_contact_info = tmp_qoo_contact_info
            new_obj.qoo_worn_key = tmp_qoo_worn_key
            new_obj.qoo_price = tmp_qoo_price
            new_obj.qoo_fixed_price = 0
            new_obj.qoo_shipping_no = tmp_qoo_shipping_no  # qooの# qoo送料コード 0:送料無料
            new_obj.qoo_postage = tmp_qoo_postage  # qooの個別送料
            new_obj.qoo_ctid = int(tmpyct_qoo)  # qooのカテゴリID
            new_obj.qoo_delivery_method_id = tmp_qoo_deliveryid  # qooの配送方法ID
            new_obj.qoo_item_qty = int(tmp_qoo_item_qty)  # 商品数量
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
        self.logger.debug('_get_wowma_buyers_detail popup_text[' + element.text + ']')
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
        self.logger.debug('_get_wowma_buyers_detail popup_text[' + element.text + ']')
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
                    if self._get_wowma_buyers_detail(tmpglink) = False:
                        # 途中でコケたら止めておこう
                        return False
        """

        self.logger.debug('_get_wowma_buyers_detail out.')
        return True

    # バイヤーズにログインしておく
    def login_buyers(self):
        try:
            self.logger.info('login_buyers start.')

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

    # wowmaにログインしておく
    def wowma_login(self):
        try:
            self.logger.info('login_wowma start.')

            # バイヤーズのtopページ
            start_url = 'https://buyerz.shop/'
            self._get_page_no_tor(start_url)

            # ログインボタンを押す
            sleep(1)
            self.common_chrome_driver.driver.execute_script("ssl_login('login')")
            sleep(3)

            # ログインページにログイン情報入力
            user_email = 'doublenuts8@gmail.com'
            user_pw = 'maropi888'
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

            self.logger.info('login_wowma end.')

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("Wowmaのログインに失敗しました。")

        return True


    # csv の格納ディレクトリから１ファイルずつ読み込む
    def read_csv_dir(self):
        self.logger.debug('read_csv start.')
        print('read_csv start.')
        try:
            # 指定のディレクトリ配下を読み込む
            # csv 読み込み
            file_list = glob.glob(UPLOAD_DIR + "*")
            for my_file in file_list:
                #print("file:" + my_file)
                self.logger.info('---> start read_csv')
                rtn = self.read_csv(my_file)

                # CSV取り込みできたらwrite
                self.logger.info('---> start write_csv')
                rtn = self.write_csv()

                # CSVは処理済みに移動
                self.logger.info('---> start move_csv')
                self.move_csv(my_file)

        except Exception as e:
            #lgr.info('call_enditem exception={}'.format(e))
            #print(e)
            #print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            #if f:
            #   f.close()
            return False  # 途中NGなら 0 return で処理済みにしない

        return True

    # 指定されたファイルを処理済みディレクトリに移動する
    def move_csv(self, csvname):
        new_path = shutil.move(
            csvname,
            DONE_CSV_DIR + "{0:%Y%m%d_%H%M%S}".format(datetime.datetime.now()) + "_" + os.path.split(csvname)[1])
        return

    # 指定されたcsv単位で処理する。
    # csv を読み込み処理
    def read_csv(self, csvname):

        try:
            #f = codecs.open(csvname, 'r', 'utf-8')
            #f = codecs.open(csvname, 'r', 'shift-jis')
            f = codecs.open(csvname, 'r', 'cp932')
            reader = csv.reader(f, delimiter=',')

            cnt = 0
            for row in reader:
                #print('read_row:')
                #self.logger.info('---> read_csv in')

                self.logger.debug('read_row start. 行の列項目をチェック ')
                #print(', '.join(row))
                cnt += 1
                self.logger.debug('read_row cnt. {}'.format(cnt))
                self.logger.info('read_row cnt. {}'.format(cnt))
                if cnt == 1:
                    self.logger.debug('---> read_csv in cnt =1')
                    self.upd_csv.append(row)
                elif cnt > 1:
                    self.logger.debug('---> read_csv cnt[{}]'.format(cnt))

                    # ここからCSVの行ごとに内容をチェック
                    self.logger.debug('行の列項目をチェック ')
                    self.logger.debug('列の長さ：{}'.format(len(row)))

                    # 6列以下だったらさすがに処理できない
                    if len(row) < 7:
                        raise Exception("CSVのフォーマットが不正です。列項目が足りません。")

                    # 以下でやりたいこと。row[5] のイメージURLからカテゴリIDを抜いてくる
					# row[2]とrow[4]のタイトル、説明文から固定のキーワードを除外する　hbab　とか
					# もしhbabとか、送料がかかる条件だとかがあれば機械的に除外したい。
					# 結果はDBに入れ、かつCSVにwriteするのでいったんメモリに取り込む。
					# 詳細ページを取ってくるロジック。そのまま使いたい
                    if self._get_wowma_buyers_detail_for_ecauto(row) is False:
                        self.logger.debug('---> read_csv get_wowma false?? ')
                        self.logger.info('---> read_csv get_wowma false?? ')

                        if f:
                            f.close()
                        return

                    self.logger.debug('---> read_csv get_wowma ok, continue')

                    """
                    if self.eb_request_enditem(row[1]) is True:
                        if self.eb_upd_delete_item_to_db(row[1]) is False:
                            # DB更新失敗 途中で止める
                            f.close()
                            return False
                    else:
                        # 削除失敗 途中で止める
                        f.close()
                        return False
                    """
                else:
                    self.logger.debug('---> read_csv get_wowma ok continue ??')
                    continue

            f.close()

        except Exception as e:
            #lgr.info('call_enditem exception={}'.format(e))
            #print(e)
            #print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            if f:
                f.close()
            return False  # 途中NGなら 0 return で処理済みにしない

        return

# csvにファイル出力
    def write_csv(self):
        self.logger.debug('write_csv in .')
        # csvはここで用意するか
        csvname = myupdcsv_dir + 'updcsv_' + "{0:%Y%m%d_%H%M%S}".format(datetime.datetime.now()) + '.csv'

        # 以下はヘッダ行のみ
        #with open(csvname, 'w', encoding='shift_jis') as csvfile:
        with open(csvname, 'w', encoding='cp932') as csvfile:
            writer = csv.writer(csvfile, lineterminator='\n')
            """
            writer.writerow([
                '保存ファイル名',
                '★カテゴリID',
                '★タイトル',
                '説明の入力方式(0:直接入力/1:ファイル)',
                '★商品説明またはファイル',
                '画像1ファイル',
                '画像2ファイル',
                '画像3ファイル',
                '画像4ファイル',
                '画像5ファイル',
                '画像6ファイル',
                '画像7ファイル',
                '画像8ファイル',
                '画像9ファイル',
                '画像10ファイル',
                '画像1コメント',
                '画像2コメント',
                '画像3コメント',
                '画像4コメント',
                '画像5コメント',
                '画像6コメント',
                '画像7コメント',
                '画像8コメント',
                '画像9コメント',
                '画像10コメント',
                '個数',
                '★開始価格',
                '即決価格',
                '値下げ交渉',
                '★開催期間',
                '★終了時刻',
                '自動再出品',
                '自動値下げ率(0)',
                '自動延長',
                '早期終了',
                '入札者制限',
                '悪い評価',
                '本人確認',
                '★商品状態(0:中古/1:新品/2:その他)',
                '状態の備考',
                '返品可否(0:不可/1:可)',
                '返品の備考',
                'Yahoo!かんたん決済',
                'みずほ銀行(3611464/0001)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '(未設定)',
                '出品者情報開示前チェック',
                '★出品地域(1:北海道～47:沖縄/48:海外)',
                '市区町村',
                '送料負担(0:落札者/1:出品者)',
                '送料入力方式(0:落札後/1:出品時/2:着払い)',
                '発送までの日数(1:1～2日/2:3～7日/3:8日以降)',
                'ヤフネコ!(宅急便)',
                'ヤフネコ!(宅急便コンパクト)',
                'ヤフネコ!(ネコポス)',
                'ゆうパック(おてがる版)',
                'ゆうパケット(おてがる版)',
                '(未使用)',
                'はこBOON mini',
                '荷物のサイズ(1～7)',
                '荷物の重さ(1～7)',
                '配送方法1',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法2',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法3',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法4',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法5',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法6',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法7',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法8',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法9',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '配送方法10',
                '全国一律',
                '北海道',
                '沖縄',
                '離島',
                '着払い[ゆうパック]',
                '着払い[ゆうメール]',
                '着払い[宅急便(ヤマト運輸)]',
                '着払い[飛脚宅配便(佐川急便)]',
                '着払い[カンガルー便(西濃運輸)]',
                '海外対応',
                '注目オプション(有料)',
                '太字(有料)',
                '背景色(有料)',
                'アフィリエイト(有料)',
                '仕入れ先',
                '仕入れ先ID',
                'プライムのみ監視',
                '在庫監視',
                '利益監視',
                '枠デザイン',
                '発送日数(1:１~２日/7:２～３日/2:３～７日/5:７日～１３日/6:１４日以降)',
                '想定開始価格',
                '想定即決価格',
                '仕入れ金額',
            ])
            """
        # データ行は追記
        #with open(csvname, 'a') as csvfile:
        #    writer = csv.writer(csvfile, lineterminator='\n')
            for item in self.upd_csv:
                writer.writerow(item)
                """
                writer.writerow([
                    item['brandcd'],
                    item['gname'],
                    item['gdetail'],
                    item['gspprice'],
                    item['gretail'],
                    item['gcode'],
                    item['tmpct'],
                    item['tmpyct_flg'],
                ])
                """

        # upd_csvは空にしておく
        self.upd_csv = None
        return

    # カテゴリコードをチェックしてマッチしたらTrueを返す
    def chk_ct(self, ctcode):
        _MY_CT_CODES = {
            "ct8": {"ctname": "ポイント", "y_ct": "12345"},
            "ct8": {"ctname": "ポイント", "y_ct": "12345"},
            "ct19": {"ctname": "ファッション", "y_ct": "12345"},
            "ct783": {"ctname": "ファッション雑貨", "y_ct": "12345"},
            "ct11": {"ctname": "インテリア/生活雑貨", "y_ct": "12345"},
            "ct9": {"ctname": "小型家電", "y_ct": "12345"},
            "ct32": {"ctname": "スマホアクセサリ", "y_ct": "12345"},
            "ct10": {"ctname": "文房具/オフィス用品", "y_ct": "12345"},
            "ct17": {"ctname": "ヘルス/ビューティー", "y_ct": "12345"},
            "ct13": {"ctname": "スポーツ/アウトドア", "y_ct": "12345"},
            "ct12": {"ctname": "車/バイク", "y_ct": "12345"},
            "ct1114": {"ctname": "ベビー/マタニティー用品", "y_ct": "12345"},
            "ct15": {"ctname": "ペット用品", "y_ct": "12345"},
            "ct170": {"ctname": "おもちゃ・ホビー", "y_ct": "12345"},
            "ct18": {"ctname": "DIY・工具", "y_ct": "12345"},
            "ct1305": {"ctname": "在庫限り", "y_ct": "12345"},
            # ファッション
            "ct109": {"ctname": "メンズ", "y_ct": "12345"},
            "ct119": {"ctname": "レディース", "y_ct": "12345"},
            "ct1039": {"ctname": "ユニセックス", "y_ct": "12345"},
            "ct165": {"ctname": "キッズ", "y_ct": "12345"},
            "ct784": {"ctname": "ベビーファッション", "y_ct": "12345"},
            "ct792": {"ctname": "マタニティー", "y_ct": "12345"},
            "ct795": {"ctname": "コスプレ", "y_ct": "12345"},
            # ファッション雑貨
            "ct801": {"ctname": "帽子", "y_ct": "12345"},
            "ct1050": {"ctname": "ウィッグ", "y_ct": "12345"},
            "ct1017": {"ctname": "ヘアアクセサリー", "y_ct": "12345"},
            "ct1011": {"ctname": "メガネ", "y_ct": "12345"},
            "ct1055": {"ctname": "アクセサリー", "y_ct": "12345"},
            "ct794": {"ctname": "マフラー/ストール", "y_ct": "12345"},
            "ct810": {"ctname": "バッグ", "y_ct": "12345"},
            "ct802": {"ctname": "腕時計", "y_ct": "12345"},
            "ct808": {"ctname": "財布", "y_ct": "12345"},
            "ct811": {"ctname": "シューズ", "y_ct": "12345"},
            "ct793": {"ctname": "スカーフ", "y_ct": "12345"},
            "ct1027": {"ctname": "手袋", "y_ct": "12345"},
            "ct1100": {"ctname": "タトゥーシール", "y_ct": "12345"},
            "ct1033": {"ctname": "ベルト", "y_ct": "12345"},
            "ct809": {"ctname": "キーケース", "y_ct": "12345"},
            "ct1023": {"ctname": "名刺入れ", "y_ct": "12345"},
            "ct813": {"ctname": "ネクタイピン", "y_ct": "12345"},
            "ct818": {"ctname": "その他", "y_ct": "12345"},
            # インテリア/生活雑貨
            "ct60": {"ctname": "インテリア", "y_ct": "12345"},
            "ct62": {"ctname": "生活雑貨", "y_ct": "12345"},
            "ct63": {"ctname": "その他", "y_ct": "12345"},
            # 小型家電
            "ct54": {"ctname": "PC アクセサリ", "y_ct": "12345"},
            "ct55": {"ctname": "オーディオ", "y_ct": "12345"},
            "ct56": {"ctname": "その他", "y_ct": "12345"},
            "ct922": {"ctname": "加湿機", "y_ct": "12345"},
            "ct923": {"ctname": "扇風機", "y_ct": "12345"},
            "ct981": {"ctname": "イヤホン", "y_ct": "12345"},
            # スマホアクセサリ
            "ct513": {"ctname": "iPhoneX / XS ケース ", "y_ct": "12345"},
            "ct924": {"ctname": "iPhoneXRケース ", "y_ct": "12345"},
            "ct925": {"ctname": "iPhoneXs Max ケース ", "y_ct": "12345"},
            "ct68": {"ctname": "iPhone7plus/8plus ケース ", "y_ct": "12345"},
            "ct65": {"ctname": "iPhone7/8 ケース ", "y_ct": "12345"},
            "ct75": {"ctname": "iPhone6plus/6splus ケース ", "y_ct": "12345"},
            "ct72": {"ctname": "iPhone6 / 6s  ケース ", "y_ct": "12345"},
            "ct69": {"ctname": "iPhone5/5s/SE ケース ", "y_ct": "12345"},
            "ct76": {"ctname": "Androidスマホ ケース", "y_ct": "12345"},
            "ct516": {"ctname": "Galaxy スマホケース", "y_ct": "12345"},
            "ct78": {"ctname": "スマホアクセサリー", "y_ct": "12345"},
            # 文房具
            "ct57": {"ctname": "文房具", "y_ct": "12345"},
            "ct58": {"ctname": "オフィス用", "y_ct": "12345"},
            "ct59": {"ctname": "その他", "y_ct": "12345"},
            # ヘルス/ビューティー
            "ct982": {"ctname": "健康グッズ", "y_ct": "12345"},
            "ct95": {"ctname": "ダイエットグッズ", "y_ct": "12345"},
            "ct1103": {"ctname": "ネイルグッズ", "y_ct": "12345"},
            "ct98": {"ctname": "メイクグッズ", "y_ct": "12345"},
            "ct101": {"ctname": "その他", "y_ct": "12345"},
            # スポーツ/アウトドア
            "ct1046": {"ctname": "スポーツ用品", "y_ct": "12345"},
            "ct71": {"ctname": "自転車アクセサリ", "y_ct": "12345"},
            "ct73": {"ctname": "グローブ・サポーター", "y_ct": "12345"},
            "ct983": {"ctname": "レイングッズ", "y_ct": "12345"},
            "ct984": {"ctname": "マスク", "y_ct": "12345"},
            "ct987": {"ctname": "アウトドアグッズ", "y_ct": "12345"},
            "ct999": {"ctname": "ビーチグッズ", "y_ct": "12345"},
            "ct74": {"ctname": "その他", "y_ct": "12345"},
            # 車/バイク
            "ct64": {"ctname": "エンブレム", "y_ct": "12345"},
            "ct66": {"ctname": "カバー", "y_ct": "12345"},
            "ct991": {"ctname": "車/バイク用ステッカー", "y_ct": "12345"},
            "ct992": {"ctname": "車/バイクアクセサリー", "y_ct": "12345"},
            "ct67": {"ctname": "その他", "y_ct": "12345"},
            # ベビー/マタニティー用品
            "ct1115": {"ctname": "ベビー", "y_ct": "12345"},
            "ct1116": {"ctname": "マタニティー", "y_ct": "12345"},
            # ペット用品
            "ct83": {"ctname": "服", "y_ct": "12345"},
            "ct87": {"ctname": "ケアグッズ", "y_ct": "12345"},
            "ct990": {"ctname": "アクセサリー", "y_ct": "12345"},
            "ct91": {"ctname": "その他", "y_ct": "12345"},
            # おもちゃ・ホビー
            "ct996": {"ctname": "教育系", "y_ct": "12345"},
            "ct172": {"ctname": "パズル系", "y_ct": "12345"},
            "ct993": {"ctname": "パーティーグッズ", "y_ct": "12345"},
            "ct994": {"ctname": "キーホルダー", "y_ct": "12345"},
            "ct995": {"ctname": "ハンドスピナー", "y_ct": "12345"},
            "ct171": {"ctname": "その他", "y_ct": "12345"},
        }

        try:
            result_y_ct = str(_MY_CT_CODES[ctcode]["y_ct"])
            if result_y_ct is not None and len(str(result_y_ct)) > 0:
                return result_y_ct
            else:
                return False

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

        # =====================================================================
        # get_wowma_buyers_list は新規で商品登録を行う。
        # 在庫チェックは別コマンドにしよう。
        # --- 処理内容 ---
        # 予め指定されたバイヤーズのリストページへのパスを順次読み込む　→　buyers_listにしよう。
        # →リストからページ中の商品コードをチェック。DBに登録がなければ新規登録、あれば飛ばす
        # 登録の場合は詳細ページへアクセス。必要な情報はDB格納
        # ペーネを繰り返して指定されたリストページ（カテゴリ）以下の商品は全部読み込み。
        # 登録時は、まだwowmaには未出品にしておこう。wowma以外、他サイトへの展開用に、出品フラグは個別でもつ。
        # 指定されたものはすべて仮登録にする。

        # ===> ここまでが当コマンド内での処理。以下は別バッチ、画面でのチェックとする。

        # ★★以下は画面を作ろう。画面でいったん確認してから登録OKのフラグを立てて更新できるようにする。
        # 仮登録のものは、画面などで確認して、商品説明がOKかどうかも見ておく。おかしければそこで修正してから出品
        # ここでOKであれば、登録OKのフラグを立てる

        # ★★以下は在庫チェックバッチのなかでやる。
        # wowmaへの本登録は、在庫バッチを回して在庫があったとき。
        # 在庫があり、出品済みフラグを見て、まだ未出品のものは出品のフローを。出品済みであれば在庫数や価格のチェックと更新を行う
        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('get_wowma_buyers_list handle is called')

            self.batch_status = BatchStatusUpd('get_wowma_buyers_list')
            self.batch_status.start()

            self.common_chrome_driver = CommonChromeDriver(self.logger)

            # self.common_chrome_driver.driverにセット
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            # self.init_chrome_with_tor()

            # 保存してみる
            # if not os.path.exists(mydwsrc_dir):
            #    os.mkdir(mydwsrc_dir)
            self.logger.debug('get_wowma_buyers_list handle start get')


            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            self.buinfo_obj = BuyersInfo(self.logger)
            self.bubrandinfo_obj = BuyersBrandInfo(self.logger)
            #my_ct_list = self.buinfo_obj.get_ct()
            #self.logger.info('start exec get_buers_info.list:[{}]'.format(my_ct_list))

            # バイヤーズにログインしておく
            self.buinfo_obj.login_buyers()

            # アップロードされたCSVを読み込む
            #self.read_csv_dir()

            # 商品リストを取得対象のURL（カテゴリコード）を取得する。
            self.my_wowma_target_ct_list = self.buinfo_obj.get_url_list_for_wowma()

            # これはカテゴリのリストなので、取得するURLにするには固定でバイヤーズのパスを追加する
            self._exec_get_buyers_list()



            #self.buinfo_obj = BuyersInfo(self.logger)
            #my_ct_list = self.buinfo_obj.get_ct()
            #self.logger.info('start exec get_buers_info.list:[{}]'.format(my_ct_list))

            self.logger.info('get_wowma_buyers_list handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            self.common_chrome_driver.quit_chrome_with_tor()
            return
        #self.common_chrome_driver.quit_chrome_with_tor()

        self.batch_status.end()
        self.logger.info('get_wowma_buyers_list handle end')
        return
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))


"""
f = open('./src_20181108.txt', mode='w')
#f.write(driver.findElement(By.tagName("body")).getText())
element = driver.find_element_by_id("imgTagWrapperId")
subele = element.find_element_by_tag_name("img")
src_1 = subele.get_attribute("src")
src_2 = subele.get_attribute("data-a-dynamic-image")
#element = driver.find_element_by_id("noFlashContent")
#f.write(driver.find_element_by_id("imgTagWrapperId").text)
f.write(driver.page_source)
f.close()

f = open('./src_1.txt', mode='w')
f.write(src_1)
f.close()

f = open('./src_2.txt', mode='w')
f.write(src_2)
f.close()

ele2 = driver.find_element_by_class_name("a-carousel-row-inner")
print(ele2.get_attribute("outerHTML"))
print(ele2.get_attribute("innerHTML"))

ele3 = driver.find_element_by_id("productDescription")
subele3 = ele3.find_element_by_tag_name("p")

print(subele3.text)
f = open('./src_3.txt', mode='w')
f.write(subele3.text)
f.close()

print(element.tag_name)
print(subele.tag_name)
#print(element)
#print(element.text)
#print(subele.text)
"""
