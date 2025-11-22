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
from qoo10_access import Qoo10Access
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.integrations.batch_status import BatchStatusUpd


# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import YaBuyersItemList, YaBuyersItemDetail, QooOrderInfo


#from yaget.AmaMws import AmaMwsProducts

# logging
logging.config.fileConfig(fname="/app/yaget/management/commands/qoo_order_chk_logging.config", disable_existing_loggers=False)

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
        help = 'qoo_order_chk.'
        self.logger.debug('qoo_order_chk Command in. init')
        self.common_chrome_driver = None
        self.driver = None
        self.upd_csv = []
        self.my_wowma_target_ct_list = []
        self.batch_status = None


    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

    # qoo10から受注情報を取り込む
    def _exec_qoo_order_chk(self):

        self.logger.debug('_exec_qoo_order_chk in')

        # 受注番号を取得。とれただけループして確認する
        # 期間は、2週間前くらい？ から今日まで。

        # パラメータ設定
        # 基準日の2週間前を算出
        ShippingStat = "1"  # 配送状態。（1：出荷待ち、2：出荷済み、3：発注確認、4：配送中、5：配送完了）
        search_Sdate = datetime.date.today()  # 照会開始日 例）20190101 (yyyyMMdd), 20190101153000 (yyyyMMddHHmmss)
        search_Edate = search_Sdate + timedelta(weeks=2)  # 照会終了日 例）20190101 (yyyyMMdd), 20190101153000 (yyyyMMddHHmmss)
        search_condition = "2"  # 日付の種類。（1：注文日、2：決済完了日、3：配送日、4：配送完了日）

        order_list = self.qoo10_access.qoo10_shipping_basic_get_shipping_info(
            ShippingStat, search_Sdate, search_Edate, search_condition)

        if order_list:

            for order in self.order_list:
                if order['res_code'] != "0":  # エラー
                    self.logger.info('_exec_qoo_order_chk error occurred res_code:[{}] res_msg][{}]'.format(
                        order['res_code'], order['res_msg']
                    ))
                    raise Exception("_exec_qoo_order_chk error occurred res_code:[{}] res_msg][{}]".format(
                        order['res_code'], order['res_msg']
                    ))

                # 正常にデータ取得できた。DB登録かな
                order_detail = order['res_obj']
                self.logger.debug('_exec_qoo_order_chk res_obj:[{}]'.format(order_detail))

                # 注文詳細をそれぞれ取り込む
                new_obj = QooOrderInfo.objects.filter(
                    order_no=order_detail['orderNo'],
                    seller_id=order_detail['sellerID'],
                ).first()
                if not new_obj:
                    obj, created = QooOrderInfo.objects.update_or_create(
                        order_no=order_detail['orderNo'],
                        shipping_status=order_detail['shippingStatus'],
                        seller_id=order_detail['sellerID'],
                        pack_no=order_detail['packNo'],
                        order_date=order_detail['orderDate'],
                        payment_date=order_detail['PaymentDate'],
                        est_shipping_date=order_detail['EstShippingDate'],
                        shipping_date=order_detail['ShippingDate'],
                        delivered_date=order_detail['DeliveredDate'],
                        buyer=order_detail['buyer'],
                        order_gata=order_detail['buyer_gata'],
                        buyer_tel=order_detail['buyerTel'],
                        buyer_mobile=order_detail['buyerMobile'],
                        buyer_email=order_detail['buyerEmail'],
                        item_code=order_detail['itemCode'],
                        seller_item_code=order_detail['sellerItemCode'],
                        item_title=order_detail['itemTitle'],
                        option=order_detail['option'],
                        option_code=order_detail['optionCode'],
                        order_price=order_detail['orderPrice'],
                        order_qty=order_detail['orderQty'],
                        discount=order_detail['discount'],
                        total=order_detail['total'],
                        receiver=order_detail['receiver'],
                        receiver_gata=order_detail['receiver_gata'],
                        shipping_country=order_detail['shippingCountry'],
                        zipcode=order_detail['zipcode'],
                        shipping_addr=order_detail['shippingAddr'],
                        addr1=order_detail['Addr1'],
                        addr2=order_detail['Addr2'],
                        receiver_tel=order_detail['receiverTel'],
                        receiver_mobile=order_detail['receiverMobile'],
                        hope_date=order_detail['hopeDate'],
                        sender_name=order_detail['senderName'],
                        sender_tel=order_detail['senderTel'],
                        sender_nation=order_detail['senderNation'],
                        sender_zipcode=order_detail['senderZipCode'],
                        sender_addr=order_detail['senderAddr'],
                        shipping_way=order_detail['ShippingWay'],
                        shipping_msg=order_detail['ShippingMsg'],
                        payment_method=order_detail['PaymentMethod'],
                        seller_discount=order_detail['SellerDiscount'],
                        currency=order_detail['Currency'],
                        shipping_rate=order_detail['ShippingRate'],
                        related_order=order_detail['RelatedOrder'],
                        shipping_rate_type=order_detail['shippingRateType'],
                        delivery_company=order_detail['DeliveryCompany'],
                        voucher_code=order_detail['VoucherCode'],
                        packing_no=order_detail['PackingNo'],
                        seller_delivery_no=order_detail['SellerDeliveryNo'],
                        payment_nation=order_detail['PaymentNation'],
                        gift=order_detail['Gift'],
                        cod_price=order_detail['cod_price'],
                        cart_discount_seller=order_detail['Cart_Discount_Seller'],
                        cart_discount_qoo10=order_detail['Cart_Discount_Qoo10'],
                        settle_price=order_detail['SettlePrice'],
                        branch_name=order_detail['BranchName'],
                        tracking_no=order_detail['TrackingNo'],
                        oversea_consignment=order_detail['OverseaConsignment'],
                        oversea_consignment_receiver=order_detail['OverseaConsignment_receiver'],
                        oversea_consignment_country=order_detail['OverseaConsignment_Country'],
                        oversea_consignment_zipcode=order_detail['OverseaConsignment_zipCode'],
                        oversea_consignment_addr1=order_detail['OverseaConsignment_Addr1'],
                        oversea_consignment_addr2=order_detail['OverseaConsignment_Addr2'],
                    )
                    obj.save()
                else:
                    new_obj.order_no = order_detail['orderNo']
                    new_obj.shipping_status = order_detail['shippingStatus']
                    new_obj.seller_id = order_detail['sellerID']
                    new_obj.pack_no = order_detail['packNo']
                    new_obj.order_date = order_detail['orderDate']
                    new_obj.payment_date = order_detail['PaymentDate']
                    new_obj.est_shipping_date = order_detail['EstShippingDate']
                    new_obj.shipping_date = order_detail['ShippingDate']
                    new_obj.delivered_date = order_detail['DeliveredDate']
                    new_obj.buyer = order_detail['buyer']
                    new_obj.order_gata = order_detail['buyer_gata']
                    new_obj.buyer_tel = order_detail['buyerTel']
                    new_obj.buyer_mobile = order_detail['buyerMobile']
                    new_obj.buyer_email = order_detail['buyerEmail']
                    new_obj.item_code = order_detail['itemCode']
                    new_obj.seller_item_code = order_detail['sellerItemCode']
                    new_obj.item_title = order_detail['itemTitle']
                    new_obj.option = order_detail['option']
                    new_obj.option_code = order_detail['optionCode']
                    new_obj.order_price = order_detail['orderPrice']
                    new_obj.order_qty = order_detail['orderQty']
                    new_obj.discount = order_detail['discount']
                    new_obj.total = order_detail['total']
                    new_obj.receiver = order_detail['receiver']
                    new_obj.receiver_gata = order_detail['receiver_gata']
                    new_obj.shipping_country = order_detail['shippingCountry']
                    new_obj.zipcode = order_detail['zipcode']
                    new_obj.shipping_addr = order_detail['shippingAddr']
                    new_obj.addr1 = order_detail['Addr1']
                    new_obj.addr2 = order_detail['Addr2']
                    new_obj.receiver_tel = order_detail['receiverTel']
                    new_obj.receiver_mobile = order_detail['receiverMobile']
                    new_obj.hope_date = order_detail['hopeDate']
                    new_obj.sender_name = order_detail['senderName']
                    new_obj.sender_tel = order_detail['senderTel']
                    new_obj.sender_nation = order_detail['senderNation']
                    new_obj.sender_zipcode = order_detail['senderZipCode']
                    new_obj.sender_addr = order_detail['senderAddr']
                    new_obj.shipping_way = order_detail['ShippingWay']
                    new_obj.shipping_msg = order_detail['ShippingMsg']
                    new_obj.payment_method = order_detail['PaymentMethod']
                    new_obj.seller_discount = order_detail['SellerDiscount']
                    new_obj.currency = order_detail['Currency']
                    new_obj.shipping_rate = order_detail['ShippingRate']
                    new_obj.related_order = order_detail['RelatedOrder']
                    new_obj.shipping_rate_type = order_detail['shippingRateType']
                    new_obj.delivery_company = order_detail['DeliveryCompany']
                    new_obj.voucher_code = order_detail['VoucherCode']
                    new_obj.packing_no = order_detail['PackingNo']
                    new_obj.seller_delivery_no = order_detail['SellerDeliveryNo']
                    new_obj.payment_nation = order_detail['PaymentNation']
                    new_obj.gift = order_detail['Gift']
                    new_obj.cod_price = order_detail['cod_price']
                    new_obj.cart_discount_seller = order_detail['Cart_Discount_Seller']
                    new_obj.cart_discount_qoo10 = order_detail['Cart_Discount_Qoo10']
                    new_obj.settle_price = order_detail['SettlePrice']
                    new_obj.branch_name = order_detail['BranchName']
                    new_obj.tracking_no = order_detail['TrackingNo']
                    new_obj.oversea_consignment = order_detail['OverseaConsignment']
                    new_obj.oversea_consignment_receiver = order_detail['OverseaConsignment_receiver']
                    new_obj.oversea_consignment_country = order_detail['OverseaConsignment_Country']
                    new_obj.oversea_consignment_zipcode = order_detail['OverseaConsignment_zipCode']
                    new_obj.oversea_consignment_addr1 = order_detail['OverseaConsignment_Addr1']
                    new_obj.oversea_consignment_addr2 = order_detail['OverseaConsignment_Addr2']
                    new_obj.save()

        else:
            # 受注情報なし
            self.logger.debug('_exec_qoo_order_chk 注文なし　処理終了')
        return

        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('qoo_order_chk handle is called')
            self.batch_status = BatchStatusUpd('qoo_order_chk')
            self.batch_status.start()

            self.qoo10_access = Qoo10Access(self.logger)
            self.qoo10_access.qoo10_create_cert_key()

            # 受注チェックの母体
            self._exec_qoo_order_chk()

            self.logger.info('qoo_order_chk handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        #self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('qoo_order_chk handle end')
        return
