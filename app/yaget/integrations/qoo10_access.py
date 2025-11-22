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
import logging
import logging.config
import traceback
from time import sleep
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
import requests
import json
import http
from http.client import HTTPConnection

#from .models import QooShopInfo
from yaget.models import QooShopInfo

http.client.HTTPConnection.debuglevel=2
HTTPConnection.debuglevel = 2
#HTTPConnection.set_debuglevel(HTTPConnection.debuglevel)

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
#logging.config.fileConfig(fname="/app/yaget/management/commands/ya_buyers_list_logging.config", disable_existing_loggers=False)

#/app/yaget/log

# requestsのlogger
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
my_rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/log/yaget_buyers_qoo10_request.log',
    encoding='utf-8',
    maxBytes=1000000,
    backupCount=3
)
requests_log.addHandler(my_rh)

# --- logger 設定 -----------------------------------------
my_logger = logging.getLogger(__name__)
my_logger.setLevel(logging.DEBUG)
#logger.setLevel(20)

# ログローテ設定
rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/log/qoo10_access.log',
    encoding='utf-8',
    maxBytes=1000000,
    backupCount=3
)
fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
rh.setFormatter(fh_formatter)

ch = logging.StreamHandler()
#ch.setLevel(logging.INFO)
ch.setLevel(logging.DEBUG)
ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(ch_formatter)

my_logger.addHandler(rh)
my_logger.addHandler(ch)
# --- logger 設定 -----------------------------------------


# 共通変数
mydwsrc_dir = "/app/yaget/qoo10/dwsrc"
mydwimg_dir = "/app/yaget/qoo10/dwimg/"
myupdcsv_dir = "/app/yaget/qoo10/updcsv/"

"""
def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))
"""

# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class Qoo10Access(object):
    def __init__(self, logger):

        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(20)

        # ログローテ設定
        rh = logging.handlers.RotatingFileHandler(
            r'/app/yaget/log/qoo10_access.log',
            encoding='utf-8',
            maxBytes=1000000,
            backupCount=3
        )
        fh_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
        rh.setFormatter(fh_formatter)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
        ch.setFormatter(ch_formatter)

        logger.addHandler(rh)
        logger.addHandler(ch)
        """

        #self.logger = logger
        self.logger = my_logger
        self.requests_log = requests_log
        help = 'qoo10 access'
        self.logger.info('qoo10_access in. init 00')

        # Qoo10の登録してあるショップから、開店中のものだけ取得
        self.shop_obj_list = []
        shop_info_list = QooShopInfo.objects.filter(shop_status=1)
        for shop_info in shop_info_list:
            tmp_list = {
                "my_shop_num": shop_info.my_shop_num,
                "auth_key": shop_info.auth_key,
                "user_id": shop_info.user_id,
                "pwd": shop_info.pwd,
                "target_url": shop_info.target_url,
            }

            # 実体を作ってリストに入れる
            self.shop_obj_list.append(Qoo10AccessExec(self.logger,tmp_list))

        """
        self.cert_key = ""
        self.auth_key = "BhiQeRsAhG1HbSfwbr3XEUnvFuqGcIhIRRYxJ1c_g_1_Pp0_g_3_"
        self.target_url = "https://api.qoo10.jp/GMKT.INC.Front.QAPIService/ebayjapan.qapi/"
        self.user_id = "yukiyukishop"
        self.pwd = "@.Okayama358"
        self.get_headers = {
            'v': '1.0',
            'key': self.auth_key,
            'user_id': self.user_id,
            'pwd': self.pwd,
        }
        self.post_headers = {
            'user_id': self.user_id,
            'pwd': self.pwd,
        }
        """
        #self.logger.info('qoo10_access in. init end')

    # 販売認証キー発行(ショップ数だけ繰り返す)
    def qoo10_create_cert_key(self):
        try:
            for shop_obj in self.shop_obj_list:
                ret = shop_obj.qoo10_create_cert_key()
                if not ret:
                    raise Exception("qoo10_create_cert_key exception occurred.")
        except Exception as e:
            raise

    # Qoo10に新商品登録する際に必要なAPIのセットを順次呼びます。
    # (ショップ数だけ繰り返す)
    def qoo10_my_set_new_goods(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_my_set_new_goods(goods)
        except Exception as e:
            raise

    # Qoo10に商品更新する際に必要なAPIのセットを順次呼びます。
    # 戻りはなし、もし途中でエラー発生したら例外を投げます。
    # (ショップ数だけ繰り返す)
    def qoo10_my_set_update_goods(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_my_set_update_goods(goods)
        except Exception as e:
            raise

    # 販売者が登録した商品の取引の状態別照会をするためのAPIメソッドです。
    # （1ページに最大500個までの商品が照会が可能。ページを指定表示することができます。）
    # item_status:商品の取引状況（検収待機= S0、取引待機= S1、取引可能= S2、取引廃止= S4）
    # page:ページ番号（入力しない場合は、1ページを照会）
    # (ショップ数だけ繰り返す)
    def qoo10_items_lookup_get_all_goods_info(self, item_status, page):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_items_lookup_get_all_goods_info(item_status, page)
        except Exception as e:
            raise

    # 商品コードを入力して、単一の商品の商品情報を照会するためのAPIメソッドです。
    def qoo10_items_lookup_get_item_detail_info(self, goods):
        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_code, res_msg, res_obj = shop_obj.qoo10_items_lookup_get_item_detail_info(goods)
                tmp_list = {
                    "res_code": res_code,
                    "res_msg": res_msg,
                    "res_obj": res_obj,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        return ret_obj_list

    # Qoo10に新しい商品を登録するためのAPIメソッドです。
    def qoo10_items_basic_set_new_goods(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                ret_code, ret_msg = shop_obj.qoo10_items_basic_set_new_goods(goods)
                if int(ret_code) != 0:
                    # 更新失敗
                    raise Exception("qoo10_items_basic_set_new_goods 失敗？[{}][{}][{}]"
                                    .format(goods.gid, ret_code, ret_msg))
        except Exception as e:
            raise

    # Qoo10に登録した販売商品情報を変更するためのAPIメソッドです。
    def qoo10_items_basic_update_goods(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_items_basic_update_goods(goods)
        except Exception as e:
            raise

    # qoo10の商品詳細を更新します
    def qoo10_items_contents_edit_goods_contents(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_items_contents_edit_goods_contents(goods)
        except Exception as e:
            raise

    # Qoo10に登録した商品のマルチ画像を登録するためのAPIメソッドです。
    def qoo10_items_contents_edit_goods_multi_image(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_items_contents_edit_goods_multi_image(goods)
        except Exception as e:
            raise

    # Qoo10に登録した商品の商品情報を修正するためのAPIメソッドです。
    # attribute: Option name: Max 100 , Detail : Max 500
    # 追加する商品情報。商品に関する追加情報を入力します。
    # 入力フォーマット：追加情報名1 || *追加情報1の詳細説明$$$$追加情報名2 || *追加情報2の詳細説明
    def qoo10_items_basic_set_item_property_info(self, goods, attribute):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_items_basic_set_item_property_info(goods, attribute)
        except Exception as e:
            raise

    # Qoo10に登録した商品の取引状態を変更するためのAPIメソッドです。
    def qoo10_items_basic_edit_goods_status(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                ret_code, ret_msg = shop_obj.qoo10_items_basic_edit_goods_status(goods)
                if int(ret_code) != 0:
                    # 更新失敗
                    raise Exception("qoo10_items_basic_edit_goods_status 失敗？[{}][{}][{}]"
                                    .format(goods.gid, ret_code, ret_msg))
        except Exception as e:
            raise

    # Qoo10に登録した商品の価格、数量、販売期限を修正するためのAPIメソッドです。
    def qoo10_items_order_set_goods_price_qty(self, goods):
        try:
            for shop_obj in self.shop_obj_list:
                ret_code, ret_msg = shop_obj.qoo10_items_order_set_goods_price_qty(goods)
                if int(ret_code) != 0:
                    # 更新失敗
                    raise Exception("qoo10_items_order_set_goods_price_qty 失敗？[{}][{}][{}]"
                                    .format(goods.gid, ret_code, ret_msg))

        except Exception as e:
            raise

    # 複数の商品の価格、在庫、有効期限を修正するためのAPIメソッドです。
    def qoo10_items_order_set_goods_price_qty_bulk(self, json_list):
        try:
            for shop_obj in self.shop_obj_list:
                ret_code, ret_msg = shop_obj.qoo10_items_order_set_goods_price_qty_bulk(json_list)
                if int(ret_code) != 0:
                    # 更新失敗
                    raise Exception("qoo10_items_order_set_goods_price_qty_bulk 失敗？[{}][{}][{}]"
                                    .format(ret_code, ret_msg, json_list))
        except Exception as e:
            raise

    # 売り手の出荷状態情報を照会するためのAPIメソッドです。
    def qoo10_shipping_basic_get_shipping_info(self,
                                               shipping_stat,  # 配送状態。（1：出荷待ち、2：出荷済み、3：発注確認、4：配送中、5：配送完了）
                                               search_Sdate,  # 照会開始日 例）20190101 (yyyyMMdd), 20190101153000 (yyyyMMddHHmmss)
                                               search_Edate,  # 照会終了日 例）20190101 (yyyyMMdd), 20190101153000 (yyyyMMddHHmmss)
                                               search_condition):  # 日付の種類。（1：注文日、2：決済完了日、3：配送日、4：配送完了日）
        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_code, res_msg, res_obj = shop_obj.qoo10_shipping_basic_get_shipping_info(
                    shipping_stat,
                    search_Sdate,
                    search_Edate,
                    search_condition)
                tmp_list = {
                    "res_code": res_code,
                    "res_msg": res_msg,
                    "res_obj": res_obj,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        return ret_obj_list

    # 売り手の注文シングル件配送/クレーム情報を照会するためのAPIメソッドです。
    def qoo10_shipping_basic_get_shipping_and_claiminfo_by_order_no(self,
                                               order_no,  # 注文番号
                                               ):
        try:
            for shop_obj in self.shop_obj_list:
                shop_obj.qoo10_shipping_basic_get_shipping_and_claiminfo_by_order_no(order_no)
        except Exception as e:
            raise

    # 発注確認の状態を変更するためのAPIメソッドです。
    def qoo10_shipping_basic_set_seller_check_yn(self,
                                               order_no,  # 注文番号
                                               est_ship_dt,  # 発送予定日 例）20190101 (yyyyMMdd)
                                               delay_type,  # 遅延の理由。（1：商品準備中、2：注文製作（オーダーメイド）、3：顧客の要求、4：その他）
                                               delay_memo):  # 販売者メモ
        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_code, res_msg = shop_obj.qoo10_shipping_basic_set_seller_check_yn(
                    order_no,
                    est_ship_dt,
                    delay_type,
                    delay_memo)
                tmp_list = {
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        return ret_obj_list

    # 配送ただし事前リクエスト制について発送確認処理をするためのAPIメソッドです。
    def qoo10_shipping_basic_set_sending_info(self,
                                               order_no,  # 注文番号
                                               shipping_corp,  # 配送会社
                                               tracking_no,  # 送り状番号
                                               ):
        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_code, res_msg = shop_obj.qoo10_shipping_basic_set_sending_info(
                    order_no,
                    shipping_corp,
                    tracking_no)
                tmp_list = {
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)
        except Exception as e:
            raise
        return ret_obj_list

# Qoo10にリクエストする実体。こいつは
class Qoo10AccessExec(object):
    def __init__(self, logger, shop_info):
        self.logger = logger
        self.requests_log = requests_log
        help = 'qoo10 access'
        self.logger.info('qoo10_access_exec in. init 00_exec')

        self.cert_key = ""
        self.auth_key = shop_info['auth_key']
        self.target_url = shop_info['target_url']
        self.user_id = shop_info['user_id']
        self.pwd = shop_info['pwd']
        self.get_headers = {
            'v': '1.0',
            'key': self.auth_key,
            'user_id': self.user_id,
            'pwd': self.pwd,
        }
        self.post_headers = {
            'user_id': self.user_id,
            'pwd': self.pwd,
        }

        """
        self.cert_key = ""
        self.auth_key = "BhiQeRsAhG1HbSfwbr3XEUnvFuqGcIhIRRYxJ1c_g_1_Pp0_g_3_"
        self.target_url = "https://api.qoo10.jp/GMKT.INC.Front.QAPIService/ebayjapan.qapi/"
        self.user_id = "yukiyukishop"
        self.pwd = "@.Okayama358"
        self.get_headers = {
            'v': '1.0',
            'key': self.auth_key,
            'user_id': self.user_id,
            'pwd': self.pwd,
        }
        self.post_headers = {
            'user_id': self.user_id,
            'pwd': self.pwd,
        }
        """
        # self.logger.info('qoo10_access in. init end')

    def get_cert_key(self):
        return self.cert_key

    # 販売認証キー発行
    def qoo10_get_post_headers(self, api_version):
        post_headers = {
            'GiosisCertificationKey': self.cert_key,
            'Content-type': 'application/x-www-form-urlencoded',
            'QAPIVersion': api_version,
        }
        return post_headers

    # 販売認証キー発行
    def qoo10_create_cert_key(self):
        try:
            #self.logger.info('qoo10_create_cert_key in.')
            self.logger.debug('qoo10_create_cert_key in.(debug)')
            method = 'CertificationAPI.CreateCertificationKey'

            """
            # get method
            get_params = {
                'v': '1.0',
                'key': self.auth_key,
                'user_id': self.user_id,
                'pwd': self.pwd,
                'method': method,
                'returnType': 'xml',
            }
            response = requests.get(self.target_url, headers=self.get_headers, params=get_params)
            self.logger.debug('get_response:[{}]'.format(str(response.text)))


            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            result_code = document.getElementsByTagName("ResultCode")[0].firstChild.nodeValue
            result_msg = document.getElementsByTagName("ResultMsg")[0].firstChild.nodeValue
            result_obj = document.getElementsByTagName("ResultObject")[0].firstChild.nodeValue

            self.logger.debug('ret ResultCode:[{}]'.format(str(result_code)))
            self.logger.debug('ret ResultMsg:[{}]'.format(str(result_msg)))
            self.logger.debug('ret ResultObject:[{}]'.format(str(result_obj)))
            self.logger.debug('ret str:[{}]'.format(document.toprettyxml(indent="  ")))
            """

            """
            print('qoo10_get_order_detail response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            """


            # Post test
            post_params = {
                'user_id': self.user_id,
                'pwd': self.pwd,
                'returnType': 'application/json',
            }
            post_params = urllib.parse.urlencode(post_params)

            #query_string = urllib.parse.urlencode(sorted(post_params.items()))

            #post_headers = self.qoo10_get_post_headers('1.0')

            post_headers = {
                'GiosisCertificationKey': self.auth_key,
                'Content-type': 'application/x-www-form-urlencoded',
                'QAPIVersion': '1.0',
            }

            #url = 'https://{}{}?{}'.format(
            #    self.target_url, method, query_string)
            #url = '{}{}?{}'.format(
            #    self.target_url, method, query_string)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            #res = requests.post(url, headers=post_headers)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)
            self.logger.debug('res_code[{}]:res_obj[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultObject']),
                str(json_dump['ResultMsg']),
            ))

            # 認証キーを保持
            self.cert_key = str(json_dump['ResultObject'])

            self.logger.debug('qoo10_create_cert_key end.(debug)')
            #self.logger.info('qoo10_create_cert_key end.')
            #return document
            #return str(response.text)
            return str(self.cert_key)

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return traceback.format_exc()

        return False


    # Qoo10に新商品登録する際に必要なAPIのセットを順次呼びます。
    # 戻りはなし、もし途中でエラー発生したら例外を投げます。
    def qoo10_my_set_new_goods(self, goods):
        try:
            self.logger.debug('qoo10_my_set_new_goods in.')

            # もし qoo_gdno もしくはqoo_seller_codeがセットされてたら既に登録済みのはず。updateに回す
            if goods.qoo_gdno and len(goods.qoo_gdno) > 0:
                self.logger.debug('qoo10_my_set_new_goods 登録済みのはずだからupdateを 1')
                self.qoo10_my_set_update_goods(goods)
                """
                elif goods.qoo_seller_code and len(goods.qoo_seller_code) > 0:
                    self.logger.debug('qoo10_my_set_new_goods 登録済みのはずだからupdateを 2')
                    self.qoo10_my_set_update_goods(goods)
                """
            else:
                # qoo10_items_basic_set_new_goods を呼ばないと。
                ret_code, ret_msg = self.qoo10_items_basic_set_new_goods(goods)
                if int(ret_code) == 0:
                    # 更新に成功している。続けてステータスを更新
                    ret_code, ret_msg = self.qoo10_items_basic_edit_goods_status(goods)
                    if int(ret_code) == 0:
                        # 更新成功している。続けてマルチ画像を更新
                        ret_code, ret_msg = self.qoo10_items_contents_edit_goods_multi_image(goods)
                        if int(ret_code) == 0:
                            # 最後に在庫数を更新
                            ret_code, ret_msg = self.qoo10_items_order_set_goods_price_qty(goods)
                            if int(ret_code) != 0:
                                # 更新失敗
                                raise Exception("qoo10_items_order_set_goods_price_qty 失敗？[{}][{}][{}]"
                                                .format(goods.gid, ret_code, ret_msg))
                        else:
                            # 更新失敗
                            raise Exception("qoo10_items_contents_edit_goods_multi_image 失敗？[{}][{}][{}]"
                                            .format(goods.gid, ret_code, ret_msg))
                    else:
                        # 更新失敗
                        raise Exception("qoo10_items_basic_edit_goods_status 失敗？[{}][{}][{}]"
                                        .format(goods.gid, ret_code, ret_msg))
                else:
                    # 更新時にエラー？
                    raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{}] stock:[{}][{}][{}]"
                                    .format(goods.gid, goods.stock, ret_code, ret_msg))

        except Exception as e:
            raise

        self.logger.debug('qoo10_my_set_new_goods out.')
        return

    # Qoo10に商品更新する際に必要なAPIのセットを順次呼びます。
    # 戻りはなし、もし途中でエラー発生したら例外を投げます。
    def qoo10_my_set_update_goods(self, goods):
        try:
            self.logger.debug('qoo10_my_set_update_goods in.')

            ret_code, ret_msg = self.qoo10_items_basic_update_goods(goods)
            if int(ret_code) == 0:
                # 更新に成功している。続けて更新時のみ、商品詳細を更新
                ret_code, ret_msg = self.qoo10_items_contents_edit_goods_contents(goods)
                if int(ret_code) == 0:
                    # 更新に成功している。続けてステータスを更新
                    ret_code, ret_msg = self.qoo10_items_basic_edit_goods_status(goods)
                    if int(ret_code) == 0:
                        # 更新成功している。続けてマルチ画像を更新
                        ret_code, ret_msg = self.qoo10_items_contents_edit_goods_multi_image(goods)
                        if int(ret_code) == 0:
                            # 最後に在庫数を更新
                            ret_code, ret_msg = self.qoo10_items_order_set_goods_price_qty(goods)
                            if int(ret_code) != 0:
                                # 更新失敗
                                raise Exception("qoo10_items_order_set_goods_price_qty 失敗？[{}][{}][{}]"
                                                .format(goods.gid, ret_code, ret_msg))
                        else:
                            # 更新失敗
                            raise Exception("qoo10_items_contents_edit_goods_multi_image 失敗？[{}][{}][{}]"
                                            .format(goods.gid, ret_code, ret_msg))
                    else:
                        # 更新失敗
                        raise Exception("qoo10_items_basic_edit_goods_status 失敗？[{}][{}][{}]"
                                        .format(goods.gid, ret_code, ret_msg))
                else:
                    # 更新失敗
                    raise Exception("qoo10_items_contents_edit_goods_contents 失敗？[{}][{}][{}]"
                                    .format(goods.gid, ret_code, ret_msg))
            else:
                # 更新時にエラー？
                raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{}] stock:[{}][{}][{}]".format(goods.gid, goods.stock,ret_code, ret_msg))

        except Exception as e:
            raise

        self.logger.debug('qoo10_my_set_update_goods out.')
        return

    # 販売者が登録した商品の取引の状態別照会をするためのAPIメソッドです。
    # （1ページに最大500個までの商品が照会が可能。ページを指定表示することができます。）
    # item_status:商品の取引状況（検収待機= S0、取引待機= S1、取引可能= S2、取引廃止= S4）
    # page:ページ番号（入力しない場合は、1ページを照会）
    def qoo10_items_lookup_get_all_goods_info(self, item_status, page):
        try:
            #self.logger.info('qoo10_create_cert_key in.')
            self.logger.debug('qoo10_items_lookup_get_all_goods_info in.(debug)')
            method = 'ItemsLookup.GetAllGoodsInfo'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'ItemStatus': item_status,
                'Page': page,
                'returnType': 'application/json',
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            if json_dump.get('ResultObject'):
                # 該当商品あり
                self.logger.debug('TotalItems[{}]:TotalPages[{}]:PresentPage[{}]'.format(
                    str(json_dump['ResultObject']['TotalItems']),
                    str(json_dump['ResultObject']['TotalPages']),
                    str(json_dump['ResultObject']['PresentPage']),
                ))
                # 個別の商品情報を
                self.logger.debug('.. start chk Items')
                if json_dump['ResultObject']['Items']:
                    self.logger.debug('.. chk Items is ok')
                    for item in json_dump['ResultObject']['Items']:
                        self.logger.debug('ItemCode[{}]:SellerCode[{}]:ItemStatus[{}]'.format(
                            str(item['ItemCode']),
                            str(item['SellerCode']),
                            str(item['ItemStatus']),
                        ))
                else:
                    # 商品登録なし？
                    self.logger.debug('qoo10_items_lookup_get_all_goods_info: 通信成功したが該当商品なし')

            else:
                # 商品登録なし？
                self.logger.debug('qoo10_items_lookup_get_all_goods_info: 該当商品なし')

            self.logger.debug('qoo10_items_lookup_get_all_goods_info end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return False, traceback.format_exc()

        return False, None

    # 商品コードを入力して、単一の商品の商品情報を照会するためのAPIメソッドです。
    def qoo10_items_lookup_get_item_detail_info(self, goods):
        try:
            self.logger.debug('qoo10_items_lookup_get_item_detail_info in.(debug)')
            method = 'ItemsLookup.GetItemDetailInfo'

            post_headers = self.qoo10_get_post_headers('1.1')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'SellerCode': goods.qoo_seller_code,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

            ret_resultobj = ''
            if json_dump.get('ResultObject'):
                # 該当商品あり
                #self.logger.debug('ItemCode[{}]:ItemStatus[{}]:ItemTitle[{}]:ItemDetail[{}]'.format(
                self.logger.debug('ItemCode[{}]:ItemStatus[{}]:ItemTitle[{}]'.format(
                    str(json_dump['ResultObject'][0]['ItemCode']),
                    str(json_dump['ResultObject'][0]['ItemStatus']),
                    str(json_dump['ResultObject'][0]['ItemTitle']),
                    #str(json_dump['ResultObject'][0]['ItemDetail']),
                ))
                ret_resultobj = str(json_dump['ResultObject'])

            else:
                # 商品登録なし？
                self.logger.debug('qoo10_items_lookup_get_item_detail_info: 該当商品なし')

            self.logger.debug('qoo10_items_lookup_get_item_detail_info end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg']), ret_resultobj

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc(), None

        return str("-1"), "qoo10_items_lookup_get_item_detail_info なにかエラー発生しました", None

    # Qoo10に新しい商品を登録するためのAPIメソッドです。
    def qoo10_items_basic_set_new_goods(self, goods):
        try:
            #self.logger.info('qoo10_create_cert_key in.')
            self.requests_log.debug('req:qoo10_items_basic_set_new_goods in.(debug)')
            self.logger.debug('qoo10_items_basic_set_new_goods in.(debug)')
            method = 'ItemsBasic.SetNewGoods'

            post_headers = self.qoo10_get_post_headers('1.1')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'SecondSubCat': goods.qoo_ctid,
                'OuterSecondSubCat': '',
                'Drugtype': '',
                'BrandNo': '',
                'ItemTitle': goods.qoo_gname,
                'PromotionName': goods.qoo_promotion_name,
                'SellerCode': goods.qoo_seller_code,
                'IndustrialCodeType': '',
                'IndustrialCode': '',
                'ModelNM': goods.qoo_model_name,
                'ManufactureDate': '',
                'ProductionPlaceType': 'F',
                'ProductionPlace': 'CN',
                'Weight': '',
                'Material': '',
                'AdultYN': goods.qoo_adult_yn,
                'ContactInfo': goods.qoo_contact_info,
                'StandardImage': goods.qoo_standard_img,
                'VideoURL': '',
                'ItemDescription': goods.qoo_gdetail,
                'AdditionalOption': goods.qoo_additional_opt,
                'ItemType': '',
                'RetailPrice': '0',
                'ItemPrice': goods.qoo_price,
                'ItemQty': goods.qoo_item_qty,
                'ExpireDate': '',
                'ShippingNo': goods.qoo_shipping_no,
                #'ShippingNo': '549678',
                'AvailableDateType': '0',
                #'AvailableDateType': goods.qoo_available_date_type,
                'AvailableDateValue': '3',
                #'AvailableDateValue': goods.qoo_available_date_value,
                'Keyword': goods.qoo_keyword,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            if json_dump.get('ResultObject'):
                if json_dump['ResultObject']['GdNo']:
                    # 商品登録成功
                    self.logger.debug('GdNo[{}]:'.format(
                        str(json_dump['ResultObject']['GdNo']),
                    ))
                    goods.qoo_gdno = json_dump['ResultObject']['GdNo']
                    goods.save()
                else:
                    # 商品登録失敗
                    self.logger.debug('qoo10_items_basic_set_new_goods: 通信成功したが商品登録失敗？')

            else:
                # 商品登録なし？
                self.logger.debug('qoo10_items_basic_set_new_goods: 該当商品なし')

            self.logger.debug('qoo10_items_basic_set_new_goods end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), None

    # Qoo10に登録した販売商品情報を変更するためのAPIメソッドです。
    def qoo10_items_basic_update_goods(self, goods):
        try:
            #self.logger.info('qoo10_create_cert_key in.')
            self.logger.debug('qoo10_items_basic_update_goods in.(debug)')
            self.logger.debug('qoo_gdno:[{}]'.format(goods.qoo_gdno))
            method = 'ItemsBasic.UpdateGoods'

            post_headers = self.qoo10_get_post_headers('1.1')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'SecondSubCat': goods.qoo_ctid,
                'OuterSecondSubCat': '',
                'Drugtype': '',
                'BrandNo': '',
                'ItemTitle': goods.qoo_gname,
                'PromotionName': goods.qoo_promotion_name,
                'SellerCode': goods.qoo_seller_code,
                'IndustrialCodeType': '',
                'IndustrialCode': '',
                'ModelNM': goods.qoo_model_name,
                'ManufactureDate': '',
                'ProductionPlaceType': '2',
                'ProductionPlace': 'CN',
                'Weight': '',
                'Material': '',
                'AdultYN': goods.qoo_adult_yn,
                'ContactInfo': goods.qoo_contact_info,
                'StandardImage': goods.qoo_standard_img,
                'VideoURL': '',
                'AdditionalOption': goods.qoo_additional_opt,
                'ItemType': goods.qoo_item_type,
                'RetailPrice': '0',
                'ItemPrice': goods.qoo_price,
                'ItemQty': goods.qoo_item_qty,
                'ExpireDate': '',
                'ShippingNo': goods.qoo_shipping_no,
                'OptionShippingNo1': '',
                'OptionShippingNo2': '',
                'DesiredShippingDate': '',
                'AvailableDateType': '0',
                #'AvailableDateType': goods.qoo_available_date_type,
                'AvailableDateValue': '3',
                #'AvailableDateValue': goods.qoo_available_date_value,
                'Keyword': goods.qoo_keyword,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            self.logger.debug('qoo10_items_basic_update_goods end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), None

    # qoo10の商品詳細を更新します
    def qoo10_items_contents_edit_goods_contents(self, goods):
        try:
            #self.logger.info('qoo10_create_cert_key in.')
            self.logger.debug('qoo10_items_contents_edit_goods_contents in.(debug)')
            method = 'ItemsContents.EditGoodsContents'

            post_headers = self.qoo10_get_post_headers('1.0')

            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'Contents': goods.qoo_gdetail,
            }

            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            self.logger.debug('qoo10_items_contents_edit_goods_contents end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return False, traceback.format_exc()

        return False, None

    # Qoo10に登録した商品のマルチ画像を登録するためのAPIメソッドです。
    def qoo10_items_contents_edit_goods_multi_image(self, goods):
        try:
            self.logger.debug('qoo10_items_contents_edit_goods_multi_image in.(debug)')

            # 取引廃止なら処理できない
            if goods.qoo_upd_status == 3:
                return True

            method = 'ItemsContents.EditGoodsMultiImage'

            post_headers = self.qoo10_get_post_headers('1.1')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'SellerCode': goods.qoo_seller_code,
                'EnlargedImage1': goods.g_img_src_1,
                'EnlargedImage2': goods.g_img_src_2,
                'EnlargedImage3': goods.g_img_src_3,
                'EnlargedImage4': goods.g_img_src_4,
                'EnlargedImage5': goods.g_img_src_5,
                'EnlargedImage6': goods.g_img_src_6,
                'EnlargedImage7': goods.g_img_src_7,
                'EnlargedImage8': goods.g_img_src_8,
                'EnlargedImage9': goods.g_img_src_9,
                'EnlargedImage10': goods.g_img_src_10,
                'EnlargedImage11': goods.g_img_src_11,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            self.logger.debug('qoo10_items_contents_edit_goods_multi_image end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), "qoo10_items_contents_edit_goods_multi_image なにかエラー発生しました"

    # Qoo10に登録した商品の商品情報を修正するためのAPIメソッドです。
    # attribute: Option name: Max 100 , Detail : Max 500
    # 追加する商品情報。商品に関する追加情報を入力します。
    # 入力フォーマット：追加情報名1 || *追加情報1の詳細説明$$$$追加情報名2 || *追加情報2の詳細説明
    def qoo10_items_basic_set_item_property_info(self, goods, attribute):
        try:
            self.logger.debug('qoo10_items_basic_set_item_property_info in.(debug)')
            method = 'ItemsBasic.SetItemPropertyInfo'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'SellerCode': goods.qoo_seller_code,
                'Attribute': attribute,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

            self.logger.debug('qoo10_items_basic_set_item_property_info end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), "qoo10_items_basic_set_item_property_info なにかエラー発生しました"


    # Qoo10に登録した商品の取引状態を変更するためのAPIメソッドです。
    def qoo10_items_basic_edit_goods_status(self, goods):
        try:
            self.logger.debug('qoo10_items_basic_edit_goods_status in.(debug)')
            method = 'ItemsBasic.EditGoodsStatus'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'SellerCode': goods.qoo_seller_code,
                'Status': goods.qoo_upd_status,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                # 商品状態が、1か2以外だったら更新できない。（承認拒否とかになってる）もしくは商品が存在しない。
                # qoo_upd_status　は 3にしてしまい、上位にエラーを返しておく
                error_cd = int(json_dump['ErrorCode'])
                if error_cd == -10009 or error_cd == -10001 or error_cd == -10003 \
                        or error_cd == -10004 or error_cd == -10005:
                    goods.qoo_upd_status = 3  # 取引廃止に更新
                    goods.save()

                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

            self.logger.debug('qoo10_items_basic_edit_goods_status end.(debug)')
            error_cd = int(json_dump['ResultCode'])
            if error_cd == -10009 or error_cd == -10001 or error_cd == -10003 \
                    or error_cd == -10004 or error_cd == -10005:
                goods.qoo_upd_status = 3  # 取引廃止に更新
                goods.save()
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), "qoo10_items_basic_edit_goods_status なにかエラー発生しました"

    # Qoo10に登録した商品の価格、数量、販売期限を修正するためのAPIメソッドです。
    def qoo10_items_order_set_goods_price_qty(self, goods):
        try:
            self.logger.debug('qoo10_items_order_set_goods_price_qty in.(debug)')
            method = 'ItemsOrder.SetGoodsPriceQty'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemCode': goods.qoo_gdno,
                'SellerCode': goods.qoo_seller_code,
                'Price': goods.qoo_price,
                'Qty': goods.stock,
                'ExpireDate': '',
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

            self.logger.debug('qoo10_items_order_set_goods_price_qty end.(debug)')
            return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), "qoo10_items_order_set_goods_price_qty なにかエラー発生しました"

    # 複数の商品の価格、在庫、有効期限を修正するためのAPIメソッドです。
    def qoo10_items_order_set_goods_price_qty_bulk(self, json_list):
        try:
            self.logger.debug('qoo10_items_order_set_goods_price_qty_bulk in.(debug)')
            self.logger.debug('json_list[{}]'.format(json.dumps(json_list)))
            method = 'ItemsOrder.SetGoodsPriceQtyBulk'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ItemInfoJson': json.dumps(json_list),
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            ret_msg = str(json_dump['ResultMsg'])

            if json_dump.get('ResultObject'):
                #ret_msg = ret_msg + 'count:[' + json_dump['ResultObject']['Count'] + '] Keys:[' + json_dump['ResultObject']['Keys'] + '] Values:[' + json_dump['ResultObject']['Values'] + ']'
                ret_msg = ret_msg + json.dumps(json_dump['ResultObject'][0])
            else:
                # 更新失敗？
                self.logger.debug('qoo10_items_order_set_goods_price_qty_bulk:更新失敗？')

            self.logger.debug('qoo10_items_order_set_goods_price_qty_bulk end.(debug)')
            return str(json_dump['ResultCode']), ret_msg

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            #print(traceback.format_exc())
            #return False
            return str("-1"), traceback.format_exc()

        return str("-1"), "qoo10_items_order_set_goods_price_qty_bulk なにかエラー発生しました"

    # 売り手の出荷状態情報を照会するためのAPIメソッドです。
    def qoo10_shipping_basic_get_shipping_info(self,
                                               shipping_stat,  # 配送状態。（1：出荷待ち、2：出荷済み、3：発注確認、4：配送中、5：配送完了）
                                               search_Sdate,  # 照会開始日 例）20190101 (yyyyMMdd), 20190101153000 (yyyyMMddHHmmss)
                                               search_Edate,  # 照会終了日 例）20190101 (yyyyMMdd), 20190101153000 (yyyyMMddHHmmss)
                                               search_condition):  # 日付の種類。（1：注文日、2：決済完了日、3：配送日、4：配送完了日）
        try:
            self.logger.debug('qoo10_shipping_basic_get_shipping_info in.(debug)')
            self.logger.info('qoo10_shipping_basic_get_shipping_info in.(debug)')
            method = 'ShippingBasic.GetShippingInfo_v2'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'ShippingStat': shipping_stat,
                'search_Sdate': search_Sdate,
                'search_Edate': search_Edate,
                'search_condition': search_condition,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            #result_obj = None
            #if json_dump.get('ResultObject'):
            #    result_obj = str(json_dump['ResultObject'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))
            self.logger.debug('res_obj[{}]'.format(json_dump['ResultObject']))
            self.logger.info('res_obj[{}]'.format(json_dump['ResultObject']))

        except Exception as e:
            self.logger.info(traceback.format_exc())
            self.logger.debug(traceback.format_exc())
            return str("-1"), traceback.format_exc()

        self.logger.info('qoo10_shipping_basic_get_shipping_info end.(debug)')
        self.logger.debug('qoo10_shipping_basic_get_shipping_info end.(debug)')
        return str(json_dump['ResultCode']), str(json_dump['ResultMsg']), json_dump['ResultObject']

    # 売り手の注文シングル件配送/クレーム情報を照会するためのAPIメソッドです。
    def qoo10_shipping_basic_get_shipping_and_claiminfo_by_order_no(self,
                                               order_no,  # 注文番号
                                               ):
        try:
            self.logger.debug('qoo10_shipping_basic_get_shipping_and_claiminfo_by_order_no in.(debug)')
            method = 'ShippingBasic.GetShippingAndClaimInfoByOrderNo_V2'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'OrderNo': order_no,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            result_obj = None
            if json_dump.get('ResultObject'):
                result_obj = str(json_dump['ResultObject'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return str("-1"), traceback.format_exc()

        self.logger.debug('qoo10_shipping_basic_get_shipping_and_claiminfo_by_order_no end.(debug)')
        return str(json_dump['ResultCode']), str(json_dump['ResultMsg']), result_obj

    # 発注確認の状態を変更するためのAPIメソッドです。
    def qoo10_shipping_basic_set_seller_check_yn(self,
                                               order_no,  # 注文番号
                                               est_ship_dt,  # 発送予定日 例）20190101 (yyyyMMdd)
                                               delay_type,  # 遅延の理由。（1：商品準備中、2：注文製作（オーダーメイド）、3：顧客の要求、4：その他）
                                               delay_memo):  # 販売者メモ
        try:
            self.logger.debug('qoo10_shipping_basic_set_seller_check_yn in.(debug)')
            method = 'ShippingBasic.SetSellerCheckYN_V2'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'OrderNo': order_no,
                'EstShipDt': est_ship_dt,
                'DelayType': delay_type,
                'DelayMemo': delay_memo,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return str("-1"), traceback.format_exc()

        self.logger.debug('qoo10_shipping_basic_set_seller_check_yn end.(debug)')
        return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])

    # 配送ただし事前リクエスト制について発送確認処理をするためのAPIメソッドです。
    def qoo10_shipping_basic_set_sending_info(self,
                                               order_no,  # 注文番号
                                               shipping_corp,  # 配送会社
                                               tracking_no,  # 送り状番号
                                               ):
        try:
            self.logger.debug('qoo10_shipping_basic_set_sending_info in.(debug)')
            method = 'ShippingBasic.SetSendingInfo'

            post_headers = self.qoo10_get_post_headers('1.0')

            # Post test
            post_params = {
                'returnType': 'application/json',
                'OrderNo': order_no,
                'ShippingCorp': shipping_corp,
                'TrackingNo': tracking_no,
            }
            post_params = urllib.parse.urlencode(post_params)

            url = self.target_url + method
            res = requests.post(url, headers=post_headers, data=post_params)
            # 文字化け対策
            res.encoding = res.apparent_encoding
            self.logger.debug('post_response:[{}]'.format(str(res.text)))
            json_dump = json.loads(res.text)

            if json_dump.get('ErrorCode'):
                # エラーかな
                return str(json_dump['ErrorCode']), str(json_dump['ErrorMsg'])

            # こっちはおそらく成功
            self.logger.debug('res_code[{}]:res_msg[{}]'.format(
                str(json_dump['ResultCode']),
                str(json_dump['ResultMsg']),
            ))

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return str("-1"), traceback.format_exc()

        self.logger.debug('qoo10_shipping_basic_set_sending_info end.(debug)')
        return str(json_dump['ResultCode']), str(json_dump['ResultMsg'])


    ###################################################################################################################
    # 以下は古いからまだ使ってない
    # 商品情報登録API
    def qoo10_register_item_info(self,
                                 item_name,
                                 item_code,
                                 item_price,
                                 postage_segment, # 送料設定区分 1:送料別/2:送料込み/3:個別送料
                                 postage, # 個別送料
                                 delivery_method_id, # 配送方法ID
                                 description, # 商品説明
                                 category_id, # カテゴリID
                                 sale_status, # 販売ステータス 1:販売中/2:販売終了商品
                                 stock, #　在庫数
                                 images, # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                 ):
        myrtn = 0
        try:
            self.logger.info('qoo10_register_item_info in.')
            method = "registerItemInfo"

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            my_register_item = dom.createElement("registerItem")
            request_dom.appendChild(my_register_item)

            # 商品名　設定
            my_item_name = dom.createElement("itemName")
            my_register_item.appendChild(my_item_name)
            my_item_name.appendChild(dom.createTextNode(item_name))

            # 商品コード　設定
            my_item_code = dom.createElement("itemCode")
            my_register_item.appendChild(my_item_code)
            my_item_code.appendChild(dom.createTextNode(str(item_code)))

            # 商品価格　設定
            my_item_price = dom.createElement("itemPrice")
            my_register_item.appendChild(my_item_price)
            my_item_price.appendChild(dom.createTextNode(str(item_price)))

            # 税区分　設定  1:内税　固定
            my_item_tax_segment = dom.createElement("taxSegment")
            my_register_item.appendChild(my_item_tax_segment)
            my_item_tax_segment.appendChild(dom.createTextNode(str("1")))

            # 送料設定区分　設定
            my_item_postage_segment = dom.createElement("postageSegment")
            my_register_item.appendChild(my_item_postage_segment)
            my_item_postage_segment.appendChild(dom.createTextNode(str(postage_segment)))

            # 送料　設定 送料設定区分が１，２のときは設定してはいけない
            if str(postage_segment) == "3":
                my_item_postage = dom.createElement("postage")
                my_register_item.appendChild(my_item_postage)
                my_item_postage.appendChild(dom.createTextNode(str(postage)))

            # 配送方法ID delivery_method_id
            my_delivery_method = dom.createElement("deliveryMethod")
            my_register_item.appendChild(my_delivery_method)

            my_delivery_method_id = dom.createElement("deliveryMethodId")
            my_delivery_method_id.appendChild(dom.createTextNode(str(delivery_method_id)))
            my_delivery_method.appendChild(my_delivery_method_id)

            my_delivery_method_seq = dom.createElement("deliveryMethodSeq")
            my_delivery_method_seq.appendChild(dom.createTextNode(str(1)))
            my_delivery_method.appendChild(my_delivery_method_seq)

            # 商品詳細　設定
            my_item_description = dom.createElement("description")
            my_register_item.appendChild(my_item_description)
            my_item_description.appendChild(dom.createTextNode(description))

            # categoryId　設定
            my_item_category_id = dom.createElement("categoryId")
            my_register_item.appendChild(my_item_category_id)
            my_item_category_id.appendChild(dom.createTextNode(str(category_id)))

            # saleStatus　設定
            my_item_sale_status = dom.createElement("saleStatus")
            my_register_item.appendChild(my_item_sale_status)
            my_item_sale_status.appendChild(dom.createTextNode(str(sale_status)))

            # stock　設定
            my_item_stock = dom.createElement("stock")
            my_register_item.appendChild(my_item_stock)
            my_item_stock.appendChild(dom.createTextNode(str(stock)))


            # 画像情報　設定

            for upd_image in images:
                my_images = dom.createElement("images")
                my_register_item.appendChild(my_images)

                my_image_url = dom.createElement("imageUrl")
                my_image_url.appendChild(dom.createTextNode(upd_image['imageUrl']))
                my_images.appendChild(my_image_url)

                my_image_name = dom.createElement("imageName")
                my_image_name.appendChild(dom.createTextNode(str(upd_image['imageName'])))
                my_images.appendChild(my_image_name)

                my_image_seq = dom.createElement("imageSeq")
                my_image_seq.appendChild(dom.createTextNode(str(upd_image['imageSeq'])))
                my_images.appendChild(my_image_seq)

            my_register_stock = dom.createElement("registerStock")
            request_dom.appendChild(my_register_stock)

            # 在庫区分　設定
            # 固定で 1:通常在庫 を設定
            my_item_stock_segment = dom.createElement("stockSegment")
            my_register_stock.appendChild(my_item_stock_segment)
            my_item_stock_segment.appendChild(dom.createTextNode("1"))

            # 在庫数 設定
            my_item_stock_count = dom.createElement("stockCount")
            my_register_stock.appendChild(my_item_stock_count)
            my_item_stock_count.appendChild(dom.createTextNode(str(stock)))

            #print(dom.toprettyxml(indent="  "))

            #params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info('qoo10_register_item_info response.status[' + str(response.status_code) + ']')
            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            #print('qoo10_register_item_info response.status[' + str(response.status_code) + ']')
            #print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('qoo10TestCall response[' + ET.parse(response.text) + ']')

            myrtn = document.getElementsByTagName("status")[0].firstChild.nodeValue # 0なら成功、1　失敗
            if myrtn == 1:
                self.logger.info('qoo10_register_item_info error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('qoo10_register_item_info code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('qoo10_register_item_info message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')


        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return myrtn

    # 商品在庫更新API
    def qoo10_update_stock(self,
                                 item_code, # itemCode
                                 stock_count, # stockCount 通常在庫数
                                 ):
        myrtn = 0
        try:
            self.logger.info('qoo10_update_stock in.')
            method = "updateStock"

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            my_stock_update_item = dom.createElement("stockUpdateItem")
            request_dom.appendChild(my_stock_update_item)

            # 商品コード　設定
            my_item_code = dom.createElement("itemCode")
            my_stock_update_item.appendChild(my_item_code)
            my_item_code.appendChild(dom.createTextNode(str(item_code)))

            # 在庫区分　設定
            my_stock_segment = dom.createElement("stockSegment")
            my_stock_update_item.appendChild(my_stock_segment)
            my_stock_segment.appendChild(dom.createTextNode("1"))

            # 通常在庫数　設定
            my_stock_count = dom.createElement("stockCount")
            my_stock_update_item.appendChild(my_stock_count)
            my_stock_count.appendChild(dom.createTextNode(str(stock_count)))


            #params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info('qoo10_update_stock response.status[' + str(response.status_code) + ']')
            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            #print('qoo10_update_stock response.status[' + str(response.status_code) + ']')
            #print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('qoo10TestCall response[' + ET.parse(response.text) + ']')
            myrtn = document.getElementsByTagName("status")[0].firstChild.nodeValue # 0なら成功、1　失敗
            if myrtn == 1:
                self.logger.info('qoo10_update_stock error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('qoo10_update_stock code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('qoo10_update_stock message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')


        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return myrtn


    # 価格更新API
    def qoo10_update_item_price(self,
                                 item_code, # itemCode
                                 item_price, # itemPrice 販売価格
                                 ):
        try:
            self.logger.info('qoo10_update_item_price in.')
            method = "updateItemPrice"

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            my_update_item_info = dom.createElement("updateItemInfo")
            request_dom.appendChild(my_update_item_info)

            # 商品コード　設定
            my_item_code = dom.createElement("itemCode")
            my_update_item_info.appendChild(my_item_code)
            my_item_code.appendChild(dom.createTextNode(str(item_code)))

            # 販売価格　設定
            my_item_price = dom.createElement("itemPrice")
            my_update_item_info.appendChild(my_item_price)
            my_item_price.appendChild(dom.createTextNode(str(item_price)))


            #params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            myrtn = document.getElementsByTagName("status")[0].firstChild.nodeValue # 0なら成功、1　失敗
            if myrtn == 1:
                self.logger.info('qoo10_update_item_price error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('qoo10_update_item_price code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('qoo10_update_item_price message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return myrtn

    # 受注番号取得API 注文者名などを特定した取得は別途。ここでは新規分など、注文ステータス、注文期間だけで絞る
    def qoo10_get_order_list(self, start_date, end_date, date_type, order_status_1, order_status_2):
        try:
            self.logger.info('qoo10_get_order_list in.')
            method = 'searchTradeNoListProc'
            params = {'shopId': self.shop_id, 'startDate': start_date, 'endDate': end_date, 'dateType': date_type,
                      'orderStatus': order_status_1, 'orderStatus2': order_status_2, 'totalCount': 1000}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('qoo10_get_order_detail response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            self.logger.info('qoo10_get_order_list end.')
            return document

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return False

    # 受注情報詳細取得API
    def qoo10_get_order_detail(self, order_id):
        try:
            self.logger.info('qoo10_get_order_detail in.')
            method = 'searchTradeInfoProc'
            params = {'shopId': self.shop_id, 'orderId': order_id}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('qoo10_get_order_detail response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('qoo10TestCall response[' + ET.parse(response.text) + ']')
            return document

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return False

    # 販売実績取得API
    def qoo10_search_sell_performance_status(self):
        try:
            self.logger.info('qoo10_search_sell_performance_status in.')
            method = 'searchSellPerformanceStatus'
            params = {'shopId': self.shop_id}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('qoo10_search_sell_performance_status response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('qoo10TestCall response[' + ET.parse(response.text) + ']')
            return

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return "none."

