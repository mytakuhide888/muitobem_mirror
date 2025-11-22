# -*- coding:utf-8 -*-
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
import yaget.integrations.error_goods_log

# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')
sys.path.append('/app/yaget/management/commands')

from yaget.integrations.buyers_info import BuyersInfo, BuyersBrandInfo
from yaget.integrations.wowma_access import WowmaAccess
from qoo10_access import Qoo10Access
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.models import YaBuyersItemList, YaBuyersItemDetail
from yaget.integrations.batch_status import BatchStatusUpd


#from yaget.AmaMws import AmaMwsProducts

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/stock_chk_logging.config", disable_existing_loggers=False)

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
        self.logger.debug('wowma_stock_chk Command in. init')
        self.common_chrome_driver = None
        self.driver = None
        self.upd_csv = []
        self.my_wowma_target_ct_list = []
        self.start_time = datetime.datetime.now()
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
    # 登録されている商品情報に対して価格・在庫の更新をする
    def _chk_buyers_stock_from_list(self):

        self.logger.debug('_chk_buyers_stock_from_list in.')
        # self.my_wowma_target_ct_list にあるカテゴリの分だけ順に処理するか
        #             result_y_ct = str(_MY_CT_CODES[ctcode]["y_ct"])
        for my_ct, my_value in self.my_wowma_target_ct_list.items():
         #   for ss_url in options['s_url']:
            # 入り口がss_url、ペーネが存在する間は順に取得する
            # 形式は　https://buyerz.shop/shopbrand/ct113/
            ss_url = "https://buyerz.shop/shopbrand/" + str(my_ct) + "/"
            pcount = 1
            while True:
                next_page = self._chk_buyers_stock_page(ss_url, str(my_ct), pcount)

                # いったん１ページ目で終わり
                #next_page = False
                if not bool(next_page):
                    break
                # next_page が次ページのurlであることを期待している
                ss_url = next_page
                pcount += 1

            # 全部取得が完了したらcsvをファイル出力
            #self.write_csv()

        self.logger.debug('_chk_buyers_stock_from_list out.')
        return

    # 2021/10/21 名前は変えよう！
    # https://qiita.com/tomson784/items/88a3fd2398a41932762a 参照
    # ※これは商品リストページが対象。
    # 指定されたURLに対してバイヤーズの商品群を取得する
    # 渡される ss_url は　https://buyerz.shop/shopbrand/ct113/　の形式
    # ペーネすると、　https://buyerz.shop/shopbrand/ct113/page2/order/
    def _chk_buyers_stock_page(self, ss_url, my_ct, pcount):
        # self.stdout.write('ss_url:' + ss_url)
        # self.stdout.write(self.style.SUCCESS('my_s_url:' + s_url))
        self.logger.debug('_chk_buyers_stock_page in pcount:[{}]my_ct[{}]ssurl[{}]'.format(
            pcount, ss_url, my_ct))

        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                # ss_url = 'https://buyerz.shop/shop/shopbrand.html?page=1&search=&sort=&money1=&money2=&prize1=&company1=&content1=&originalcode1=&category=&subcategory='
                self.common_chrome_driver.driver.get(ss_url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.debug(traceback.format_exc())
                self.logger.debug('webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                # self.restart_chrome()
                sleep(3)
            else:
                break

        # ソースを戻りから読み込み
        dom = lxml.html.fromstring(self.common_chrome_driver.driver.page_source)
        self.common_chrome_driver.driver.close()  # closeはフォーカスがあたってるブラウザを閉じるらしい

        # a_list = dom.xpath("//div[@class='th']/table/tbody/tr/td")  # <div id="web">の子要素の<li>の子要素の<a>をすべて抽出
        # shop urlをとってみる
        # //*[@id="TopSPathList1"]/ol/li[1]/a

        # 以下が個別の商品群
        # tmpdivs = dom.xpath("//div[@class='th']/table/tbody/tr/td/a")
        # tmpdivs = dom.xpath("//div[@id='r_searchList']/ul/li/div")
        tmpdivs = dom.xpath("//div[@class='innerBox']")

        self.logger.debug('start break item list.')
        self.logger.debug('tmpdivs:' + str(len(tmpdivs)))

        mydomain = 'https://buyerz.shop'

        for i, j in enumerate(tmpdivs):
            self.logger.debug('i:[' + str(i) + '] detail[' + str(len(j.find_class('detail'))) + ']')
            # tmp_td_obj = list(j)
            # print(i)
            # self.logger.debug('list. i[' + str(i) + ']')
            # tmpglink = mydomain + str(j.find_class('imgWrap')[0].find('a').attrib['href'])
            # tmpgsrc = j.find_class('imgWrap')[0].find('a/img').attrib['src']
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
            tmpgid_1 = j.find_class('detail')[0].text  # gコード
            tmpgid_2 = j.find_class('detail')[0].find_class('else')[0].text  # gコード
            tmpgid_3 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].text  # gコード
            self.logger.debug('tmpgid_3:[' + str(tmpgid_3) + ']')
            tmpgid_4 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].find('li').text  # gコード
            self.logger.debug('tmpgid_4:[' + str(tmpgid_4) + ']')
            tmpgid_5 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].findall('li')[
                0].text  # gコード
            self.logger.debug('tmpgid_5:[' + str(tmpgid_5) + ']')
            tmpgid_6 = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].findall('li')[
                1].text  # gコード
            self.logger.debug('tmpgid_6:[' + str(tmpgid_6) + ']')
            """

            # tmpgcd: 商品コード zbza153 など
            tmpgcd = j.find_class('detail')[0].find_class('else')[0].find_class('clear')[0].findall('li')[
                1].text  # gコード
            tmpgname = j.find_class('detail')[0].find_class('name')[0].find('a').text  # 商品名
            # tmpgother = re.sub("\\D", "", str(tmpglink).rsplit("/", 1)[1])  # gコード

            # tmpbrandcd = re.sub("\\D", "", tmpurl_path)
            # tmpbrandcd = re.sub("\\d", "", str(tmpurl_path).rsplit("/", 1)[1])
            tmpbrandcd = str(tmpurl_path).split("/")[2]
            # ブランドコードは111始まりとする これがyahoo上の商品コードになる
            # tmpgid: 商品id 000000025633 など
            #         管理のために、B111 を接頭にして 111000000025633 とする
            tmpgid = str("B111") + str(tmpbrandcd)

            self.logger.debug('tmpurl_path:[' + str(tmpurl_path) + ']')
            self.logger.debug('glink:[' + str(tmpglink) + ']')
            self.logger.debug('gsrc:[' + str(tmpgsrc) + ']')
            self.logger.debug('gid:[' + str(tmpgid) + ']')
            self.logger.debug('gcd:[' + str(tmpgcd) + ']')
            self.logger.debug('gname:[' + str(tmpgname) + ']')
            self.logger.debug('tmpbrandcd:[' + str(tmpbrandcd) + ']')

            # ===============================
            # 通常価格
            tmpgspprice = int(re.sub("\\D", "",
                                     j.find_class('detail')[0].find_class('price')[0].find('em').text))
            self.logger.debug('tmpgspprice:[' + str(tmpgspprice) + ']')

            # 販売価格の算出はちょくちょくやるので共通化していい
            # wowmaの価格を算出
            # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
            # 利益額を、価格帯で変えてみる。
            # ※ ここは将来的にサイトごとで設定できてもいいが、ひとまず今は一つだけ
            if tmpgspprice > 0:
                tmp_wow_price = self.buinfo_obj.get_benefit_price(tmpgspprice, 1.15)
                tmp_qoo_price = self.buinfo_obj.get_benefit_price(tmpgspprice, 1.3)
            else:
                tmp_wow_price = 0
                tmp_qoo_price = 0

            self.logger.debug('tmp_wow_price:[' + str(tmp_wow_price) + ']')

            # ===============================
            # 在庫数の抽出
            try:
                tmp_stock = j.find_class('detail')[0].find_class('quantity')[0].find('span').text
                if tmp_stock:
                    # 在庫は取れた。後は文字列で判定
                    tmpgretail_str = re.sub("\\D", "", tmp_stock)
                    if tmpgretail_str != '':
                        tmpgretail = tmpgretail_str
                    else:
                        tmpgretail = "0"
                else:
                    # 在庫が取れないときは在庫切れか
                    self.logger.debug('_chk_buyers_stock_page cant get [M_item-stock-smallstock].2')
                    tmpgretail = "0"
            except:
                # 在庫が取れないときは在庫切れか
                self.logger.debug('_chk_buyers_stock_page cant get [M_item-stock-smallstock].3')
                tmpgretail = "0"

            self.logger.debug('tmpgretail:[' + str(tmpgretail) + ']')

            # wowmaの在庫は、在庫切れなら 2(0だと未出品かな)、1以上なら在庫ありにする（1でいいかな）
            # WOW_STATUS = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))

            # ===============================
            # 商品詳細のDB更新をここで
            # いちおうfixed_priceとの比較くらいはしよう
            # なければ、価格・在庫更新かけて。
            # wowma側の更新は後でよい。ここではDB更新だけ

            # ブラックリストの商品に該当してたら処理はしない
            black_list_obj = YaBuyersItemDetail.objects.filter(gid=tmpgid).filter(black_list__isnull=False).first()
            if black_list_obj:
                self.logger.debug('_chk_buyers_stock_page ブラックリストに該当したので処理しない gid:[{}]'.format(tmpgid))
                continue

            new_obj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
            if not new_obj:
                # ここでもし登録のないものだったら、商品詳細までチェックして新規登録してしまうか。
                # detailはここで取得してみる
                # if self._get_ya_buyers_detail(tmpglink) == False:

                # 在庫が1以上だったら更新します
                if tmpgretail != "0":
                    if not self.buinfo_obj.get_wowma_buyers_detail(tmpglink, tmpgid, tmpgcd, ss_url, tmpgsrc, my_ct):
                        # 途中でコケたら止めておこう
                        self.logger.info('_chk_buyers_stock_page failed ?!')
                        # いや、おかしな商品は飛ばして他は処理したい。passにする
                        pass
                else:
                    # 在庫0 だった。何もしない
                    pass

                # 以下はそのまま使っちゃだめ！
                """
                gid=tmpgid,
                gcode=gcd,
                glink=d_url,
                ss_url=ss_url,
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
                wow_ctid=tmpyct, # wowmaのカテゴリID
                wow_delivery_method_id=tmpdeliveryid, # wowmaの配送方法ID
                wow_on_flg=tmp_wow_on_flg,
                wow_upd_status=tmp_wow_upd_status,
                qoo_gname=tmp_qoo_gname,
                qoo_gdetail=tmp_qoo_gdetail,
                qoo_keyword=tmp_qoo_keyword,
                qoo_contact_info=tmp_qoo_contact_info,
                qoo_worn_key=tmp_qoo_worn_key,
                qoo_price=tmp_qoo_price,
                qoo_fixed_price=0,
                qoo_shipping_no=tmp_qoo_shipping_no,  # qooの# qoo送料コード 0:送料無料
                qoo_postage=tmp_qoo_postage,  # qooの個別送料
                qoo_ctid=int(tmpyct_qoo), # qooのカテゴリID
                qoo_delivery_method_id=tmp_qoo_deliveryid, # qooの配送方法ID
                qoo_item_qty=int(tmp_qoo_item_qty), #商品数量
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
                """
                """
                obj, created = YaBuyersItemDetail.objects.update_or_create(
                    gid=tmpgid,
                    gcd=tmpgcd,
                    my_ct=my_ct,
                    listurl=ss_url,
                    glink=tmpglink,
                    gname=tmpgname,
                    g_img_src=tmpgsrc,
                )
                obj.save()
                """
            else:
                # 更新対象のレコードが見つかった。
                # しかし負荷軽減のため、在庫数、通常価格がDBの値と変わっていなかったら
                # レコード更新はかけない。
                if tmpgspprice != new_obj.gnormalprice or int(tmpgretail) != new_obj.stock:
                    self.logger.debug('_chk_buyers_stock_page 価格か在庫数が更新されていたのでDB更新する')
                    # 更新できる項目を上書き
                    new_obj.stock = int(tmpgretail)
                    #new_obj.wow_on_flg = tmp_wow_on_flg
                    #new_obj.qoo_on_flg = tmp_qoo_on_flg
                    new_obj.wow_price = tmp_wow_price
                    new_obj.qoo_price = tmp_qoo_price
                    new_obj.save()
                else:
                    self.logger.debug('_chk_buyers_stock_page 価格か在庫数が更新されてないのでDB更新しない')

        # とりあえず1ページだけ
        # return False
        # ペーねが存在したら取得、終わっていたらfalse　を返却
        tmp_nextpage_obj = dom.xpath("//li[@class='next']/a")
        if tmp_nextpage_obj is not None:
            if len(tmp_nextpage_obj) > 0:
                tmp_nextpage_href = tmp_nextpage_obj[0].attrib['href']
                if tmp_nextpage_href is not None:
                    time.sleep(1)
                    return tmp_nextpage_href
                else:
                    return False
            else:
                return False
        else:
            return False

        self.logger.debug('end of _chk_buyers_stock_page')

        return False

    # 商品カテゴリのリストを対象にした在庫チェックから漏れた商品をチェックしておく
    # 対象は、バッチ開始時刻より前の更新時間が残されているもの。（それ以外は、本バッチで更新済みのはず）
    def _chk_buyers_stock_from_remaining_items(self):

        self.logger.debug('_chk_buyers_stock_from_remaining_items in.')

        # バッチを開始したstart_timeより古い更新時刻のものを対象
        #result = YaBuyersItemDetail.objects.exclude(wow_on_flg=2).filter(wow_upd_status=1)
        result = YaBuyersItemDetail.objects. \
            select_related('black_list').filter(black_list__isnull=True).\
            exclude(wow_on_flg=2).\
            exclude(qoo_on_flg=2).\
            filter(update_date__lt=self.start_time)
        self.logger.debug('_chk_buyers_stock_from_remaining_items target_cnt [' + str(len(result)) + ']')
        for my_value in result:
            # 形式は　https://buyerz.shop/shopbrand/ct113/
            self.logger.debug('_chk_buyers_stock_from_remaining_items url:[' + str(my_value.glink) + ']')
            self.buinfo_obj.chk_wowma_buyers_stock(my_value.glink, my_value.gid, my_value.gcode)

        self.logger.debug('end of _chk_buyers_stock_from_remaining_items')

        return True

    # バイヤーズで登録済みの商品について、在庫チェックを行い
    # 在庫数や価格を改定してゆく
    # こちらは商品詳細をひとつづつなめていく版。
    def _exec_wowma_stock_chk(self):

        self.logger.debug('_exec_wowma_stock_chk in .')
        # self.YaBuyersItemDetail に登録済みの商品から、
        # wow_on_flg　が(2：NG）の設定ではない かつ wow_upd_statusが (1:掲載中) のものを全て対象とする
        #  →　いや、wow_upd_statusが０（未掲載）のものもいったんチェックして、未登録のものでOKになるなら後続で登録までしてしまう
        #result = YaBuyersItemDetail.objects.exclude(wow_on_flg=2).filter(wow_upd_status=1)
        result = YaBuyersItemDetail.objects.\
            select_related('black_list').filter(black_list__isnull=True).\
            exclude(wow_on_flg=2)
        self.logger.debug('_exec_wowma_stock_chk target_cnt [' + str(len(result)) + ']')
        for my_value in result:
            # 形式は　https://buyerz.shop/shopbrand/ct113/
            self.logger.debug('_exec_wowma_stock_chk url:[' + str(my_value.glink) + ']')
            self._chk_wowma_buyers_stock(my_value.glink, my_value.gid, my_value.gcode)
            """
            pcount = 1
            while True:
                next_page = self._get_wowma_buyers_list(ss_url, pcount)

                # いったん１ページ目で終わり
                next_page = False
                if not bool(next_page):
                    break
                # next_page が次ページのurlであることを期待している
                ss_url = next_page
                pcount += 1

            # 全部取得が完了したらcsvをファイル出力
            #self.write_csv()
            """
        self.logger.debug('_exec_wowma_stock_chk out .')

        return

    # https://qiita.com/tomson784/items/88a3fd2398a41932762a 参照
    # 指定された商品詳細のURLに対して在庫チェックする
    # 渡される ss_url は　https://buyerz.shop/shopbrand/ct113/　の形式
    # 登録の手順としては、
    # 1.  バイヤーズから商品情報取得 この時点ではまだ未掲載。フラグを立てる。まだ出品NG　のフラグを
    # 2.  画面から、掲載可否を判断して商品詳細などを編集する。OKなら出品OKのフラグをたてる。NGならブラックリストいり
    # 3.  在庫チェックバッチが巡回する。
    #     ブラックリスト以外の商品をDBから抜いてくる。　_exec_wowma_stock_chk　で絞り込み済み
    # 4.  在庫をバイヤーズにチェックしにいったあと、
    #     未出品から、画面にてOKかどうかを確認したら。OKであれば
    #       → wow_on_flg が 0 → 1 (OK) に
    #     出品OK　かつ　未掲載（wow_upd_status=0）　かつ　在庫あり のものは 新規に商品をwowmaに登録する
    #       → 登録できたら wow_upd_status が 0 → 1 (掲載中)
    #     出品OKかつ、掲載済みのものは　在庫と価格を更新する。
    #       → wow_on_flg が 1 、wow_upd_status が 1 のまま。（在庫があれば）
    #     出品NGのものは、まだ未編集だが在庫数と価格は、DBを更新してもよい。（これはどうするか・・？）
    #       → wow_on_flg が 0 のまま。 かつ未掲載（wow_upd_status=0）　のまま
    #     出品OKかつ、在庫が０になったらそのまま在庫０で更新しておく。（在庫０になったら、掲載はやめてもいいけど）
    #       → wow_on_flg が 1 のまま　wow_upd_statusは 1 のままでいいかな　
    #     ブラックリスト入り
    #       → wow_on_flg が 2 (NG)
    #       商品ページは削除せずにいくか、削除してしまうか？　＞　削除してもいいかな
    def _chk_wowma_buyers_stock(self, ss_url, gid, gcode):
        # self.stdout.write('ss_url:' + ss_url)
        # self.stdout.write(self.style.SUCCESS('my_s_url:' + s_url))
        self.logger.debug('_chk_wowma_buyers_stock in ssurl:[' + str(ss_url) + ']')


        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                #ss_url = 'https://buyerz.shop/shop/shopbrand.html?page=1&search=&sort=&money1=&money2=&prize1=&company1=&content1=&originalcode1=&category=&subcategory='
                self.common_chrome_driver.driver.get(ss_url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.debug(traceback.format_exc())
                self.logger.debug('_chk_wowma_buyers_stock webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                #self.restart_chrome()
                sleep(3)
            else:
                break

        # ファイルに書き込みたかったら以下をONに
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


        f_read = codecs.open(tfpath, 'r', 'utf-8')
        s = f_read.read()
        """

        s = self.common_chrome_driver.driver.page_source
        dom = lxml.html.fromstring(s)

        # 在庫チェックではいまのところ、画像の再取得は行わない。以下はコメントアウト
        """
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
        self.common_chrome_driver.driver.switch_to_window(handles[1])
        self.logger.debug('source ---' + self.common_chrome_driver.driver.page_source + '---')
        """

        tmpimglist = []
        cnt = 0

        """
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

            tmp_g_img_src[tmp_cnt] = str(tmpgsrc)
            tmp_cnt += 1

            # 画像保存してみる
            myresponce = requests.get(tmpgsrc)
            if cnt == 0:
                tmpimgfname = gid
            else:
                tmpimgfname = gid + '_' + str(cnt)
            with open(mydwimg_dir + "{}.jpg".format(tmpimgfname), "wb") as myf:
                myf.write(myresponce.content)

            cnt += 1

        # 親のウィンドウに戻る
        #self.common_chrome_driver.driver.switch_to_window(handles[0])
        self.common_chrome_driver.driver.close()
        self.common_chrome_driver.driver.switch_to_window(handles[0])
        """

        # 商品詳細の各要素を取得する

        #tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        #tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 在庫チェックの際は、商品名と商品詳細は更新する。
        # wowma用に編集したものはそのままにしておく
        # 商品名
        tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='itemInfo']/h2").text

        # 商品詳細
        tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='itemInfo']/div[1]/div").text

        # ===============================
        # 通常価格
        tmpgspprice = int(re.sub("\\D", "",
                             self.common_chrome_driver.driver.find_element_by_xpath(
                                 "//li[@id='M_usualValue']/span").text))

        # wowmaの価格を算出
        # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
        # 利益額を、価格帯で変えてみる。
        wow_benefit = 500
        if tmpgspprice < 500:
            wow_benefit = 300
        elif 500 <= tmpgspprice < 2000:
            wow_benefit = 400
        elif 2000 <= tmpgspprice < 3000:
            wow_benefit = 500
        elif 3000 <= tmpgspprice < 5000:
            wow_benefit = 700
        else:
            wow_benefit = 1000

        # 末尾は80円で整える
        tmp_wow_price = int(round(((int(tmpgspprice) * 1.15) + wow_benefit), -2)) + 80
        self.logger.debug('_chk_wowma_buyers_stock tmp_wow_price[' + str(tmp_wow_price) + ']')

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
        # wowmaの在庫は、在庫切れなら 2、ほかは未出品にする
        """
        if tmpgretail == "0":
            tmp_wow_on_flg = 3
        else:
            tmp_wow_on_flg = 0
        """

        # 2021/1/19 テストのため在庫数を１に
        #tmpgretail = "1"

        tmpgcode = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='detailInfo']/ul/li[4]").text

        #self.logger.debug('gid:[' + str(tmpgid) + ']')
        self.logger.debug('d-gid:[' + str(gid) + ']')
        self.logger.debug('d-gname:[' + str(tmpgname) + ']')
        self.logger.debug('d-gdetail:[' + str(tmpgdetail) + ']')
        self.logger.debug('d-gspprice:[' + str(tmpgspprice) + ']')
        self.logger.debug('d-gretail:[' + str(tmpgretail) + ']')

        myrtn = 0
        mycode = ''

        # DBに保存
        myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        if myobj:
            self.logger.debug('start save YaBuyersItemDetail add.')

            # 画像情報を作らないといけない。
            images = [{'imageUrl': myobj.g_img_src_1, 'imageName': 'image_1', 'imageSeq': 1},
                      {'imageUrl': myobj.g_img_src_2, 'imageName': 'image_2', 'imageSeq': 2},
                      {'imageUrl': myobj.g_img_src_3, 'imageName': 'image_3', 'imageSeq': 3},
                      {'imageUrl': myobj.g_img_src_4, 'imageName': 'image_4', 'imageSeq': 4},
                      {'imageUrl': myobj.g_img_src_5, 'imageName': 'image_5', 'imageSeq': 5},
                      {'imageUrl': myobj.g_img_src_6, 'imageName': 'image_6', 'imageSeq': 6},
                      {'imageUrl': myobj.g_img_src_7, 'imageName': 'image_7', 'imageSeq': 7},
                      {'imageUrl': myobj.g_img_src_8, 'imageName': 'image_8', 'imageSeq': 8},
                      {'imageUrl': myobj.g_img_src_9, 'imageName': 'image_9', 'imageSeq': 9},
                      {'imageUrl': myobj.g_img_src_10, 'imageName': 'image_10', 'imageSeq': 10},
                      {'imageUrl': myobj.g_img_src_11, 'imageName': 'image_11', 'imageSeq': 11},
                      {'imageUrl': myobj.g_img_src_12, 'imageName': 'image_12', 'imageSeq': 12},
                      {'imageUrl': myobj.g_img_src_13, 'imageName': 'image_13', 'imageSeq': 13},
                      {'imageUrl': myobj.g_img_src_14, 'imageName': 'image_14', 'imageSeq': 14},
                      {'imageUrl': myobj.g_img_src_15, 'imageName': 'image_15', 'imageSeq': 15},
                      {'imageUrl': myobj.g_img_src_16, 'imageName': 'image_16', 'imageSeq': 16},
                      {'imageUrl': myobj.g_img_src_17, 'imageName': 'image_17', 'imageSeq': 17},
                      {'imageUrl': myobj.g_img_src_18, 'imageName': 'image_18', 'imageSeq': 18},
                      {'imageUrl': myobj.g_img_src_19, 'imageName': 'image_19', 'imageSeq': 19},
                      {'imageUrl': myobj.g_img_src_20, 'imageName': 'image_20', 'imageSeq': 20}]

            # 既存DBのフラグによってどうステータスを更新するか
            # 出品はまだNG。（画面から編集してない）が、DBの在庫などは更新していい
            if myobj.wow_on_flg == 0:
                self.logger.debug('--> _chk_wowma_buyers_stock 出品まだNG そのまま')
                myobj.wow_on_flg = 0

            # 画面から出品OKになっている。以下で掲載状況を確認して更新してゆく
            elif myobj.wow_on_flg == 1:

                # 出品OKなのに在庫０なら、そのまま未掲載にしておく
                if tmpgretail == "0":
                    if myobj.wow_upd_status == 0:
                        # 未掲載 wow_upd_status = 0
                        # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                        self.logger.debug('--> _chk_wowma_buyers_stock 出品OKなのに在庫０　未掲載のまま')
                        myobj.wow_on_flg = 1
                    else:
                        # 掲載中 wow_upd_status = 1
                        # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない
                        try:
                            ret_obj_list = self.wowma_access.wowma_update_item_info(
                                    myobj.wow_gname,
                                    myobj.gid,
                                    myobj.gcode,
                                    myobj.wow_price,
                                    myobj.wow_fixed_price,
                                    myobj.wow_postage_segment,
                                    myobj.wow_postage,
                                    myobj.wow_delivery_method_id,
                                    myobj.wow_gdetail,
                                    myobj.wow_ctid,
                                    myobj.wow_keyword,
                                    myobj.wow_tagid,
                                    myobj.wow_upd_status,  # 1は販売中。2は販売終了。
                                    int(tmpgretail),  # 在庫数
                                    images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                            )
                            for ret_obj in ret_obj_list:
                                if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                    # lotnumberを更新しておく
                                    self.buinfo_obj.set_wow_lotnum(myobj.gid, ret_obj['res_code'])
                            # 0が返ってきて 出品OKだったら、フラグを出品済みに
                            # 出品失敗なら 1 が返される。この場合は未出品のまま
                            myobj.wow_on_flg = 1  # 更新成功したら 在庫切れにする
                            self.logger.debug('--> _chk_wowma_buyers_stock 在庫切れにした。')
                        except:
                            # 更新時にエラー？
                            my_err_list = {
                                'batch_name': '_chk_wowma_buyers_stock wowma_update_stock point 0_2',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': myobj.gcode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            raise Exception("在庫を0更新時に失敗？{}".format(gid))

                # 　在庫がある
                elif int(tmpgretail) > 0:
                    # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                    if myobj.wow_upd_status == 0:
                        self.logger.debug('--> _chk_wowma_buyers_stock 未登録だが出品OKで在庫あるので登録開始')
                        # 未掲載 wow_upd_status = 0
                        try:
                            ret_obj_list = self.wowma_access.wowma_register_item_info(
                                                               myobj.wow_gname,
                                                               gid,
                                                               gcode,
                                                               tmp_wow_price,
                                                               myobj.wow_fixed_price,
                                                               myobj.wow_postage_segment,
                                                               myobj.wow_postage,
                                                               myobj.wow_delivery_method_id,
                                                               myobj.wow_gdetail,
                                                               myobj.wow_ctid,
                                                               myobj.wow_keyword,
                                                               myobj.wow_tagid,
                                                               1,  # 出品OKなので1は販売中。
                                                               int(tmpgretail),  # 在庫数
                                                               images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                                               )

                            chk_flg = 0
                            for ret_obj in ret_obj_list:
                                # PME0106:入力された商品コードは、既に登録されています。
                                if ret_obj['res_rtn'] == '1' and ret_obj['res_code'] == 'PME0106':
                                    # 出品していいはずなので、更新をかけ直す
                                    try:
                                        ret_obj_list = self.wowma_access.wowma_update_item_info(
                                            myobj.wow_gname,
                                            myobj.gid,
                                            myobj.gcode,
                                            myobj.wow_price,
                                            myobj.wow_fixed_price,
                                            myobj.wow_postage_segment,
                                            myobj.wow_postage,
                                            myobj.wow_delivery_method_id,
                                            myobj.wow_gdetail,
                                            myobj.wow_ctid,
                                            myobj.wow_keyword,
                                            myobj.wow_tagid,
                                            1,  # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                                            int(myobj.stock),  # 在庫数
                                            images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                        )
                                        for ret_obj in ret_obj_list:
                                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                                # lotnumberを更新しておく
                                                self.buinfo_obj.set_wow_lotnum(myobj.gid, ret_obj['res_code'])
                                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                                        # 出品失敗なら 1 が返される。この場合は未出品のまま
                                        self.logger.info(
                                            '--> _chk_wowma_buyers_stock 更新OK！ 1_1 在庫[{}]'.format(myobj.stock))
                                        myobj.wow_on_flg = 1  # OKのまま
                                        myobj.wow_upd_status = 1  # 掲載中に

                                    except:
                                        # 更新時にエラー？
                                        my_err_list = {
                                            'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 1_1',
                                            'gid': myobj.gid,
                                            'status': myrtn,
                                            'code': mycode,
                                            'message': traceback.format_exc(),
                                        }
                                        error_goods_log.exe_error_log(my_err_list)
                                        continue  # DB更新せずに戻す
                                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

                                elif ret_obj['res_rtn'] != "0":
                                    self.logger.debug(
                                        "_chk_wowma_buyers_stock wowma 商品登録でエラー [{}][{}]".format(ret_obj['res_code'],
                                                                                                 ret_obj['res_msg']))
                                    chk_flg = 1  # なにかエラーになってた

                                elif ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                    self.logger.debug(
                                        "_chk_wowma_buyers_stock wowma 商品登録できた [{}][{}]".format(ret_obj['res_code'],
                                                                                                 ret_obj['res_msg']))
                                    # lotnumberを更新しておく
                                    self.buinfo_obj.set_wow_lotnum(gid, ret_obj['res_code'])

                            if chk_flg == 0:
                                # 0が返ってきて 出品OKだったら、フラグを出品済みに
                                # 出品失敗なら 1 が返される。この場合は未出品のまま
                                self.logger.debug('--> _chk_wowma_buyers_stock 登録OK！ 1')
                                myobj.wow_on_flg = 1  # OK
                                myobj.wow_upd_status = 1  # 掲載中に更新
                            else:
                                # 更新時にエラー？
                                my_err_list = {
                                    'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 2_1',
                                    'gid': myobj.gid,
                                    'status': myrtn,
                                    'code': mycode,
                                    'message': traceback.format_exc(),
                                }
                                # エラー記録だけ残して処理は続行しておく
                                error_goods_log.exe_error_log(my_err_list)

                        except:
                            # 更新時にエラー？
                            my_err_list = {
                                'batch_name': '_chk_wowma_buyers_stock wowma_update_stock point 0_3',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': myobj.gcode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(gid, tmpgretail))

                    else:
                        # 掲載中 wow_upd_status = 1
                        # 現在の在庫数で更新する
                        self.logger.debug('--> _chk_wowma_buyers_stock 掲載中。現時点の在庫数で更新')
                        try:
                            ret_obj_list = self.wowma_access.wowma_update_item_info(
                                    myobj.wow_gname,
                                    myobj.gid,
                                    myobj.gcode,
                                    tmp_wow_price,
                                    myobj.wow_fixed_price,
                                    myobj.wow_postage_segment,
                                    myobj.wow_postage,
                                    myobj.wow_delivery_method_id,
                                    myobj.wow_gdetail,
                                    myobj.wow_ctid,
                                    myobj.wow_keyword,
                                    myobj.wow_tagid,
                                    myobj.wow_upd_status,  # 1は販売中。2は販売終了。
                                    int(tmpgretail),  # 在庫数
                                    images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                            )
                            for ret_obj in ret_obj_list:
                                if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                    # lotnumberを更新しておく
                                    self.buinfo_obj.set_wow_lotnum(myobj.gid, ret_obj['res_code'])
                            myobj.wow_on_flg = 1  # 更新成功した。
                            self.logger.debug(
                                '--> _chk_wowma_buyers_stock 在庫数更新 gid:[{0}] stock:[{1}]'.format(gid, tmpgretail))
                        except:
                            # 更新時にエラー？
                            #raise Exception("在庫を0更新時に失敗？ gid:[{0}] stock:[{1}]".format(gid, tmpgretail))
                            my_err_list = {
                                'batch_name': '_chk_wowma_buyers_stock wowma_update_stock point 1_1',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': myobj.gcode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)


                else:  # 在庫数の取得エラー？
                    raise Exception("在庫数の取得に失敗？{}".format(tmpgretail))

            else:
                # ここにきたら、wow_on_flg は 2（NG）のはず。そのままにしておく
                # ただし本メソッド呼び出し時の条件で 2は除外してあるのでここには来ないはず
                self.logger.debug('--> _chk_wowma_buyers_stock 処理せず flg=2 （NG）')
                myobj.wow_on_flg = 2

            # DBを更新
            myobj.gname = tmpgname
            myobj.gdetail = tmpgdetail
            myobj.gnormalprice = int(tmpgspprice)
            myobj.stock = int(tmpgretail)
            myobj.wow_price = tmp_wow_price
            myobj.save()

        self.logger.debug('end of _chk_wowma_buyers_stock')

        return True

    # wowmaとqoo10に順次アクセスして、商品登録or在庫更新する
    def _upd_stock_info(self):

        self.logger.debug('_upd_stock_info in.')
        upd_list = []

        # qoo10の在庫更新
        self._upd_wowma_stock_info()

        # qoo10の在庫更新
        self._upd_qoo10_stock_info()

        self.logger.debug('_upd_stock_info out.')
        return

    # wowmaにアクセスして在庫更新する
    def _upd_wowma_stock_info(self):

        self.logger.debug('_upd_wowma_stock_info in.')
        upd_list = []
        myrtn = 0
        mycode = ''
        mymsg = ''

        # DBをチェックして、wow_on_flgが0(確認待ち) 2(NG) 以外なら更新してゆくか。1（OK）か３（在庫切れ）
        #result = YaBuyersItemDetail.objects.exclude(wow_on_flg=2).filter(update_date__lt=self.start_time)
        # 更新対象は、DBがバッチ処理中に更新されたものだけにする。
        result = YaBuyersItemDetail.objects.exclude(wow_on_flg=0).exclude(wow_on_flg=2).filter(update_date__gt=self.start_time)
        self.logger.debug('_upd_wowma_stock_info target_cnt [' + str(len(result)) + ']')
        for cnt, my_value in enumerate(result):
            self.logger.debug('_upd_wowma_stock_info start call qoo10_items_order_set_goods_price_qty_bulk:[]')

            # 既存DBのフラグによってどうステータスを更新するか
            # 画像情報を作らないといけない。
            images = [{'imageUrl': my_value.g_img_src_1, 'imageName': 'image_1', 'imageSeq': 1},
                      {'imageUrl': my_value.g_img_src_2, 'imageName': 'image_2', 'imageSeq': 2},
                      {'imageUrl': my_value.g_img_src_3, 'imageName': 'image_3', 'imageSeq': 3},
                      {'imageUrl': my_value.g_img_src_4, 'imageName': 'image_4', 'imageSeq': 4},
                      {'imageUrl': my_value.g_img_src_5, 'imageName': 'image_5', 'imageSeq': 5},
                      {'imageUrl': my_value.g_img_src_6, 'imageName': 'image_6', 'imageSeq': 6},
                      {'imageUrl': my_value.g_img_src_7, 'imageName': 'image_7', 'imageSeq': 7},
                      {'imageUrl': my_value.g_img_src_8, 'imageName': 'image_8', 'imageSeq': 8},
                      {'imageUrl': my_value.g_img_src_9, 'imageName': 'image_9', 'imageSeq': 9},
                      {'imageUrl': my_value.g_img_src_10, 'imageName': 'image_10', 'imageSeq': 10},
                      {'imageUrl': my_value.g_img_src_11, 'imageName': 'image_11', 'imageSeq': 11},
                      {'imageUrl': my_value.g_img_src_12, 'imageName': 'image_12', 'imageSeq': 12},
                      {'imageUrl': my_value.g_img_src_13, 'imageName': 'image_13', 'imageSeq': 13},
                      {'imageUrl': my_value.g_img_src_14, 'imageName': 'image_14', 'imageSeq': 14},
                      {'imageUrl': my_value.g_img_src_15, 'imageName': 'image_15', 'imageSeq': 15},
                      {'imageUrl': my_value.g_img_src_16, 'imageName': 'image_16', 'imageSeq': 16},
                      {'imageUrl': my_value.g_img_src_17, 'imageName': 'image_17', 'imageSeq': 17},
                      {'imageUrl': my_value.g_img_src_18, 'imageName': 'image_18', 'imageSeq': 18},
                      {'imageUrl': my_value.g_img_src_19, 'imageName': 'image_19', 'imageSeq': 19},
                      {'imageUrl': my_value.g_img_src_20, 'imageName': 'image_20', 'imageSeq': 20}]

            # 画面から出品OKになっている。以下で掲載状況を確認して更新してゆく wow_on_flg が 1（OK)か３（在庫切れ）を処理

            # 出品OKなのに在庫０なら、そのまま未掲載にしておく
            if int(my_value.stock) == 0:
                if my_value.wow_upd_status == 0 or my_value.wow_upd_status == 2:  # wowma未掲載
                    # 未掲載 wow_upd_status = 0
                    # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                    self.logger.debug('--> _chk_wowma_buyers_stock 出品OKなのに在庫０　未掲載のまま')
                    my_value.wow_on_flg = 3  # 在庫切れに切り替え
                else:
                    # 掲載中 wow_upd_status = 1
                    # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない
                    try:
                        self.wowma_access.wowma_update_stock(my_value.gid, 0, '2')
                        my_value.wow_on_flg = 3  # 更新成功したら 在庫切れにする
                        my_value.wow_upd_status = 2  # 未掲載に
                        self.logger.debug('--> _chk_wowma_buyers_stock 在庫切れにした。')
                    except:
                        #raise Exception("在庫を0更新時に失敗？{}".format(my_value.gid))
                        # 更新時にエラー？
                        self.logger.debug('--> _chk_wowma_buyers_stock エラー gid:[{}] msg[{}]'.format(my_value.gid,mymsg))
                        my_err_list = {
                            'batch_name': 'wowma_stock_chk wowma_update_stock point 1',
                            'gid': my_value.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        continue  # DB更新せずに戻す

            # 　在庫がある
            elif int(my_value.stock) > 0:
                # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                if my_value.wow_upd_status == 0:
                    self.logger.debug('--> _chk_wowma_buyers_stock 未登録だが出品OKで在庫あるので登録開始')
                    # 未掲載 wow_upd_status = 0
                    try:
                        ret_obj_list = self.wowma_access.wowma_register_item_info(
                                                               my_value.wow_gname,
                                                               my_value.gid,
                                                               my_value.gcode,
                                                               my_value.wow_price,
                                                               my_value.wow_fixed_price,
                                                               my_value.wow_postage_segment,
                                                               my_value.wow_postage,
                                                               my_value.wow_delivery_method_id,
                                                               my_value.wow_gdetail,
                                                               my_value.wow_ctid,
                                                               my_value.wow_keyword,
                                                               my_value.wow_tagid,
                                                               1,  # 1は販売中。。出品OKなので販売中 ( 1 ) にしておく
                                                               int(my_value.stock), # 在庫数
                                                               images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                                               )

                        chk_flg = 0
                        for ret_obj in ret_obj_list:
                            # PME0106:入力された商品コードは、既に登録されています。
                            if ret_obj['res_rtn'] == '1' and ret_obj['res_code'] == 'PME0106':
                                # 出品していいはずなので、更新をかけ直す
                                try:
                                    ret_obj_list = self.wowma_access.wowma_update_item_info(
                                        my_value.wow_gname,
                                        my_value.gid,
                                        my_value.gcode,
                                        my_value.wow_price,
                                        my_value.wow_fixed_price,
                                        my_value.wow_postage_segment,
                                        my_value.wow_postage,
                                        my_value.wow_delivery_method_id,
                                        my_value.wow_gdetail,
                                        my_value.wow_ctid,
                                        my_value.wow_keyword,
                                        my_value.wow_tagid,
                                        1,  # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                                        int(my_value.stock),  # 在庫数
                                        images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                    )
                                    for ret_obj in ret_obj_list:
                                        if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                            # lotnumberを更新しておく
                                            self.buinfo_obj.set_wow_lotnum(my_value.gid, ret_obj['res_code'])
                                    # 0が返ってきて 出品OKだったら、フラグを出品済みに
                                    # 出品失敗なら 1 が返される。この場合は未出品のまま
                                    self.logger.info(
                                        '--> _chk_wowma_buyers_stock 更新OK！ 1 在庫[{}]'.format(my_value.stock))
                                    my_value.wow_on_flg = 1  # OKのまま
                                    my_value.wow_upd_status = 1  # 掲載中に

                                except:
                                    # 更新時にエラー？
                                    my_err_list = {
                                        'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 1',
                                        'gid': my_value.gid,
                                        'status': myrtn,
                                        'code': mycode,
                                        'message': traceback.format_exc(),
                                    }
                                    error_goods_log.exe_error_log(my_err_list)
                                    continue  # DB更新せずに戻す
                                    # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

                            elif ret_obj['res_rtn'] != "0":
                                self.logger.debug(
                                    "_chk_wowma_buyers_stock qoo10 商品検索でエラー [{}][{}]".format(ret_obj['res_code'],
                                                                                                 ret_obj['res_msg']))
                                chk_flg = 1  # なにかエラーになってた
                            elif ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                self.logger.debug(
                                    "_chk_wowma_buyers_stock wowma 商品登録できた [{}][{}]".format(
                                        ret_obj['res_code'],
                                        ret_obj['res_msg']))
                                # lotnumberを更新しておく
                                self.buinfo_obj.set_wow_lotnum(my_value.gid, ret_obj['res_code'])

                        if chk_flg == 0:
                            # 0が返ってきて 出品OKだったら、フラグを出品済みに
                            # 出品失敗なら 1 が返される。この場合は未出品のまま
                            self.logger.debug('--> _upd_wowma_stock_info 登録OK！')
                            my_value.wow_on_flg = 1  # OK
                            my_value.wow_upd_status = 1  # 掲載中に更新
                        else:
                            # 更新時にエラー？
                            my_err_list = {
                                'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 2',
                                'gid': my_value.gid,
                                'status': myrtn,
                                'code': mycode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            continue  # DB更新せずに戻す
                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 3_1',
                            'gid': my_value.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        continue  # DB更新せずに戻す

                else:
                    # 掲載中 wow_upd_status = 1　か 2（登録済みだが未掲載）
                    # 現在の在庫数で更新する
                    self.logger.debug('--> _upd_wowma_stock_info 掲載中。現時点の在庫数で更新 gid[{}] stock[{}]'.format(my_value.gid, my_value.stock))
                    try:
                        self.wowma_access.wowma_update_stock(my_value.gid, int(my_value.stock), '1')
                        my_value.wow_on_flg = 1  # 更新成功した。
                        my_value.wow_upd_status = 1  # 掲載中に更新
                        self.logger.debug(
                            '--> _upd_wowma_stock_info 在庫数更新 gid:[{0}] stock:[{1}]'.format(my_value.gid,
                                                                                           my_value.stock))

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 3',
                            'gid': my_value.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        self.logger.debug(
                            '--> _upd_wowma_stock_info 在庫数更新時にエラー？ gid:[{0}] stock:[{1}]'.format(my_value.gid, my_value.stock))
                        continue  # DB更新せずに戻す
                        #raise Exception("在庫を0更新時に失敗？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock))

                    # 続いて価格も更新
                    try:
                        self.wowma_access.wowma_update_item_price(
                                my_value.gid,
                                int(my_value.wow_price),
                                int(my_value.wow_fixed_price))
                        self.logger.debug(
                            '--> _upd_wowma_stock_info 価格更新OK gid:[{0}] price:[{1}]'.format(
                                my_value.gid, my_value.wow_price))
                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 3',
                            'gid': my_value.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': "価格を更新時に失敗？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        self.logger.debug("価格を更新時に失敗？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock))
                        continue  # DB更新せずに戻す
                        # raise Exception("価格を0更新時に失敗？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock))

            else: # 在庫数の取得エラー？
                my_err_list = {
                    'batch_name': 'wowma_stock_chk _chk_wowma_buyers_stock point 4',
                    'gid': my_value.gid,
                    'status': myrtn,
                    'code': mycode,
                    'message': "価格を0更新時に失敗？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock),
                }
                error_goods_log.exe_error_log(my_err_list)
                self.logger.debug("在庫数の取得エラー？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock))
                continue  # DB更新せずに戻す
                #raise Exception("在庫数の取得に失敗？{}".format(my_value.stock))

            my_value.save()
        return


    # qoo10にアクセスして在庫更新する
    # JSON形式の価格、数量、有効期限 (最大 500)
    # 例: [{"ItemCode":"String","SellerCode":"String","Price":String,"Qty":String,"ExpireDate":"String"},{"ItemCode":"String","SellerCode":"String","Price":String,"Qty":String,"ExpireDate":"String"}]
    def _upd_qoo10_stock_info(self):

        self.logger.debug('_upd_qoo10_stock_info in.')
        upd_list = []

        # DBをチェックして、qoo_on_flg(確認待ち) ２（NG）以外なら更新してゆくか。
        #result = YaBuyersItemDetail.objects.exclude(wow_on_flg=2).filter(update_date__lt=self.start_time)
        # 更新対象は、DBがバッチ処理中に更新されたものだけにする。
        result = YaBuyersItemDetail.objects.exclude(qoo_on_flg=0).exclude(qoo_on_flg=2).filter(update_date__gt=self.start_time)
        self.logger.debug('_upd_qoo10_stock_info target_cnt [' + str(len(result)) + ']')
        for cnt, my_value in enumerate(result):
            #self.logger.debug('_upd_qoo10_stock_info start call qoo10_items_order_set_goods_price_qty_bulk:[]')

            # エラー時のデータ復帰用に一時保持
            tmp_qoo_on_flg = my_value.qoo_on_flg
            tmp_qoo_upd_status = my_value.qoo_upd_status

            # 出品OKなのに在庫０なら、そのまま未掲載にしておく
            if int(my_value.stock) == 0:
                if my_value.qoo_upd_status == 1 or my_value.qoo_upd_status == 3:  # 取引待機か取引廃止
                    # 未掲載 qoo_upd_status = 1
                    # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                    self.logger.debug('--> _upd_qoo10_stock_info[{}] 出品OKなのに在庫０　未掲載のまま'.format(my_value.qoo_gdno))
                    my_value.qoo_on_flg = 3  # 在庫切れに切り替え
                else:
                    # 掲載中 qoo_upd_status = 2
                    # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない
                    # 在庫更新
                    tmp_list = {
                        "ItemCode": my_value.qoo_gdno,
                        "SellerCode": my_value.qoo_seller_code,
                        "Price": my_value.qoo_price,
                        "Qty": my_value.stock,
                        "ExpireDate": "",
                    }
                    if my_value.qoo_gdno != "":  # qoo10の商品コードが登録済みの場合だけリストに追加
                        #my_value.qoo_on_flg = 3  # 在庫切れにする
                        #my_value.qoo_upd_status = 1  # 取引待機に
                        # ステータス更新する
                        if my_value.qoo_upd_status != 1:  # 1じゃない場合のみ1で更新かける
                            my_value.qoo_on_flg = 3  # 在庫切れにする
                            my_value.qoo_upd_status = 1  # 取引待機に
                            try:
                                self.qoo10_access.qoo10_items_basic_edit_goods_status(my_value)
                            except:
                                self.logger.debug(
                                    '_upd_qoo10_stock_info error occurred. msg:[{}]'.format(traceback.format_exc()))
                                # 更新時にエラー？
                                my_err_list = {
                                    'batch_name': 'wowma_stock_chk _upd_qoo10_stock_info point 1',
                                    'gid': my_value.gid,
                                    'status': 1,
                                    'code': 0,
                                    'message': traceback.format_exc(),
                                }
                                error_goods_log.exe_error_log(my_err_list)

                                my_value.qoo_on_flg = tmp_qoo_on_flg  # ステータスは元に戻す
                                my_value.qoo_upd_status = tmp_qoo_upd_status

                                continue
                                #return False

                        upd_list.append(tmp_list)

                    # 500回毎にAPI call
                    #if cnt % 500 == 0:
                    if len(upd_list) % 500 == 0:
                        # qoo10の500件まとめてアップするAPIをcall
                        try:
                            self.qoo10_access.qoo10_items_order_set_goods_price_qty_bulk(upd_list)
                        except:
                            # 更新時にエラー？
                            my_err_list = {
                                'batch_name': 'wowma_stock_chk qoo10_items_order_set_goods_price_qty_bulk point 2',
                                'gid': my_value.gid,
                                'status': 1,
                                'code': 0,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            # 失敗したので更新リストはクリアするか
                            upd_list = []
                            my_value.qoo_on_flg = tmp_qoo_on_flg  # ステータスは元に戻す
                            my_value.qoo_upd_status = tmp_qoo_upd_status
                            continue

                        # 成功、送信するリストはクリアしてやり直し
                        upd_list = []
                        self.logger.debug('--> _upd_qoo10_stock_info 在庫切れにした。[{}]'.format(my_value.gid))
                    else:
                        pass
                        #raise Exception("在庫を0更新時に失敗？{}".format(my_value.gid))

            # 　在庫がある
            elif int(my_value.stock) > 0:
                # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                if my_value.qoo_upd_status == 1:
                    self.logger.debug('--> _upd_qoo10_stock_info[{}] 未掲載だが出品OKで在庫あるので登録開始'.format(my_value.gid))
                    # 取引待機 qoo_upd_status = 1

                    # qoo10_items_basic_set_new_goods を呼ばないと。
                    try:
                        # qoo10_my_set_new_goods に切り替え
                        #self.qoo10_access.qoo10_items_basic_set_new_goods(my_value)
                        self.qoo10_access.qoo10_my_set_new_goods(my_value)
                    except:
                        # 更新時にエラー？
                        self.logger.debug('--> error. qoo10_items_basic_set_new_goods 1 gid:[{}] msg[{}] '.format(my_value.gid, traceback.format_exc()))
                        my_err_list = {
                            'batch_name': 'wowma_stock_chk qoo10_items_basic_set_new_goods point 3',
                            'gid': my_value.gid,
                            'status': 1,
                            'code': 0,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        continue

                    # 0が返ってきて 出品OKだったら、フラグを出品済みに
                    # 出品失敗なら 1 が返される。この場合は未出品のまま
                    self.logger.debug('--> _upd_qoo10_stock_info 登録OK！')
                    my_value.qoo_on_flg = 1  # OKのまま
                    my_value.qoo_upd_status = 2  # 取引可能に更新

                    # ステータス更新する
                    # qoo10_my_set_new_goods に切り替えたので下記不要
                    """
                    try:
                        self.qoo10_access.qoo10_items_basic_edit_goods_status(my_value)
                    except:
                        # 更新時にエラー？
                        self.logger.debug('--> error. qoo10_items_basic_edit_goods_status 2 gid:[{}] msg[{}] '.format(my_value.gid, traceback.format_exc()))
                        my_err_list = {
                            'batch_name': 'wowma_stock_chk qoo10_items_basic_edit_goods_status point 4',
                            'gid': my_value.gid,
                            'status': 1,
                            'code': 0,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        continue
                    """
                else:
                    # 掲載中 qoo_upd_status = 2か3
                    # 現在の在庫数で更新する
                    tmp_list = {
                        "ItemCode": my_value.qoo_gdno,
                        "SellerCode": my_value.qoo_seller_code,
                        "Price": str(my_value.qoo_price),
                        "Qty": str(my_value.stock),
                        "ExpireDate": "",
                    }
                    # qoo_upd_status が3（取引廃止）以外、かつ
                    # qoo10の商品コードが登録済みの場合だけリストに追加
                    if my_value.qoo_gdno != "" and my_value.qoo_upd_status != 3:

                        #my_value.qoo_on_flg = 3  # 在庫切れにする
                        #my_value.qoo_upd_status = 1  # 取引待機に
                        # ステータス更新する
                        if my_value.qoo_upd_status != 2:  # 1じゃない場合のみ1で更新かける

                            my_value.qoo_on_flg = 1  # 更新成功した。
                            my_value.qoo_upd_status = 2  # 取引可能に更新

                            # ステータス更新する
                            try:
                                self.qoo10_access.qoo10_items_basic_edit_goods_status(my_value)
                            except:
                                # 更新時にエラー？
                                self.logger.debug(
                                    '--> error. qoo10_items_basic_edit_goods_status 3 gid:[{}] msg[{}] '.format(
                                        my_value.gid, traceback.format_exc()))
                                my_err_list = {
                                    'batch_name': 'wowma_stock_chk qoo10_items_basic_edit_goods_status point 5',
                                    'gid': my_value.gid,
                                    'status': 1,
                                    'code': 0,
                                    'message': traceback.format_exc(),
                                }
                                error_goods_log.exe_error_log(my_err_list)
                                my_value.qoo_on_flg = tmp_qoo_on_flg  # ステータスは元に戻す
                                my_value.qoo_upd_status = tmp_qoo_upd_status
                                continue

                        upd_list.append(tmp_list)

                    # 500回毎にAPI call
                    if len(upd_list) % 500 == 0:
                        # qoo10の500件まとめてアップするAPIをcall
                        try:
                            self.qoo10_access.qoo10_items_order_set_goods_price_qty_bulk(upd_list)
                        except:
                            # 更新時にエラー？
                            self.logger.debug(
                                '--> error. qoo10_items_order_set_goods_price_qty_bulk 4 gid:[{}] msg[{}] '.format(
                                    my_value.gid, traceback.format_exc()))
                            my_err_list = {
                                'batch_name': 'wowma_stock_chk qoo10_items_order_set_goods_price_qty_bulk point 6',
                                'gid': my_value.gid,
                                'status': 1,
                                'code': 0,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            my_value.qoo_on_flg = tmp_qoo_on_flg  # ステータスは元に戻す
                            my_value.qoo_upd_status = tmp_qoo_upd_status
                            upd_list = []
                            continue

                        # 成功、送信するリストはクリアしてやり直し
                        upd_list = []
                    else:
                        pass

            else:  # 在庫数の取得エラー？
                self.logger.debug(
                    '--> error. _upd_qoo10_stock_info 5 gid:[{}] msg[{}] '.format(
                        my_value.gid, traceback.format_exc()))
                my_err_list = {
                    'batch_name': 'wowma_stock_chk _upd_qoo10_stock_info point 3',
                    'gid': my_value.gid,
                    'status': 1,
                    'code': 0,
                    'message': "在庫数の取得に失敗？gid:[{}] stock:[{}]".format(my_value.gid, my_value.stock),
                }
                error_goods_log.exe_error_log(my_err_list)
                continue
                #raise Exception("在庫数の取得に失敗？gid:[{0}] stock:[{}]".format(my_value.gid, my_value.stock))

            my_value.save()

        try:
            self.qoo10_access.qoo10_items_order_set_goods_price_qty_bulk(upd_list)
        except:
            # 更新時にエラー？
            self.logger.debug(
                '--> error. qoo10_items_order_set_goods_price_qty_bulk 6 gid:[{}] msg[{}] '.format(
                    my_value.gid, traceback.format_exc()))
            my_err_list = {
                'batch_name': 'wowma_stock_chk qoo10_items_order_set_goods_price_qty_bulk point 7',
                'gid': my_value.gid,
                'status': 1,
                'code': 0,
                'message': traceback.format_exc(),
            }
            error_goods_log.exe_error_log(my_err_list)

        self.logger.debug('end of _upd_qoo10_stock_info')

        return True


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


    # 詳細ページにアクセスしてECAUTOのカテゴリ設定用に編集する
    # ※画像は保存しない
    def _get_wowma_buyers_detail_for_ecauto(self, row):
        self.logger.debug('_get_wowma_buyers_detail_for_ecauto in.')

        try:
            # アイテムコードを画像URL ( row[5] ）から取ってくる
            tmpitemcd = re.findall('_(.+)_', row[5])
            if len(tmpitemcd[0]) < 7:
                self.logger.debug('_get_wowma_buyers_detail_for_ecauto row[5] itemcd is illegal.')
                self.logger.debug('-----> _get_wowma_buyers_detail_for_ecauto  row[5][{}] itemcd is illegal.'.format(tmpitemcd[0]))
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
                #self.logger.debug('-----> _get_wowma_buyers_detail_for_ecauto cant get [detailInfo].')
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
                #self.logger.debug('----- > _get_wowma_buyers_detail_for_ecauto cant match tmpyct.')
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
    def _get_wowma_buyers_detail(self, d_url, gid, gcd):
        self.logger.debug('_get_wowma_buyers_detail in.')

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
        self.common_chrome_driver.driver.switch_to_window(handles[1])
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

            tmp_g_img_src[tmp_cnt] = str(tmpgsrc)
            tmp_cnt += 1

            """
            # 画像保存してみる
            myresponce = requests.get(tmpgsrc)
            if cnt == 0:
                tmpimgfname = gid
            else:
                tmpimgfname = gid + '_' + str(cnt)
            with open(mydwimg_dir + "{}.jpg".format(tmpimgfname), "wb") as myf:
                myf.write(myresponce.content)
            """

            cnt += 1
            if tmp_cnt == 20:
                break

        # 親のウィンドウに戻る
        #self.common_chrome_driver.driver.switch_to_window(handles[0])
        self.common_chrome_driver.driver.close()
        self.common_chrome_driver.driver.switch_to_window(handles[0])

        # 商品詳細の各要素を取得する

        #tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        #tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 商品名
        tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='itemInfo']/h2").text

        # 商品詳細
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
        tmp_wow_gname = tmpgname_obj[0]
        if tmpgname_obj[1] == 1:
            ng_flg = 1

        # 不要文字削除
        # 商品説明より削除
        tmpgdetail_obj = self.bubrandinfo_obj.chk_goods_detail(tmpgdetail)
        tmp_wow_gdetail = tmpgdetail_obj[0]
        if tmpgdetail_obj[1] == 1:
            ng_flg = 1

        if tmpgdetail_obj[1] == 5:
            ng_flg = 1

        if tmpgdetail_obj[1] == 6:
            tmpyct_flg = 6  # NGワードが商品詳細に含まれる、要確認

        # ===============================
        # 通常価格
        tmpgspprice = int(re.sub("\\D", "",
                             self.common_chrome_driver.driver.find_element_by_xpath(
                                 "//li[@id='M_usualValue']/span").text))

        # wowmaの価格を算出
        # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
        # 利益額を、価格帯で変えてみる。
        wow_benefit = 500
        if tmpgspprice < 500:
            wow_benefit = 300
        elif 500 <= tmpgspprice < 2000:
            wow_benefit = 400
        elif 2000 <= tmpgspprice < 3000:
            wow_benefit = 500
        elif 3000 <= tmpgspprice < 5000:
            wow_benefit = 700
        else:
            wow_benefit = 1000
        tmp_wow_price=(int(tmpgspprice) * 1.1) + wow_benefit

        # ===============================
        # 在庫数の抽出
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//span[@class='M_item-stock-smallstock']")) == 0:
            # 在庫が取れないときは在庫切れか
            self.logger.debug('_get_wowma_buyers_detail cant get [M_item-stock-smallstock].')
            tmpgretail = "0"
        else:
            tmpgretail = re.sub("\\D", "",
                                self.common_chrome_driver.driver.find_element_by_xpath(
                                    "//span[@class='M_item-stock-smallstock']").text)
        # wowmaの在庫は、在庫切れなら 2、ほかは未出品にする
        if tmpgretail == "0":
            tmp_wow_on_flg = 2
        else:
            tmp_wow_on_flg = 0

        tmpgcode = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='detailInfo']/ul/li[4]").text

        # カテゴリコードはとりあえず一つ。パンくずの末尾をとってみる
        for ii in self.common_chrome_driver.driver.find_elements_by_xpath("//p[@class='pankuzu']/a"):
            # カテゴリ一致するかリスト引いて、マッチしたらそいつをセットしてループは抜ける
            tmpct =  ii.get_attribute('href') # 文字はちゃんと整形して
            tmpct = re.sub('https://buyerz.shop/shopbrand/', "", tmpct)
            tmpct = re.sub('/', "", tmpct)
            tmpyct = self.buinfo_obj.chk_ct(tmpct, tmpgname)
            if tmpyct is True:
                break

        # ここでtmpyctが取れてない（False）だったらNGか。
        # とりあえず、とれてなくてもあまり気にしないように。
        # ※wowmaでは、ヤフオクカテゴリじゃなくwowmaカテゴリに割り当てるのだが。
        if tmpyct is False:
            self.logger.debug('_get_wowma_buyers_detail cant match tmpyct.gid:[' + str(gid) + ']')
            return False

        #self.logger.debug('gid:[' + str(tmpgid) + ']')
        self.logger.debug('d-gid:[' + str(gid) + ']')
        self.logger.debug('d-gname:[' + str(tmpgname) + ']')
        self.logger.debug('d-gdetail:[' + str(tmpgdetail) + ']')
        self.logger.debug('d-gspprice:[' + str(tmpgspprice) + ']')
        self.logger.debug('d-gretail:[' + str(tmpgretail) + ']')
        self.logger.debug('d-gcode:[' + str(tmpgcode) + ']')
        self.logger.debug('d-tmpct:[' + str(tmpct) + ']')


        # DBに保存
        self.logger.debug('start save YaBuyersItemDetail')
        if not YaBuyersItemDetail.objects.filter(gid=tmpgid).exists():
            self.logger.debug('start save YaBuyersItemDetail add.')
            obj, created = YaBuyersItemDetail.objects.update_or_create(
                gid=tmpgid,
                gcode=gcd,
                glink=d_url,
                gname=tmpgname,
                gdetail=tmpgdetail,
                gnormalprice=int(tmpgspprice),
                stock=int(tmpgretail),
                wow_gname=tmp_wow_gname,
                wow_gdetail=tmp_wow_gdetail,
                wow_price=tmp_wow_price,
                wow_on_flg=tmp_wow_on_flg,
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

    """
    # バイヤーズにログインしておく
    def login_buyers(self):
        try:
            self.logger.debug('login_buyers start.')

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

            self.logger.debug('login_buyers end.')

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise Exception("バイヤーズのログインに失敗しました。")

        return True
    """

    # wowmaにログインしておく
    def wowma_login(self):
        try:
            self.logger.debug('login_wowma start.')

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

            self.logger.debug('login_wowma end.')

        except Exception as e:
            self.logger.debug(traceback.format_exc())
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
                self.logger.debug('---> start read_csv')
                rtn = self.read_csv(my_file)

                # CSV取り込みできたらwrite
                self.logger.debug('---> start write_csv')
                rtn = self.write_csv()

                # CSVは処理済みに移動
                self.logger.debug('---> start move_csv')
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
                #self.logger.debug('---> read_csv in')

                self.logger.debug('read_row start. 行の列項目をチェック ')
                #print(', '.join(row))
                cnt += 1
                self.logger.debug('read_row cnt. {}'.format(cnt))
                self.logger.debug('read_row cnt. {}'.format(cnt))
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
                        self.logger.debug('---> read_csv get_wowma false?? ')

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
            self.logger.debug(traceback.format_exc())
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
            self.logger.info(traceback.format_exc())
            return False

        # =====================================================================
        # ★★wowma用の在庫チェックバッチのなかでやる。
        # バイヤーズの在庫を巡回して、在庫数や価格を更新。
        # チェック対象は、yaget_yabuyersitemdetail　に登録済みのもの。
        # wowmaへの本登録は、在庫バッチを回して在庫があったとき。
        # 在庫があり、出品済みフラグを見て、まだ未出品のものは出品のフローを。出品済みであれば在庫数や価格のチェックと更新を行う
        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('wowma_stock_chk handle is called')
            self.batch_status = BatchStatusUpd('wowma_stock_chk')
            self.batch_status.start()

            self.common_chrome_driver = CommonChromeDriver(self.logger)

            # self.common_chrome_driver.driverにセット
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            # self.init_chrome_with_tor()

            # 保存してみる
            # if not os.path.exists(mydwsrc_dir):
            #    os.mkdir(mydwsrc_dir)
            self.logger.debug('wowma_stock_chk handle start get')

            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            self.buinfo_obj = BuyersInfo(self.logger)
            self.bubrandinfo_obj = BuyersBrandInfo(self.logger)
            self.wowma_access = WowmaAccess(self.logger)
            self.qoo10_access = Qoo10Access(self.logger)

            self.qoo10_access.qoo10_create_cert_key()

            #my_ct_list = self.buinfo_obj.get_ct()
            #self.logger.info('start exec get_buers_info.list:[{}]'.format(my_ct_list))

            # バイヤーズにログインしておく
            self.buinfo_obj.login_buyers()

            # 商品リストを取得対象のURL（カテゴリコード）を取得する。
            self.my_wowma_target_ct_list = self.buinfo_obj.get_url_list_for_wowma()

            # 在庫チェックの母体
            # これは指定した商品カテゴリのリストをチェックするだけ
            #self._exec_wowma_stock_chk() # こっちを呼ぶと、商品詳細毎に在庫更新・価格更新を走らせている
            self._chk_buyers_stock_from_list()

            # カテゴリリストのチェックにかからなかった商品を個別にチェックしてDBの在庫更新
            self._chk_buyers_stock_from_remaining_items()

            # wowmaとqoo10側に在庫更新を行う
            self._upd_stock_info()

            self.logger.info('wowma_stock_chk handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.logger.info('exception occurred.')
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            self.common_chrome_driver.quit_chrome_with_tor()
            return

        #self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('wowma_stock_chk handle end')
        return
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))

