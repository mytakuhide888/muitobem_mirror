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
from yaget.integrations.logispi_info import LogispiInfo
from yaget.integrations.wowma_access import WowmaAccess
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.integrations.batch_status import BatchStatusUpd


# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import YaBuyersItemDetail, WowmaOrderInfo, WowmaOrderDetail, WowmaBuyersOrderDetail
from yaget.models import WowmaShopInfo

# logging
logging.config.fileConfig(fname="/app/yaget/management/commands/wowma_do_buyers_order_logging.config", disable_existing_loggers=False)

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


class Command(BaseCommand):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        help = 'do order buyers.'
        self.logger.debug('wowma_do_buyers_order Command in. init')
        self.common_chrome_driver = None
        self.driver = None
        self.upd_csv = []
        self.my_wowma_target_ct_list = []
        self.batch_status = None

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('--pk', nargs='?', default='', type=str)
        parser.add_argument('--payment_method', nargs='?', default='', type=str)
        # parser.add_argument('pk', nargs='+')

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('wowma_do_buyers_order handle is called')
            self.batch_status = BatchStatusUpd('wowma_do_buyers_order')
            self.batch_status.start()

            # ロジスピのカテゴリはLogispiInfoから取ってくる
            self.logispi_info_obj = LogispiInfo(self.logger)
            self.wowma_access = WowmaAccess(self.logger)

            # ロジスピに発注する母体
            self._exec_buyers_order(options['pk'], options['payment_method'])

            self.logger.info('wowma_do_buyers_order handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        # self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('wowma_do_buyers_order handle end')
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))
        return

    # wowmaから注文情報を取り込みロジスピに発注する
    def _exec_buyers_order(self, pk, payment_method):

        # 受注番号をコマンド引数 pk から取得。とれただけループして確認する
        self.logger.info('wowma_do_buyers_order _exec_buyers_order handle pk:' + pk)

        # パラメータ設定
        #end_date = datetime.date.today()
        #start_date = end_date + timedelta(weeks=-2)
        date_type = 0  # 0:注文日　1:発送日　2:入金日　3:発売(入荷)予定日　4:発送期限日　（デフォルト0）

        # 指定された注文情報取得
        wow_order = WowmaOrderInfo.objects.filter(
            orderid=pk,
        ).first()

        # 注文がヒットしたら処理
        if wow_order:

            # 注文に基づく発送先
            order_receiver_list = {
                "sender_name": wow_order.sender_name,
                "sender_kana": wow_order.sender_kana,
                "sender_zipcode": wow_order.sender_zipcode,
                "sender_address": wow_order.sender_address,
                "sender_phone_number_1": wow_order.sender_phone_number_1,
                "sender_phone_number_2": wow_order.sender_phone_number_2,
            }

            # 注文に紐づくショップ情報も必要
            shop_info = WowmaShopInfo.objects.filter(shop_id=wow_order.shop_id).first()
            shop_info_list = {
                "shop_name": shop_info.shop_name,
                "from_name": shop_info.from_name,
                "from_name_kana": shop_info.from_name_kana,
                "from_postcode": shop_info.from_postcode,
                "from_state": shop_info.from_state,
                "from_address_1": shop_info.from_address_1,
                "from_address_2": shop_info.from_address_2,
                "from_phone": shop_info.from_phone,
                "mail": shop_info.mail,
            }

            # ロジスピにログインしておく
            self.logispi_info_obj.login_logispi()
            self.logger.info('wowma_do_buyers_order _exec_buyers_order ログイン成功まで')

            wowma_order_detail_list = WowmaOrderDetail.objects.filter(
                orderinfo=wow_order
            ).all()

            order_list_url_for_buyers = []
            if wowma_order_detail_list:
                for wowma_order_detail in wowma_order_detail_list:
                    for i in range(wowma_order_detail.unit):
                        self.logger.info('item_code:[{}] 個数 {}/{}'.format(
                            wowma_order_detail.item_code,
                            i+1,
                            wowma_order_detail.unit))
                        order_list_url_for_buyers.append(
                            'https://buyerz.shop/shopdetail/' + str(wowma_order_detail.item_code)[4:])

                        # 購入をすすめる
                        buyers_order_id, payment_total = self.logispi_info_obj.get_buyers_detail_page(
                            'https://buyerz.shop/shopdetail/' + str(wowma_order_detail.item_code)[4:],
                            shop_info_list,
                            order_receiver_list,
                            payment_method,
                        )

                        if buyers_order_id:  # ロジスピの発注番号が返却されたら保存しておく
                            obj, created = WowmaBuyersOrderDetail.objects.update_or_create(
                                buyers_order_id=buyers_order_id,
                                order_detail=wowma_order_detail,
                                status='発注済み',
                                payment_method=payment_method,
                                payment_total=payment_total,
                                delivery_method=wow_order.delivery_method_id,
                                order_date=dt.now().strftime('%Y%m%d %H%M%S.%f'),
                                unit=1,
                            )
                            obj.save
                        else:
                            # Falseで返されたらスルー
                            pass

        else:
            # 注文がヒットなし
            self.logger.info('wowma_do_buyers_order _exec_buyers_order 該当の注文が見つからないので処理終了[{}]'.format(pk))
            raise Exception('_exec_buyers_order 該当の注文が見つからないので処理終了[{}]'.format(pk))

        """
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
        """

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
                    obj_detail, detail_created = WowmaOrderDetail.objects.update_or_create(
                        order_detail_id=str(mydom_detail.getElementsByTagName("orderDetailId")[0].firstChild.nodeValue),
                        orderinfo=WowmaOrderInfo(orderid=order_id),
                        item_management_id=self._chk_node_exists(document_detail, "itemManagementId", 0),
                        item_code=self._chk_node_exists(document_detail, "itemCode", 0),
                        lot_number=self._chk_node_exists(document_detail, "lotnumber", 0),
                        item_name=self._chk_node_exists(document_detail, "itemName", 0),
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
                    obj_detail.save()
                self.logger.info('wowma_get_order_detail end of save WowmaOrderDetail')

        else:
            self.logger.info('_exec_wowma_order_chk error occurred. wowma_get_order_detail retured false')

        self.logger.info('wowma_get_order_detail end.')
        return

