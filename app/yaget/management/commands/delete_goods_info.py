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
logging.config.fileConfig(fname="/app/yaget/management/commands/delete_goods_info.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

#logger.setLevel(20)

# 共通変数
mydwsrc_dir = "/app/yaget/wowma_buyers/dwsrc"
mydwimg_dir = "/app/yaget/wowma_buyers/dwimg/"
myupdcsv_dir = "/app/yaget/wowma_buyers/updcsv/"
mydeletecsv_dir = "/app/yaget/wowma_buyers/deletecsv/"

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
    #def add_arguments(self, parser):
    #    parser.add_argument('s_url', nargs='+')

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

    # バイヤーズで取り込み対象のカテゴリ全てのリンクに対してアクセスし、
    # 登録されている商品情報に対して価格・在庫の更新をする
    def _chk_buyers_stock_from_list(self):

        self.logger.info('_chk_buyers_stock_from_list in.')
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

        self.logger.info('_chk_buyers_stock_from_list out.')
        return



    # バイヤーズで登録済みの商品について、在庫チェックを行い
    # 在庫数や価格を改定してゆく
    # こちらは商品詳細をひとつづつなめていく版。
    def _exec_wowma_stock_chk(self):

        self.logger.info('_exec_wowma_stock_chk in .')
        # self.YaBuyersItemDetail に登録済みの商品から、
        # wow_on_flg　が(2：NG）の設定ではない かつ wow_upd_statusが (1:掲載中) のものを全て対象とする
        #  →　いや、wow_upd_statusが０（未掲載）のものもいったんチェックして、未登録のものでOKになるなら後続で登録までしてしまう
        #result = YaBuyersItemDetail.objects.exclude(wow_on_flg=2).filter(wow_upd_status=1)
        result = YaBuyersItemDetail.objects.\
            select_related('black_list').filter(black_list__isnull=True).\
            exclude(wow_on_flg=2)
        self.logger.info('_exec_wowma_stock_chk target_cnt [' + str(len(result)) + ']')
        for my_value in result:
            # 形式は　https://buyerz.shop/shopbrand/ct113/
            self.logger.info('_exec_wowma_stock_chk url:[' + str(my_value.glink) + ']')
            self._chk_wowma_buyers_stock(my_value.glink, my_value.gid, my_value.gcode)
        self.logger.info('_exec_wowma_stock_chk out .')

        return


    # wowmaとqoo10に順次アクセスして、商品登録or在庫更新する
    def _upd_stock_info(self):

        self.logger.info('_upd_stock_info in.')
        upd_list = []

        # qoo10の在庫更新
        self._upd_wowma_stock_info()

        # qoo10の在庫更新
        self._upd_qoo10_stock_info()

        self.logger.info('_upd_stock_info out.')
        return

    # wowmaにアクセスして在庫更新する
    def _upd_wowma_stock_info(self):

        self.logger.info('_upd_wowma_stock_info in.')
        return


    # qoo10にアクセスして在庫更新する
    # JSON形式の価格、数量、有効期限 (最大 500)
    # 例: [{"ItemCode":"String","SellerCode":"String","Price":String,"Qty":String,"ExpireDate":"String"},{"ItemCode":"String","SellerCode":"String","Price":String,"Qty":String,"ExpireDate":"String"}]
    def _upd_qoo10_stock_info(self):


        return True


    # csv の格納ディレクトリから１ファイルずつ読み込む
    def _read_csv_dir(self):
        self.logger.debug('read_csv_dir start.')
        try:
            # 指定のディレクトリ配下を読み込む
            # csv 読み込み
            #file_list = glob.glob(UPLOAD_DIR + "*")
            file_list = glob.glob(mydeletecsv_dir + "*")

            for my_file in file_list:
                self.logger.info('---> start read_csv')
                rtn = self._read_csv(my_file)

                # CSVは処理済みに移動
                self.logger.info('---> start move_csv')
                self._move_csv(my_file)

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
    def _move_csv(self, csvname):
        new_path = shutil.move(
            csvname,
            DONE_CSV_DIR + "{0:%Y%m%d_%H%M%S}".format(datetime.datetime.now()) + "_" + os.path.split(csvname)[1])
        return

    # 指定されたcsv単位で処理する。
    # csv を読み込み処理
    def _read_csv(self, csvname):

        f = None
        try:
            f = codecs.open(csvname, 'r', 'utf-8')
            #f = codecs.open(csvname, 'r', 'shift-jis')
            #f = codecs.open(csvname, 'r', 'cp932')
            reader = csv.reader(f, delimiter=',')

            self.logger.info('read_row csvname:[{}]'.format(csvname))

            self.logger.debug('read_row start. 行の列項目をチェック ')
            for cnt, row in enumerate(reader):
                self.logger.info('read_row start. [{}]'.format(row))
                self.logger.debug('read_row cnt. {}'.format(cnt))
                if cnt == 0:  # 先頭行のチェック
                    self.logger.debug('---> read_csv in cnt =0')
                    # 行頭の列数をチェック
                    if len(row) != 2:
                        raise Exception("CSVのフォーマットが不正です。列項目は商品ID、商品名の２つにします。len[{}]".format(len(row)))
                else:
                    # ここからCSVの行ごとに内容をチェック。DB更新から、wowma、qoo10も１商品ずつ削除してしまう
                    self._delete_wowma_qoo_item_info(row[0])

        except Exception as e:
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            if f:
                f.close()
            return False  # 途中NGなら 0 return で処理済みにしない

        # Exceptionが飛んでなかったら正常に処理終了
        if f:
            f.close()
        self.logger.debug('---> _read_csv ok, next csv')
        return

    # wowma,qoo10から商品を削除、DBからも削除
    def _delete_wowma_qoo_item_info(self, gid):

        self.logger.info('_delete_wowma_qoo_item_info in.')

        # 既存DBのフラグによってどうステータスを更新するか
        # 削除処理
        try:
            myobj = YaBuyersItemDetail.objects.filter(gid=gid).first()
            if not myobj:
                # データがないとエラーに。
                raise Exception("_delete_wowma_qoo_item_info 未登録のgidが指定されました。gid[{}]".format(gid))

            # qoo10のステータスを削除に更新
            # Qoo10にアクセス

            myobj.qoo_upd_status = 3  # 取引廃止

            # qoo10から削除
            # まず登録があるかどうか。なかったら処理しない
            ret_obj_list = self.qoo10_access.qoo10_items_lookup_get_item_detail_info(myobj)
            chk_flg = 0
            for ret_obj in ret_obj_list:
                if ret_obj['res_code'] != "0":
                    self.logger.debug("_delete_wowma_qoo_item_info qoo10 商品検索でエラー [{}][{}]".format(ret_obj['res_code'],ret_obj['res_msg'] ))
                    chk_flg = 1  # なにかエラーになってた
            if chk_flg == 0:
                # 商品が見つかったときだけqoo10から削除
                self.qoo10_access.qoo10_items_basic_edit_goods_status(myobj)
                self.logger.debug("_delete_wowma_qoo_item_info qoo10 削除更新 ok")
            else:
                self.logger.debug("_delete_wowma_qoo_item_info qoo10 で対象商品が見つからないのでスルー。wowmaの処理に続く")

            # 続けてwowmaから削除
            # まず商品ステータスを変えてから
            if self.wowma_access.wowma_update_stock(myobj.gid, 0, '2') == 0:
                self.logger.debug('_delete_wowma_qoo_item_info wow_delete wowma_update_stock ok.')
                ret_code, ret_msg = self.wowma_access.wowma_delete_item_infos(myobj.gid)
                if ret_code == 0:
                    self.logger.info('_delete_wowma_qoo_item_info wow 削除更新 ok')
                else:
                    self.logger.debug('_delete_wowma_qoo_item_info wow_delete エラー？.[{}][{}]'.format(ret_code, ret_msg))
                    raise Exception('_delete_wowma_qoo_item_info wow_delete エラー？gid[{}][{}][{}]'.format(myobj.gid, ret_code, ret_msg))
            else:
                logger.debug("_delete_wowma_qoo_item_info  wowma で対象商品が見つからないのでスルー。DBから消す")

            # ここまできたら、DBから削除
            myobj.delete()

        except Exception as e:
            raise

        logger.debug("_delete_wowma_qoo_item_info 削除成功")
        return

        # =====================================================================
        # 指定されたディレクトリにアップされた商品CSVを読み込んで
        # 順次DBを更新。かつwowmaとqoo10から削除する。
        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('delete_goods_info handle is called')
            self.batch_status = BatchStatusUpd('delete_goods_info')
            self.batch_status.start()

            #self.common_chrome_driver = CommonChromeDriver(self.logger)

            # self.common_chrome_driver.driverにセット
            #self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            # self.init_chrome_with_tor()

            self.logger.debug('delete_goods_info handle start get')

            self.wowma_access = WowmaAccess(self.logger)
            self.qoo10_access = Qoo10Access(self.logger)

            self.qoo10_access.qoo10_create_cert_key()

            # アップロードされたディレクトリを探索して格納済みのCSVを全部処理
            self._read_csv_dir()

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            #self.common_chrome_driver.quit_chrome_with_tor()
            return

        #self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('delete_goods_info handle end')
        return

