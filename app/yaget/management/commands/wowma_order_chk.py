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
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
from datetime import date,timedelta


sys.path.append('/app/yaget/management/commands')
from yaget.integrations.buyers_info import BuyersInfo, BuyersBrandInfo
from yaget.integrations.wowma_access import WowmaAccess
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.integrations.batch_status import BatchStatusUpd


# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import YaBuyersItemList, YaBuyersItemDetail, WowmaOrderInfo, WowmaOrderDetail


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
        self.logger.debug('wowma_order_chk Command in. init')
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

    # wowmaから注文情報を取り込みDB格納する
    def _exec_wowma_order_chk(self):

        # 受注番号を取得。とれただけループして確認する
        # 条件はどうするか・・・ パラメータは以下
        # [新規受付]と、[発送待ち]　だけでいいか。
        # 期間は、2週間前くらい？ から今日まで。
        """
        新規受付
        発送前入金待ち
        発送後入金待ち
        与信待ち
        発送待ち
        完了
        保留
        キャンセル
        各種カスタムステータス（取引管理で貴店舗が登録したステータス名）
        新規予約
        予約中
        不正取引審査中
        審査保留
        審査NG
        キャンセル受付中
        """

        # パラメータ設定
        end_date = datetime.date.today()
        # 基準日の2週間前を算出
        start_date = end_date + timedelta(weeks=-2)
        date_type = 0 # 0:注文日　1:発送日　2:入金日　3:発売(入荷)予定日　4:発送期限日　（デフォルト0）
        order_status_1 = "新規受付"
        order_status_2 = "発送待ち"

        document = self.wowma_access.wowma_get_order_list(
            start_date, end_date, date_type, order_status_1, order_status_2)

        if document:
            #self.logger.info('document:[' + document.toString() + ']')
            myrtn = document.getElementsByTagName("status")[0].firstChild.nodeValue # 0なら成功、1　失敗
            if myrtn == 1:
                self.logger.info('wowma_get_order_list error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_get_order_list code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_get_order_list message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
            else:
                # 正常にデータ取得できた。DB登録かな
                self.logger.info('wowma_get_order_list ok total_cnt:[' \
                                 + str(document.getElementsByTagName("resultCount")[0].firstChild.nodeValue) + ']')

                # 注文詳細をそれぞれ取り込む
                orderInfo = document.getElementsByTagName("orderInfo")[0]
                for order_id_elm in orderInfo.getElementsByTagName("orderId"):
                    self._get_wowma_order_detail(order_id_elm.firstChild.nodeValue)

        return

    def _chk_node_exists(self, document, node_str, rtn_flg):
        my_node = document.getElementsByTagName(node_str)
        if len(my_node) > 0:
            if my_node[0].firstChild:
                my_rtn = my_node[0].firstChild.nodeValue
            else:
                my_rtn = ""
        else:
            my_rtn = ""

        if rtn_flg == 1: # 1が指定されたら None (DateTime)を返す
            if my_rtn == "":
                my_rtn = None
            else:
                my_rtn = str(my_rtn).replace('/', '-') # 日付の区切り修正
        if rtn_flg == 2: # 2が指定されたら 0 (Integer)を返す
            if my_rtn == "":
                my_rtn = 0
        return my_rtn

    # wowmaから注文情報の詳細を取り込みDB格納する
    def _get_wowma_order_detail(self, order_id):

        self.logger.info('--> wowma_get_order_detail in.order_id:[' + str(order_id) + ']')

        # 受注詳細を取得。受注番号を渡す必要がある
        document_detail = self.wowma_access.wowma_get_order_detail(order_id)
        if document_detail:
            self.logger.info('--> wowma_get_order_detail 取得OK')
            myrtn_detail = document_detail.getElementsByTagName("status")[0].firstChild.nodeValue # 0なら成功、1　失敗
            if myrtn_detail == 1:
                self.logger.info('wowma_get_order_detail error occurred itemcd:[' \
                                 + str(document_detail.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_get_order_detail code:[' \
                                 + str(document_detail.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_get_order_detail message:[' \
                                 + str(document_detail.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
            else:
                # 正常にデータ取得できた。DB登録かな
                # DBに保存
                self.logger.info('wowma_get_order_detail start save WowmaOrderInfo')

                obj, created = WowmaOrderInfo.objects.update_or_create(
                    orderid=str(document_detail.getElementsByTagName("orderId")[0].firstChild.nodeValue),
                    site_and_device=str(document_detail.getElementsByTagName("siteAndDevice")[0].firstChild.nodeValue),
                    mail_address=str(document_detail.getElementsByTagName("mailAddress")[0].firstChild.nodeValue),
                    order_name=str(document_detail.getElementsByTagName("ordererName")[0].firstChild.nodeValue),
                    order_kana=str(document_detail.getElementsByTagName("ordererKana")[0].firstChild.nodeValue),
                    order_zipcode=str(document_detail.getElementsByTagName("ordererZipCode")[0].firstChild.nodeValue),
                    order_address=str(document_detail.getElementsByTagName("ordererAddress")[0].firstChild.nodeValue),
                    order_phone_number_1=str(
                        document_detail.getElementsByTagName("ordererPhoneNumber1")[0].firstChild.nodeValue),
                    order_phone_number_2=self._chk_node_exists(document_detail, "ordererPhoneNumber2", 0),
                    nickname=self._chk_node_exists(document_detail, "nickname", 0),
                    sender_name=str(document_detail.getElementsByTagName("senderName")[0].firstChild.nodeValue),
                    sender_kana=str(document_detail.getElementsByTagName("senderKana")[0].firstChild.nodeValue),
                    sender_zipcode=str(document_detail.getElementsByTagName("senderZipCode")[0].firstChild.nodeValue),
                    sender_address=str(document_detail.getElementsByTagName("senderAddress")[0].firstChild.nodeValue),
                    sender_phone_number_1=str(
                        document_detail.getElementsByTagName("senderPhoneNumber1")[0].firstChild.nodeValue),
                    sender_phone_number_2=self._chk_node_exists(document_detail, "senderPhoneNumber2", 0),
                    order_option=self._chk_node_exists(document_detail, "orderOption", 0),
                    settlement_name=str(document_detail.getElementsByTagName("settlementName")[0].firstChild.nodeValue),
                    user_comment=self._chk_node_exists(document_detail, "userComment", 0),
                    memo=self._chk_node_exists(document_detail, "memo", 0),
                    order_status=str(document_detail.getElementsByTagName("orderStatus")[0].firstChild.nodeValue),
                    contact_status=str(document_detail.getElementsByTagName("contactStatus")[0].firstChild.nodeValue),
                    authorization_status=str(
                        document_detail.getElementsByTagName("authorizationStatus")[0].firstChild.nodeValue),
                    payment_status=str(document_detail.getElementsByTagName("paymentStatus")[0].firstChild.nodeValue),
                    ship_status=str(document_detail.getElementsByTagName("shipStatus")[0].firstChild.nodeValue),
                    print_status=str(document_detail.getElementsByTagName("printStatus")[0].firstChild.nodeValue),
                    cancel_status=str(document_detail.getElementsByTagName("cancelStatus")[0].firstChild.nodeValue),
                    total_sale_price=str(
                        document_detail.getElementsByTagName("totalSalePrice")[0].firstChild.nodeValue),
                    total_sale_unit=str(document_detail.getElementsByTagName("totalSaleUnit")[0].firstChild.nodeValue),
                    postage_price=str(document_detail.getElementsByTagName("postagePrice")[0].firstChild.nodeValue),
                    charge_price=str(document_detail.getElementsByTagName("chargePrice")[0].firstChild.nodeValue),
                    total_price=str(document_detail.getElementsByTagName("totalPrice")[0].firstChild.nodeValue),
                    coupon_total_price=self._chk_node_exists(document_detail, "couponTotalPrice", 2),
                    use_point=self._chk_node_exists(document_detail, "usePoint", 2),
                    use_point_cancel=self._chk_node_exists(document_detail, "usePointCancel", 0),
                    use_au_point_price=self._chk_node_exists(document_detail, "useAuPointPrice", 2),
                    use_au_point=self._chk_node_exists(document_detail, "useAuPoint", 2),
                    use_au_point_cancel=self._chk_node_exists(document_detail, "useAuPointCancel", 0),
                    point_fixed_status=self._chk_node_exists(document_detail, "pointFixedStatus", 0),
                    settle_status=self._chk_node_exists(document_detail, "settleStatus", 0),
                    pg_result=self._chk_node_exists(document_detail, "pgResult", 2),
                    pg_orderid=self._chk_node_exists(document_detail, "pgOrderId", 2),
                    pg_request_price=self._chk_node_exists(document_detail, "pgRequestPrice", 2),
                    coupon_type=self._chk_node_exists(document_detail, "couponType", 0),
                    coupon_key=self._chk_node_exists(document_detail, "couponKey", 0),
                    card_jagdement=self._chk_node_exists(document_detail, "cardJadgement", 2),
                    delivery_name=self._chk_node_exists(document_detail, "deliveryName", 0),
                    delivery_method_id=self._chk_node_exists(document_detail, "deliveryMethodId", 0),
                    delivery_request_time=self._chk_node_exists(document_detail, "deliveryRequestTime", 0),
                    shipping_carrier=self._chk_node_exists(document_detail, "shippingCarrier", 2),
                    shipping_number=self._chk_node_exists(document_detail, "shippingNumber", 0),
                    order_date=self._chk_node_exists(document_detail, "orderDate", 1),
                    contact_date=self._chk_node_exists(document_detail, "contactDate", 1),
                    authorization_date=self._chk_node_exists(document_detail, "authorizationDate", 1),
                    payment_date=self._chk_node_exists(document_detail, "paymentDate", 1),
                    ship_date=self._chk_node_exists(document_detail, "shipDate", 1),
                    cancel_date=self._chk_node_exists(document_detail, "cancelDate", 1),
                    print_date=self._chk_node_exists(document_detail, "printDate", 1),
                    point_fixed_date=self._chk_node_exists(document_detail, "pointFixedDate", 1),
                    delivery_request_day=self._chk_node_exists(document_detail, "deliveryRequestDay", 1),
                    shipping_date=self._chk_node_exists(document_detail, "shippingDate", 1),
                )
                obj.save()
                self.logger.info('wowma_get_order_detail end of save WowmaOrderInfo')

                # 続いて明細の格納
                self.logger.info('wowma_get_order_detail start save WowmaOrderDetail')
                mydom_details = document_detail.getElementsByTagName("detail")
                for mydom_detail in mydom_details:

                    # item_name は取り直して格納
                    item_code = self._chk_node_exists(document_detail, "itemCode", 0)
                    item = YaBuyersItemDetail.objects.filter(
                        gid=item_code,
                    ).first()
                    my_item_name = item.wow_gname

                    obj_detail, detail_created = WowmaOrderDetail.objects.update_or_create(
                        order_detail_id=str(mydom_detail.getElementsByTagName("orderDetailId")[0].firstChild.nodeValue),
                        orderinfo=WowmaOrderInfo(orderid=order_id),
                        item_management_id=self._chk_node_exists(document_detail, "itemManagementId", 0),
                        item_code=self._chk_node_exists(document_detail, "itemCode", 0),
                        lot_number=self._chk_node_exists(document_detail, "lotnumber", 0),
                        #item_name=self._chk_node_exists(document_detail, "itemName", 0),
                        item_name=my_item_name,
                        item_option=self._chk_node_exists(document_detail, "itemOption", 0),
                        item_cancel_status=self._chk_node_exists(document_detail, "itemCancelStatus", 0),
                        before_discount=self._chk_node_exists(document_detail, "beforeDiscount", 1),
                        discount=self._chk_node_exists(document_detail, "discount", 1),
                        item_price=self._chk_node_exists(document_detail, "itemPrice", 1),
                        unit=self._chk_node_exists(document_detail, "unit", 1),
                        total_item_price=self._chk_node_exists(document_detail, "totalItemPrice", 1),
                        tax_type=self._chk_node_exists(document_detail, "taxType", 0),
                        gift_point=self._chk_node_exists(document_detail, "giftPoint", 1),
                    )
                    if detail_created:  # updateだった
                        obj_detail.item_name = my_item_name
                        obj_detail.orderinfo = WowmaOrderInfo(orderid=order_id)
                    obj_detail.save()
                self.logger.info('wowma_get_order_detail end of save WowmaOrderDetail')

        else:
            self.logger.info('_exec_wowma_order_chk error occurred. wowma_get_order_detail retured false')

        self.logger.info('wowma_get_order_detail end.')
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
            self.logger.info('wowma_order_chk handle is called')
            self.batch_status = BatchStatusUpd('wowma_order_chk')
            self.batch_status.start()

            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            self.buinfo_obj = BuyersInfo(self.logger)
            self.bubrandinfo_obj = BuyersBrandInfo(self.logger)
            self.wowma_access = WowmaAccess(self.logger)

            # 受注チェックの母体
            self._exec_wowma_order_chk()

            self.logger.info('wowma_order_chk handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        #self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('wowma_order_chk handle end')
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))
        return
