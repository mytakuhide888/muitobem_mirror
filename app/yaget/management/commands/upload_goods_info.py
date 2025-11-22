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
import yaget.integrations.error_goods_log


#from yaget.AmaMws import AmaMwsProducts

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/upload_goods_info.config", disable_existing_loggers=False)

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
    #def add_arguments(self, parser):
    #    parser.add_argument('s_url', nargs='+')

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

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

    # csv の格納ディレクトリから１ファイルずつ読み込む
    def _read_csv_dir(self):
        self.logger.debug('read_csv_dir start.')
        try:
            # 指定のディレクトリ配下を読み込む
            # csv 読み込み
            #file_list = glob.glob(UPLOAD_DIR + "*")
            file_list = glob.glob(myupdcsv_dir + "*")

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
            #self.logger.info(traceback.format_exc())
            #traceback.print_exc()
            #if f:
            #   f.close()
            #return False  # 途中NGなら 0 return で処理済みにしない
            raise

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

            # 読み込んだcsvが、縮小版（ファイル名 s始まり）かそうじゃないか
            self.logger.info('read_row csvname:[{}]'.format(csvname))
            s_flg = 0
            if os.path.basename(csvname)[0] == 's':
                s_flg = 1

            self.logger.debug('read_row start. 行の列項目をチェック ')
            for cnt, row in enumerate(reader):
                self.logger.debug('read_row start. [{}]'.format(row))
                self.logger.debug('read_row cnt. {}'.format(cnt))
                if cnt == 0:  # 先頭行のチェック
                    self.logger.debug('---> read_csv in cnt =0')
                    # 行頭の列数をチェック
                    if s_flg == 0:  # 通常のフル項目版 列数：32
                        if len(row) != 32:
                            raise Exception("CSVのフォーマットが不正です。(通常版) 列項目が足りません。len[{}]".format(len(row)))
                    else:  # 縮小版　列数：15
                        if len(row) != 15:
                            raise Exception("CSVのフォーマットが不正です。(縮小版) 列項目が足りません。len[{}]".format(len(row)))
                else:
                    # ここからCSVの行ごとに内容をチェック。DB更新から、wowma、qoo10も１商品ずつアップしてしまう
                    if s_flg == 0:  # 通常のフル項目版 列数：30
                        self._upd_csv_row_normal(row)
                    else:  # 縮小版　列数：15
                        self._upd_csv_row_small(row)

        except Exception as e:
            #self.logger.info(traceback.format_exc())
            #traceback.print_exc()
            if f:
                f.close()
            #return False  # 途中NGなら 0 return で処理済みにしない
            raise

        # Exceptionが飛んでなかったら正常に処理終了
        if f:
            f.close()
        self.logger.debug('---> _read_csv ok, next csv')
        return

    # 通常のCSVをDB登録、wowma, qoo10アップロード
    def _upd_csv_row_normal(self, row):
        self.logger.debug('_upd_csv_row_normal in,')

        # ブラックリストの商品に該当してたら処理はしない
        black_list_obj = YaBuyersItemDetail.objects.filter(gid=row[0].strip()).filter(black_list__isnull=False).first()
        if black_list_obj:
            self.logger.debug('_upd_csv_row_normal ブラックリストに該当したので処理しない gid:[{}]'.format(row[0].strip()))
            return

        # DBに保存
        #if YaBuyersItemDetail.objects.filter(gid=row[0]).exists():
        myobj = YaBuyersItemDetail.objects.filter(gid=row[0].strip()).first()
        if myobj:
            self.logger.info('start save YaBuyersItemDetail add.')
            """
            obj, created = YaBuyersItemDetail.objects.update_or_create(
                gid=row[0].strip(),
                glink=row[1],
                gname=row[2],
                gdetail=row[3],
                gnormalprice=row[4],
                gspprice=row[5],
                gcode=row[6],
                stock=row[7],
                wow_upd_status=row[8],
                wow_on_flg=row[9],
                wow_gname=row[10],
                wow_gdetail=row[11],
                wow_worn_key=row[12],
                wow_price=row[13],
                wow_fixed_price=row[14],
                wow_postage_segment=row[15],
                wow_postage=row[16],
                wow_delivery_method_id=row[17],
                wow_ctid=row[18],
                qoo_upd_status=row[19],
                qoo_on_flg=row[20],
                qoo_seller_code=row[21],
                qoo_gdno=row[22],
                qoo_gname=row[23],
                qoo_gdetail=row[24],
                qoo_worn_key=row[25],
                qoo_price=row[26],
                qoo_fixed_price=row[27],
                qoo_shipping_no=row[28],
                qoo_postage=row[29],
                qoo_delivery_method_id=row[30],
                qoo_ctid=row[31],
            )
            """
            myobj.glink = row[1]
            myobj.gname = row[2]
            myobj.gdetail = row[3]
            myobj.gnormalprice = int(row[4])
            myobj.gspprice = int(row[5])
            myobj.gcode = row[6]
            myobj.stock = int(row[7])
            myobj.wow_upd_status = int(row[8])
            myobj.wow_on_flg = int(row[9])
            myobj.wow_gname = row[10]
            myobj.wow_gdetail = row[11]
            myobj.wow_worn_key = row[12]
            myobj.wow_price = int(row[13])
            myobj.wow_fixed_price = int(row[14])
            myobj.wow_postage_segment = int(row[15])
            myobj.wow_postage = int(row[16])
            myobj.wow_delivery_method_id = int(row[17])
            myobj.wow_ctid = int(row[18])
            myobj.qoo_upd_status = int(row[19])
            myobj.qoo_on_flg = int(row[20])
            myobj.qoo_seller_code = row[21]
            myobj.qoo_gdno = row[22]
            myobj.qoo_gname = row[23]
            myobj.qoo_gdetail = row[24]
            myobj.qoo_worn_key = row[25]
            myobj.qoo_price = int(row[26])
            myobj.qoo_fixed_price = int(row[27])
            myobj.qoo_shipping_no = int(row[28])
            myobj.qoo_postage = int(row[29])
            myobj.qoo_delivery_method_id = int(row[30])
            myobj.qoo_ctid = int(row[31])
            myobj.save()
        else:
            # CSVで未登録のデータが指定されたら処理中断しよう
            raise Exception("_upd_csv_row_normal 未登録のgidが指定されました。gid[{}]".format(row[0]))

        # wowmq, qoo10のデータ更新
        self._upd_wowma_qoo_item_info_normal(row[0])

        self.logger.debug('_upd_csv_row_normal out,')
        return

    # 縮小版のCSVをDB登録、wowma, qoo10アップロード
    def _upd_csv_row_small(self, row):
        self.logger.debug('_upd_csv_row_small in,')

        # ブラックリストの商品に該当してたら処理はしない
        black_list_obj = YaBuyersItemDetail.objects.filter(gid=row[0].strip()).filter(black_list__isnull=False).first()
        if black_list_obj:
            self.logger.debug('_upd_csv_row_small ブラックリストに該当したので処理しない gid:[{}]'.format(row[0].strip()))
            return

        # DBに保存
        #if YaBuyersItemDetail.objects.filter(gid=row[0]).exists():
        myobj = YaBuyersItemDetail.objects.filter(gid=row[0].strip()).first()
        if myobj:
            self.logger.info('start save YaBuyersItemDetail add.')
            """
            obj, created = YaBuyersItemDetail.objects.update_or_create(
                gid=row[0].strip(),
                gname=row[1],
                gdetail=row[2],
                gnormalprice=row[3],
                stock=row[4],
                wow_upd_status=row[5],
                wow_on_flg=row[6],
                wow_gname=row[7],
                wow_gdetail=row[8],
                wow_worn_key=row[9],
                qoo_upd_status=row[10],
                qoo_on_flg=row[11],
                qoo_gname=row[12],
                qoo_gdetail=row[13],
                qoo_worn_key=row[14],
            )
            """
            myobj.gname = row[1]
            myobj.gdetail = row[2]
            myobj.gnormalprice = int(row[3])
            myobj.stock = int(row[4])
            myobj.wow_upd_status = int(row[5])
            myobj.wow_on_flg = int(row[6])
            myobj.wow_gname = row[7]
            myobj.wow_gdetail = row[8]
            myobj.wow_worn_key = row[9]
            myobj.qoo_upd_status = int(row[10])
            myobj.qoo_on_flg = int(row[11])
            myobj.qoo_gname = row[12]
            myobj.qoo_gdetail = row[13]
            myobj.qoo_worn_key = row[14]
            myobj.save()
        else:
            # CSVで未登録のデータが指定されたら処理中断しよう
            raise Exception("_upd_csv_row_small 未登録のgidが指定されました。gid[{}]".format(row[0]))

        # wowmq, qoo10のデータ更新
        self._upd_wowma_qoo_item_info_normal(row[0])

        self.logger.debug('_upd_csv_row_small out,')
        return

    # ノーマルデータをwowma,qoo10ともに更新
    # return は何も返してなかったが、正常更新か、エラーかくらいは判定できるようにしよう。
    def _upd_wowma_qoo_item_info_normal(self, gid):

        self.logger.info('_upd_wowma_qoo_item_info_normal in.gid:[{}]'.format(gid))
        myrtn = 0
        mycode = ''
        mymsg = ''
        myobj = YaBuyersItemDetail.objects.filter(gid=gid).first()
        if not myobj:
            # データがなければ飛ばす
            self.logger.info('_upd_wowma_qoo_item_info_normal 該当のレコードなし gid:[{}]'.format(gid))
            return
            #raise Exception("_upd_wowma_qoo_item_info_normal 未登録のgidが指定されました。gid[{}]".format(gid))

        # カテゴリIDが入ってないことがあるのでURLから取得したい
        if myobj.bu_ctid == '':
            myobj.bu_ctid = self.buinfo_obj.get_buyers_ctcd_from_url(myobj.glink)

        # カテゴリIDの最新化、キーワードの設定はここでやり直したい
        tmpyct_flg = 0
        tmpyct_qoo_flg = 0
        myobj.wow_ctid, tmpyct_flg, myobj.qoo_ctid, tmpyct_qoo_flg = self.buinfo_obj.get_wow_qoo_ctcd(
            myobj.bu_ctid,  # バイヤーズのカテゴリCD
            myobj.gname,
            myobj.wow_gdetail,
            myobj.qoo_gdetail)

        self.logger.info(
            '_upd_wowma_qoo_item_info_normal カテゴリIDとれたかな wow_ctid:[{}] qoo_ctid:[{}]'.format(
                myobj.wow_ctid, myobj.qoo_ctid))

        # 検索キーワードをそれぞれ設定
        myobj.qoo_keyword = self.buinfo_obj.set_qoo_keyword(myobj.bu_ctid, myobj.gname, myobj.qoo_ctid)
        myobj.wow_keyword = self.buinfo_obj.set_wow_keyword(myobj.bu_ctid, myobj.gname, myobj.wow_ctid)

        # wowmaのtagidは、このタイミングで最新化しておく
        # wowma は検索タグIDを設定。
        myobj.wow_tagid = self.buinfo_obj.get_wow_tagid_list(myobj.bu_ctid, myobj.wow_gname, myobj.wow_ctid)
        myobj.save()

        # 既存DBのフラグによってどうステータスを更新するか
        # wowma新規登録用の画像情報を作らないといけない。
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

        # wowma 更新 ###################################################################################################
        # wowmaについて画面から出品OKになっている。以下で掲載状況を確認して更新してゆく もしくは　wow_on_flg == 3（在庫切れ）
        if myobj.wow_on_flg == 1 or myobj.wow_on_flg == 3:

            # 出品OKなのに在庫０なら、そのまま未掲載にしておく
            if int(myobj.stock) == 0:
                if myobj.wow_upd_status == 0 or myobj.wow_upd_status == 2:  # wowma未掲載
                    # 未掲載 wow_upd_status = 0（未登録）もしくは2（登録済みだが未掲載）
                    # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                    self.logger.info('--> _upd_wowma_qoo_item_info_normal 出品OKなのに在庫０　未掲載のまま gid:[{}]'.format(gid))
                    myobj.wow_on_flg = 3
                else:
                    # 掲載中 wow_upd_status = 1
                    # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない、かつ登録済みだが未掲載に切り替える
                    try:
                        self.wowma_access.wowma_update_stock(myobj.gid, 0, '2')
                        myobj.wow_on_flg = 3  # 更新成功したら 在庫切れにする。出品OK状態はそのまま、wow掲載状況は掲載中止になってる
                        myobj.wow_upd_status = 2  # 未掲載に
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 在庫切れにした。gid:[{}]'.format(gid))
                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'upload_goods_info _upd_wowma_qoo_item_info_normal',
                            'gid': gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        self.logger.debug(
                            '--> _upd_wowma_stock_info 在庫数更新時にエラー？ gid:[{}] 在庫は0'.format(gid))
                        return  # DB更新せずに戻す
                        #raise Exception("在庫を0更新時に失敗？ gid:[{0}] stock:[{1}]".format(my_value.gid, my_value.stock))

                if myobj.wow_upd_status != 0:
                    # 登録済みだったら、在庫状況によらず商品内容をupdateする
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
                            2,  # 1は販売中。2は販売終了。出品OKだが在庫切れなので登録済みだが未掲載 ( 2 ) にしておく
                            int(myobj.stock),  # 在庫数
                            images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                        )
                        for ret_obj in ret_obj_list:
                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                # lotnumberを更新しておく
                                self.buinfo_obj.set_wow_lotnum(myobj.gid, ret_obj['res_code'])

                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                        # 在庫0更新
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 更新OK！ 在庫は0')
                        myobj.wow_on_flg = 3  # OKのまま
                        myobj.wow_upd_status = 2  # 登録済みだが未掲載に

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'upload_goods_info _upd_wowma_qoo_item_info_normal point 1_3',
                            'gid': myobj.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

            # 　在庫がある
            elif int(myobj.stock) > 0:
                # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                if myobj.wow_upd_status == 0:  # 未登録なら新規登録する
                    self.logger.info('--> _upd_wowma_qoo_item_info_normal 未登録だが出品OKで在庫あるので登録開始')
                    # 未掲載 wow_upd_status = 0
                    ret_obj_list = self.wowma_access.wowma_register_item_info(
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

                    myrtn = 0
                    mycode = ''
                    mymsg = ''
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
                                    '--> _upd_wowma_qoo_item_info_normal 更新OK！ 1_1 在庫[{}]'.format(myobj.stock))
                                myobj.wow_on_flg = 1  # OKのまま
                                myobj.wow_upd_status = 1  # 掲載中に

                            except:
                                # 更新時にエラー？
                                my_err_list = {
                                    'batch_name': 'upload_goods_info _upd_wowma_qoo_item_info_normal point 1_1',
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
                                "upload_goods_info _upd_wowma_qoo_item_info_normal wowma 商品検索でエラー [{}][{}]".format(ret_obj['res_code'],
                                                                                         ret_obj['res_msg']))
                            chk_flg = 1  # なにかエラーになってた

                        elif ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                            self.logger.debug(
                                "upload_goods_info _upd_wowma_qoo_item_info_normal 商品登録できた [{}][{}]".format(ret_obj['res_code'],
                                                                                        ret_obj['res_msg']))
                            # lotnumberを更新しておく
                            self.buinfo_obj.set_wow_lotnum(myobj.gid, ret_obj['res_code'])

                    if chk_flg == 0:
                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                        # 出品失敗なら 1 が返される。この場合は未出品のまま
                        self.logger.debug('--> _upd_wowma_qoo_item_info_normal 登録OK！ 1')
                        myobj.wow_on_flg = 1  # OK
                        myobj.wow_upd_status = 1  # 掲載中に更新
                    else:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'upload_goods_info _upd_wowma_qoo_item_info_normal point 2_1',
                            'gid': myobj.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        # エラー記録だけ残して処理は続行しておく
                        error_goods_log.exe_error_log(my_err_list)

                else:
                    # 掲載中 wow_upd_status = 1　か、登録済みだが未掲載 2 （これまで在庫０だった）
                    # 現在の在庫数で更新する、未掲載だったら復活させる
                    self.logger.info('--> _upd_wowma_qoo_item_info_normal 掲載中。現時点の在庫数で更新 gid[{}] stock[{}]'.format(
                        myobj.gid,
                        myobj.stock)
                    )
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
                            '--> _upd_wowma_qoo_item_info_normal 更新OK！ 1 在庫[{}]'.format(myobj.stock))

                        ret_obj = YaBuyersItemDetail.objects.filter(gid=gid).first()
                        if ret_obj:
                            self.logger.info('===> set_wow_lotnum seved after. :lotnum:[{}]'.format(ret_obj.wow_lotnum))

                        myobj.wow_on_flg = 1  # OKのまま
                        myobj.wow_upd_status = 1  # 掲載中に

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'upload_goods_info _upd_wowma_qoo_item_info_normal point 1',
                            'gid': myobj.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

            else:  # 在庫数の取得エラー？
                raise Exception("在庫数の取得に失敗？stock:[{}] gid:[{}]".format(myobj.stock, myobj.gid))

        else:
            # ここにきたら、wow_on_flg は 0（確認中）か2（NG）のはず。そのままにしておく
            if myobj.wow_on_flg == 2:
                self.logger.info('--> _upd_wowma_qoo_item_info_normal 未出品に更新しないと flg=2 （NG）')
                if myobj.wow_upd_status != 0:  # 登録済みのものは未掲載に倒さないと
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
                            2,  # 1は販売中。2は販売終了。出品NGなので販売終了 ( 2 ) にしておく
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
                            '--> _upd_wowma_qoo_item_info_normal 更新OK！ 1 在庫[{}]'.format(myobj.stock))
                        myobj.wow_on_flg = 1  # OKのまま
                        myobj.wow_upd_status = 1  # 掲載中に

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'upload_goods_info _upd_wowma_qoo_item_info_normal point 1_1',
                            'gid': myobj.gid,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

            else:
                self.logger.info('--> _upd_wowma_qoo_item_info_normal 在庫あるがNGフラグたってて未出品なので処理せず flg=0 ')

        # qoo10 更新 ###################################################################################################
        #     qoo_upd_status = ((1, '取引待機'), (2, '取引可能'), (3, '取引廃止'))
        #     qoo_on_flg = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
        # qooについて画面から1(出品OK)もしくは3（在庫切れ）になっている対象は、以下で掲載状況を確認して更新してゆく
        if myobj.qoo_on_flg == 1 or myobj.qoo_on_flg == 3:

            # 出品OKなのに在庫０なら、そのまま未掲載にしておく
            if int(myobj.stock) == 0:
                if myobj.qoo_upd_status == 1 or myobj.qoo_upd_status == 3:  # qoo未掲載
                    # 未掲載 qoo_upd_status = 1（取引待機）もしくは3（登録済みだが取引廃止）
                    # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                    self.logger.info('--> _upd_wowma_qoo_item_info_normal 出品OKなのに在庫０　未掲載のまま')
                    myobj.qoo_on_flg = 3
                else:
                    # 掲載中 qoo_upd_status = 2 取引可能
                    # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない、かつ登録済みだが未掲載に切り替える
                    myobj.qoo_on_flg = 3  # 更新成功したら 在庫切れにする。出品OK状態はそのまま、qoo掲載状況は取引待機になってる
                    myobj.qoo_upd_status = 1  # 取引待機に
                    # 商品更新のセットを投げる
                    try:
                        self.qoo10_access.qoo10_my_set_update_goods(myobj)
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 在庫切れにした。')
                    except Exception as e:
                        self.logger.info(traceback.format_exc())
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                        my_err_list = {
                            'batch_name': 'upload_goods_info qoo10_my_set_update_goods',
                            'gid': gid,
                            'status': 1,
                            'code': '',
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す

            # 　在庫がある
            elif int(myobj.stock) > 0:
                # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                if myobj.qoo_upd_status == 1:  # 取引待機（1）は未登録か、登録済みだが在庫0で更新された場合も。
                    if myobj.qoo_gdno:  # 商品登録済み
                        # 商品更新のセットを投げる
                        myobj.qoo_on_flg = 1  # OKに。
                        myobj.qoo_upd_status = 2  # 掲載中に更新
                        try:
                            self.qoo10_access.qoo10_my_set_update_goods(myobj)
                            self.logger.info('--> _upd_wowma_qoo_item_info_normal 出品OKで在庫あるので掲載中に更新！ 1')
                        except Exception as e:
                            self.logger.info(traceback.format_exc())
                            self.logger.info('--> _upd_wowma_qoo_item_info_normal 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                            my_err_list = {
                                'batch_name': 'upload_goods_info qoo10_my_set_update_goods',
                                'gid': gid,
                                'status': 1,
                                'code': '',
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            return  # DB更新せずに戻す
                    else:
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 未登録だが出品OKで在庫あるので登録開始')
                        # 未掲載 qoo_upd_status = 0 なら新規登録する
                        myobj.qoo_on_flg = 1  # OKに。
                        myobj.qoo_upd_status = 2  # 掲載中に更新

                        # 商品登録のセットを投げる
                        try:
                            self.qoo10_access.qoo10_my_set_new_goods(myobj)
                            self.logger.info('--> _upd_wowma_qoo_item_info_normal 在庫あり、未登録だったので新規登録OK！')
                        except Exception as e:
                            self.logger.info(traceback.format_exc())
                            self.logger.info('--> _upd_wowma_qoo_item_info_normal 新規登録中にエラーになったがそのまま続行する。後で要確認')
                            my_err_list = {
                                'batch_name': 'upload_goods_info qoo10_my_set_new_goods',
                                'gid': gid,
                                'status': 1,
                                'code': '',
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            return  # DB更新せずに戻す
                else:
                    # 掲載中 qoo_upd_status = 2　か、登録済みだが未掲載 3 （これまで在庫０だった）
                    # 現在の在庫数で更新する、未掲載だったら復活させる
                    myobj.qoo_on_flg = 1  # 更新成功した。
                    myobj.qoo_upd_status = 2  # 掲載中に更新

                    # 商品更新のセットを投げる
                    try:
                        self.qoo10_access.qoo10_my_set_update_goods(myobj)
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 出品OKで在庫あるので掲載中に更新！')
                    except Exception as e:
                        self.logger.info(traceback.format_exc())
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                        my_err_list = {
                            'batch_name': 'upload_goods_info qoo10_my_set_update_goods',
                            'gid': gid,
                            'status': 1,
                            'code': '',
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す

                """
                if myobj.qoo_upd_status != 0:
                    # 登録済みだったら、在庫状況によらず商品内容をupdateする
                    myobj.qoo_on_flg = 1  # OKのまま
                    myobj.qoo_upd_status = 1  # 掲載中に
                    # 商品更新のセットを投げる
                    self.qoo10_access.qoo10_my_set_update_goods(myobj)
                """
            else:  # 在庫数の取得エラー？
                raise Exception("在庫数の取得に失敗？stock:[{}] gid:[{}]".format(myobj.stock, gid))

        else:
            # ここにきたら、qoo_on_flg は 0（確認中）か2（NG）のはず。
            if myobj.qoo_on_flg == 2:
                self.logger.info('--> _upd_wowma_qoo_item_info_normal qoo 未出品に更新しないと flg=2 （NG）')
                if myobj.qoo_upd_status != 1:  # 登録済みのものは未掲載に倒さないと
                    myobj.qoo_on_flg = 2  # NGのまま。
                    myobj.qoo_upd_status = 1  # 取引待機に

                    # 商品更新のセットを投げる
                    try:
                        self.qoo10_access.qoo10_my_set_update_goods(myobj)
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal qoo 出品OKで在庫あるので掲載中に更新！')
                    except Exception as e:
                        self.logger.info(traceback.format_exc())
                        self.logger.info('--> _upd_wowma_qoo_item_info_normal 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                        my_err_list = {
                            'batch_name': 'upload_goods_info qoo10_my_set_update_goods',
                            'gid': gid,
                            'status': 1,
                            'code': '',
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す

                else:
                    # 更新時にエラー？
                    self.logger.info('--> _upd_wowma_qoo_item_info_normal qoo 未出品に更新しないと flg=2 （NG）qoo_upd_status:[{}]'.format(myobj.qoo_upd_status))
                    """
                    raise Exception("qoo 出品NGで在庫あったのでNGにする更新中に失敗？ gid:[{0}] stock:[{1}]".format(
                        myobj.gid, myobj.stock))
                    """
                    # 2021/11/16 ひとまず初期登録中なのでエラーになってもそのまま進んでしまう。後で直すこと！
                    return
            else:
                self.logger.info('--> _upd_wowma_qoo_item_info_normal qoo 在庫あるがNGフラグたってて未出品なので処理せず flg=0 ')

        myobj.save()

        return

        # =====================================================================
        # 指定されたディレクトリにアップされたバイヤーズ用の商品詳細CSVを読み込んで
        # 順次DBを更新。かつwowmaとqoo10にアップロードする。
        # CSVは全項目版と、商品詳細の項目に絞った２フォーマットがあるのでそれぞれに対応しよう
        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('upload_goods_info handle is called')
            self.batch_status = BatchStatusUpd('upload_goods_info')
            self.batch_status.start()

            self.common_chrome_driver = CommonChromeDriver(self.logger)

            # self.common_chrome_driver.driverにセット
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
            # self.init_chrome_with_tor()

            self.logger.debug('upload_goods_info handle start get')

            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            self.buinfo_obj = BuyersInfo(self.logger)
            self.bubrandinfo_obj = BuyersBrandInfo(self.logger)
            self.wowma_access = WowmaAccess(self.logger)
            self.qoo10_access = Qoo10Access(self.logger)

            self.qoo10_access.qoo10_create_cert_key()

            # バイヤーズにログインしておく
            self.buinfo_obj.login_buyers()

            # アップロードされたディレクトリを探索して格納済みのCSVを全部処理
            self._read_csv_dir()

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
        self.logger.info('upload_goods_info handle end')
        return
