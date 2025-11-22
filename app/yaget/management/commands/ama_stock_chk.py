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
from yaget.models import QooAsinDetail, WowmaGoodsDetail
from yaget.integrations.batch_status import BatchStatusUpd
from yaget.AmaSPApi import AmaSPApi, AmaSPApiAsinDetail, AmaSPApiQooAsinDetail
from yaget.modules import ExecQoo10, ExecWowma

#from yaget.AmaMws import AmaMwsProducts

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
#logging.config.fileConfig(fname="/app/yaget/management/commands/stock_chk_logging.config", disable_existing_loggers=False)


#logger.setLevel(20)

rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/management/commands/log/ama_stock_chk.log',
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

logger = logging.getLogger(__name__)
logger.addHandler(rh)
logger.addHandler(ch)

# 共通変数
mydwsrc_dir = "/app/yaget/dwsrc"
mydwimg_dir = "/app/yaget/dwimg/"
myupdcsv_dir = "/app/yaget/updcsv/"

UPLOAD_DIR = '/app/yaget/dwcsv/'
DONE_CSV_DIR = '/app/yaget/donecsv/'

USER_DATA_DIR = '/app/yaget/userdata/'

def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class Command(BaseCommand):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        help = 'ama stock chk and upd'
        self.logger.debug('ama_stock_chk Command in. init')
        self.common_chrome_driver = None
        self.driver = None
        self.upd_csv = []
        self.my_wowma_target_ct_list = []
        self.start_time = datetime.datetime.now()
        self.batch_status = None
        self._ama_spapi_qoo_ojb = None
        self._wowma_exc_obj = None

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('s_url', nargs='+')

    # QooAsinDetail に登録されている商品情報に対して価格・在庫の更新をする
    def _chk_ama_stock(self):

        """
        AmaのSP-APIから在庫数・価格を引っ張るにはこれが参考になる
        「ASINコードが同一の商品の在庫一覧情報・商品最安値価格を抽出」
        https://di-acc2.com/system/rpa/15105/#index_id7

        以下を呼べばよい。regionは jp
        def get_products_get_item_offers(self, asin, region):

        """

        self.logger.debug('_chk_ama_stock in.')

        """
        # まずターゲットのasinを引っ張る
        QooAsinDetail の条件は・・・
        ・ブラックリストにない
        ・在庫数は0でも復活してる可能性があるので取ってくる
        is_seller_ok は、更新されてる可能性があるので処理延長で再度チェック。除外条件にしない
        is_blacklist_ok は Trueのみ
        is_blacklist_ok_asin は Trueのみ
        is_blacklist_ok_img は Trueのみ
        is_blacklist_ok_keyword は Trueのみ
        """
        ama_objs = QooAsinDetail.objects.\
            exclude(is_blacklist_ok=False).\
            exclude(is_blacklist_ok_asin=False).\
            exclude(is_blacklist_ok_img=False).\
            exclude(is_blacklist_ok_keyword=False)

        for ama_obj in ama_objs:
            self._chk_ama_stock_from_spapi(ama_obj)
            # wowmaとqoo10側に在庫更新を行う
            self._upd_stock_info(ama_obj)

        self.logger.debug('_chk_ama_stock out.')
        return

    # 渡されるQooAainDetail から対象のasinに対して在庫チェックをかける
    def _chk_ama_stock_from_spapi(self, ama_obj):
        self.logger.debug('_chk_ama_stock_from_spapi in asin:[{}]'.format(
            ama_obj.asin))

        retry_cnt = 5
        for i in range(1, retry_cnt + 1):
            try:
                # SP-API呼び出し
                # get_products_get_item_offers(self, asin, region):
                # もしくはこっちを呼ぶか。すべてチェックして更新かけている
                # spapi_get_catalog_item_for_all
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
                if self._ama_spapi_qoo_ojb.spapi_get_catalog_item_for_all(
                        'jp', ama_obj.asin) is True:
                    # 一通り格納できたら少しwait
                    # self.logger.debug('_chk_ama_stock_from_spapi: spapi_get_catalog_item_for_all ok')
                    time.sleep(1)
                else:
                    # エラー？
                    self.logger.debug('_chk_ama_stock_from_spapi: spapi_get_catalog_item_for_all ng?')
                    time.sleep(3)

            except Exception as e:
                self.logger.debug(traceback.format_exc())
                self.logger.debug('_chk_ama_stock_from_spapi error occurred start retry..')
                sleep(3)
            else:
                break

        self.logger.debug('end of _chk_ama_stock_from_spapi')

        return False

    # wowmaとqoo10に順次アクセスして、商品登録or在庫更新する
    def _upd_stock_info(self, ama_obj):

        self.logger.debug('_upd_stock_info in.')

        # wowmaの在庫更新
        self._upd_wowma_stock_info(ama_obj)

        # qoo10の在庫更新
        # self._upd_qoo10_stock_info(ama_obj)

        self.logger.debug('_upd_stock_info out.')
        return

    # wowmaにアクセスして在庫更新する
    def _upd_wowma_stock_info(self, ama_obj):

        self.logger.debug('_upd_wowma_stock_info in.asin:[{}]'.format(ama_obj.asin))

        # wowma 商品情報も更新
        self.logger.info("-> _upd_wowma_stock_info start set WowmaGoodsDetail")
        wow_obj = WowmaGoodsDetail.objects.filter(
            asin__asin=ama_obj.asin,
        ).first()

        # 既存DBのフラグによってどうステータスを更新するか
        if wow_obj:
            self._wowma_exc_obj.exec_wow_goods_detail_upd(wow_obj)
            wow_obj.save()
        else:
            self.logger.debug('_upd_wowma_stock_info wowma_obj cant find...')
        self.logger.debug('_upd_wowma_stock_info out.')
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
                                    'batch_name': 'ama_stock_chk _upd_qoo10_stock_info point 1',
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
                                'batch_name': 'ama_stock_chk qoo10_items_order_set_goods_price_qty_bulk point 2',
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
                            'batch_name': 'ama_stock_chk qoo10_items_basic_set_new_goods point 3',
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
                            'batch_name': 'ama_stock_chk qoo10_items_basic_edit_goods_status point 4',
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
                                    'batch_name': 'ama_stock_chk qoo10_items_basic_edit_goods_status point 5',
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
                                'batch_name': 'ama_stock_chk qoo10_items_order_set_goods_price_qty_bulk point 6',
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
                    'batch_name': 'ama_stock_chk _upd_qoo10_stock_info point 3',
                    'gid': my_value.gid,
                    'status': 1,
                    'code': 0,
                    'message': "在庫数の取得に失敗？gid:[{}] stock:[{}]".format(my_value.gid, my_value.stock),
                }
                error_goods_log.exe_error_log(my_err_list)
                continue
                # raise Exception("在庫数の取得に失敗？gid:[{0}] stock:[{}]".format(my_value.gid, my_value.stock))

            my_value.save()

        try:
            self.qoo10_access.qoo10_items_order_set_goods_price_qty_bulk(upd_list)
        except:
            # 更新時にエラー？
            self.logger.debug(
                '--> error. qoo10_items_order_set_goods_price_qty_bulk 6 gid:[{}] msg[{}] '.format(
                    my_value.gid, traceback.format_exc()))
            my_err_list = {
                'batch_name': 'ama_stock_chk qoo10_items_order_set_goods_price_qty_bulk point 7',
                'gid': my_value.gid,
                'status': 1,
                'code': 0,
                'message': traceback.format_exc(),
            }
            error_goods_log.exe_error_log(my_err_list)

        self.logger.debug('end of _upd_qoo10_stock_info')

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
                # print("file:" + my_file)
                self.logger.debug('---> start read_csv')
                rtn = self.read_csv(my_file)

                # CSV取り込みできたらwrite
                self.logger.debug('---> start write_csv')
                rtn = self.write_csv()

                # CSVは処理済みに移動
                self.logger.debug('---> start move_csv')
                self.move_csv(my_file)

        except Exception as e:
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            # if f:
            #   f.close()
            return False  # 途中NGなら 0 return で処理済みにしない

        return True

    # 指定されたファイルを処理済みディレクトリに移動する
    def move_csv(self, csvname):
        new_path = shutil.move(
            csvname,
            DONE_CSV_DIR + "{0:%Y%m%d_%H%M%S}".format(datetime.datetime.now()) + "_" + os.path.split(csvname)[1])
        return

    # csvにファイル出力
    def write_csv(self):
        self.logger.debug('write_csv in .')
        # csvはここで用意するか
        csvname = myupdcsv_dir + 'updcsv_' + "{0:%Y%m%d_%H%M%S}".format(datetime.datetime.now()) + '.csv'

        # 以下はヘッダ行のみ
        # with open(csvname, 'w', encoding='shift_jis') as csvfile:
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
        # with open(csvname, 'a') as csvfile:
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
            self.logger.info('ama_stock_chk handle is called')
            self.batch_status = BatchStatusUpd('ama_stock_chk')
            self.batch_status.start()

            # self.common_chrome_driver = CommonChromeDriver(self.logger)

            # self.common_chrome_driver.driverにセット
            # self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            # self.init_chrome_with_tor()

            # 保存してみる
            # if not os.path.exists(mydwsrc_dir):
            #    os.mkdir(mydwsrc_dir)

            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            # self.buinfo_obj = BuyersInfo(self.logger)
            # self.bubrandinfo_obj = BuyersBrandInfo(self.logger)
            self._wowma_exc_obj = ExecWowma(self.logger)
            self._wowma_access = WowmaAccess(self.logger)
            self._ama_spapi_qoo_ojb = AmaSPApiQooAsinDetail(self.logger)

            # Todo: Qoo10開始したら以下も・・
            """
            self.qoo10_access = Qoo10Access(self.logger)
            self.qoo10_access.qoo10_create_cert_key()
            """

            # Ama在庫チェックの母体
            # これは指定した商品カテゴリのリストをチェックするだけ
            self._chk_ama_stock()

            self.logger.info('ama_stock_chk handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.logger.info('exception occurred.')
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        # self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('ama_stock_chk handle end')
        return
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))

