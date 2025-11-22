# -*- coding:utf-8 -*-
import time
import sys, codecs
import io
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
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
import requests
from .gmail_access import GmailAccess

from yaget.models import WowmaShopInfo


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# requestsのlogger
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
my_rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/log/yaget_buyers_wowma_request.log',
    encoding='utf-8',
    maxBytes=1000000,
    backupCount=3
)
requests_log.addHandler(my_rh)

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/ya_buyers_list_logging.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

#logger.setLevel(20)

# 共通変数
mydwsrc_dir = "/app/yaget/yabuyers/dwsrc"
mydwimg_dir = "/app/yaget/yabuyers/dwimg/"
myupdcsv_dir = "/app/yaget/yabuyers/updcsv/"

def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class WowmaAccess(object):
    def __init__(self, logger):
        self.logger = logger
        help = 'wowma access'
        self.logger.info('wowma_access in. init')
        self.upd_csv = []

        # wowmaの登録してあるショップから、開店中のものだけ取得
        self.shop_obj_list = []
        shop_info_list = WowmaShopInfo.objects.filter(shop_status=1)
        for shop_info in shop_info_list:

            # リストに入れる
            self.shop_obj_list.append(WowmaAccessExec(self.logger, shop_info))


        # 以下は、WowmaAccessExec　に移植
        self.target_url = "https://api.manager.wowma.jp/wmshopapi/"  # 本番用
        #self.target_url = "https://sg.manager.wowma.jp/wmshopapi/" # テスト用

        self.api_key = "7803fca273b19a98802e023eaa2981e2161a25a033a32b3d01f172ee7ca9301b"  # 本番用 有効期限 2023/08/02
        #self.api_key = "fc7dfdacdcd6f08633f6df61cacce9fdd0f82498fcdcbf08d39365b0b21e722b"  # 本番用 有効期限 2022/9/30
        #self.api_key = "ded68c45eb7ae92196afd2b3f1cb09976a775dfd143720dee76af99edc831991" # 本番用 有効期限 2022/1/30

        self.shop_id = "58067114" # 本番用
        #self.shop_id = "393058" # テスト用
        self.get_headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-type': 'application/x-www-form-urlencoded',
            'charset': 'UTF-8',
        }
        self.post_headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-type': 'application/xml',
            'charset': 'UTF-8',
        }
        self.xml_template = "<request><shopId>" + self.shop_id + "</shopId></request>"
        #self.dom = md.parseString(self.xml_template)
        #self.request_dom = self.dom.getElementByTagName("request")

    # 受注情報一括取得API ここでは新規分など、注文ステータス、注文期間だけで絞る。ほんとはもっとパラメータ指定は可能
    def wowma_get_order_all_list(self, start_date, end_date, date_type, order_status_1, order_status_2):

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_obj = shop_obj.wowma_get_order_all_list(
                    start_date,
                    end_date,
                    date_type,
                    order_status_1,
                    order_status_2,
                )
                if res_obj:
                    ret_obj_list.append([shop_obj, res_obj])

        except Exception as e:
            raise
        return ret_obj_list

    # 受注ステータス更新API
    def wowma_update_trade_sts_proc(self, order_id, order_status):
        #self.logger.info('wowma_update_trade_sts_proc in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_code, res_msg = shop_obj.wowma_update_trade_sts_proc(
                    order_id,
                    order_status,
                )
                tmp_list = {
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        # self.logger.info('wowma_update_trade_sts_proc out')
        return ret_obj_list

    # 受注ステータス更新API
    def wowma_update_trade_info_proc(self, order_id, shipping_date, shipping_carrier, shipping_number):
        self.logger.info('wowma_update_trade_info_proc in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_code, res_msg = shop_obj.wowma_update_trade_info_proc(
                    order_id,
                    shipping_date,
                    shipping_carrier,
                    shipping_number,
                )
                tmp_list = {
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        self.logger.info('wowma_update_trade_info_proc out')
        return ret_obj_list

    # 受注番号取得API 注文者名などを特定した取得は別途。ここでは新規分など、注文ステータス、注文期間だけで絞る
    def wowma_get_order_list(
            self, start_date, end_date,
            date_type, order_status_1, order_status_2):

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_obj = shop_obj.wowma_get_order_list(
                    start_date,
                    end_date,
                    date_type,
                    order_status_1,
                    order_status_2,
                )
                if res_obj:
                    ret_obj_list.append(res_obj)

        except Exception as e:
            raise
        return ret_obj_list

    # 在庫更新更新API
    def wowma_update_stock(self, item_code, stock_count, sales_status):
        self.logger.info('wowma_update_stock in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_rtn, res_code, res_msg, res_lotnum, res_item_code =\
                    shop_obj.wowma_update_stock(
                        item_code,
                        stock_count,
                        sales_status,
                    )
                tmp_list = {
                    "res_rtn": res_rtn,
                    "res_code": res_code,
                    "res_msg": res_msg,
                    "res_lotnum": res_lotnum,
                    "res_item_code": res_item_code,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        self.logger.info('wowma_update_stock out')
        return ret_obj_list

    # 価格更新API
    def wowma_update_item_price(self,
                                item_code,  # itemCode
                                item_price,  # itemPrice 通常販売価格
                                item_fixed_price,  # itemPrice 固定販売価格
                                ):
        self.logger.info('wowma_update_item_price in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_rtn, res_code, res_msg = shop_obj.wowma_update_item_price(
                    item_code,
                    item_price,
                    item_fixed_price,
                )
                tmp_list = {
                    "res_rtn": res_rtn,
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        self.logger.info('wowma_update_item_price out')
        return ret_obj_list

    # 商品情報更新更新API
    def wowma_update_item_info(
        self,
        item_name,
        item_code,  # 商品コード
        item_gcode,  # 管理用商品コード
        item_price,  # 通常価格
        item_fixed_price,  # 優先価格
        postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
        postage,  # 個別送料
        delivery_method_id,  # 配送方法ID
        description,  # 商品説明
        category_id,  # カテゴリID
        keyword,  # 検索ワード
        tagid,  # 検索タグ
        sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
        stock,  # 在庫数
        images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
    ):
        self.logger.info('wowma_update_item_info in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_rtn, res_code, res_msg = shop_obj.wowma_update_item_info(
                    item_name,
                    item_code,  # 商品コード
                    item_gcode,  # 管理用商品コード
                    item_price,  # 通常価格
                    item_fixed_price,  # 優先価格
                    postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
                    postage,  # 個別送料
                    delivery_method_id,  # 配送方法ID
                    description,  # 商品説明
                    category_id,  # カテゴリID
                    keyword,  # 検索ワード
                    tagid,  # 検索タグ
                    sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
                    stock,  # 在庫数
                    images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                )
                self.logger.info('wowma_update_item_info rtn[{}] code[{}]'.format(res_rtn,res_code))
                tmp_list = {
                    "res_rtn": res_rtn,
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        self.logger.info('wowma_update_item_info out')
        self.logger.info('wowma_update_item_info ret_obj_list[{}]'.format(ret_obj_list))
        return ret_obj_list

    def wowma_register_item_info(
        self,
        item_name,
        item_code,
        item_gcode,
        item_price,  # 通常価格
        item_fixed_price,  # 優先価格
        postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
        postage,  # 個別送料
        delivery_method_id,  # 配送方法ID
        description,  # 商品説明
        category_id,  # カテゴリID
        keyword,  # 検索ワード
        tagid,  # 検索タグ
        sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
        stock,  # 在庫数
        images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
    ):
        self.logger.info('wowma_register_item_info in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_rtn, res_code, res_msg = shop_obj.wowma_register_item_info(
                    item_name,
                    item_code,
                    item_gcode,
                    item_price,  # 通常価格
                    item_fixed_price,  # 優先価格
                    postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
                    postage,  # 個別送料
                    delivery_method_id,  # 配送方法ID
                    description,  # 商品説明
                    category_id,  # カテゴリID
                    keyword,  # 検索ワード
                    tagid,  # 検索タグ
                    sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
                    stock,  # 在庫数
                    images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                )
                tmp_list = {
                    "res_rtn": res_rtn,
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            self.logger.info('wowma_register_item_info exp [{}]'.format(traceback.format_exc()))
            raise
        self.logger.info('wowma_register_item_info out')
        self.logger.info('wowma_register_item_info ret_obj_list[{}]'.format(ret_obj_list))
        return ret_obj_list

    def wowma_send_gmail_order_accept(self, order_id):
        self.logger.info('wowma_send_gmail_order_accept in')

        ret_obj_list = []
        try:
            for shop_obj in self.shop_obj_list:
                res_rtn, res_code, res_msg = shop_obj.wowma_send_gmail_order_accept_exec(
                    order_id
                )
                tmp_list = {
                    "res_rtn": res_rtn,
                    "res_code": res_code,
                    "res_msg": res_msg,
                }
                ret_obj_list.append(tmp_list)

        except Exception as e:
            raise
        self.logger.info('wowma_send_gmail_order_accept out')
        return ret_obj_list


# wowmaにリクエストする実体。こいつは
class WowmaAccessExec(object):
    """
    def __init__(self, logger):

        self.logger = logger
        self.requests_log = requests_log
        help = 'wowma access'
        self.logger.info('wowma_access_exec in. init 00_00')

        # 以下は、WowmaAccessExec　に移植
        self.target_url = "https://api.manager.wowma.jp/wmshopapi/" # 本番用
        #self.target_url = "https://sg.manager.wowma.jp/wmshopapi/" # テスト用
        self.api_key = "ded68c45eb7ae92196afd2b3f1cb09976a775dfd143720dee76af99edc831991" # 本番用 有効期限 2022/1/30
        #self.api_key = "c66998f4763579d3401721a3409c6b0d5ccf902c174f9e96411cfb2c3b758d2d"  # テスト用 有効期限 2022/1/30

        self.shop_id = "58067114" # 本番用
        #self.shop_id = "393058" # テスト用
        self.get_headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-type': 'application/x-www-form-urlencoded',
            'charset': 'UTF-8',
        }
        self.post_headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-type': 'application/xml',
            'charset': 'UTF-8',
        }
        self.xml_template = "<request><shopId>" + self.shop_id + "</shopId></request>"
    """

    def __init__(self, logger, shop_info):
        self.logger = logger
        self.requests_log = requests_log
        help = 'wowma access'
        self.logger.info('wowma_access_exec in. init 00')

        # 以下は、WowmaAccessExec　に移植
        self.target_url = shop_info.target_url
        #self.target_url = "https://api.manager.wowma.jp/wmshopapi/" # 本番用
        #self.target_url = "https://sg.manager.wowma.jp/wmshopapi/" # テスト用

        self.api_key = shop_info.api_key
        #self.api_key = "ded68c45eb7ae92196afd2b3f1cb09976a775dfd143720dee76af99edc831991" # 本番用 有効期限 2022/1/30
        #self.api_key = "c66998f4763579d3401721a3409c6b0d5ccf902c174f9e96411cfb2c3b758d2d"  # テスト用 有効期限 2022/1/30

        self.shop_id = shop_info.shop_id
        #self.shop_id = "58067114" # 本番用
        #self.shop_id = "393058" # テスト用

        self.get_headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-type': 'application/x-www-form-urlencoded',
            'charset': 'UTF-8',
        }
        self.post_headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-type': 'application/xml',
            'charset': 'UTF-8',
        }
        self.xml_template = "<request><shopId>" + str(self.shop_id) + "</shopId></request>"

    # 商品情報登録API
    def wowma_register_item_info(
        self,
        item_name,
        item_code,
        item_gcode,
        item_price,  # 通常価格
        item_fixed_price,  # 優先価格
        postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
        postage,  # 個別送料
        delivery_method_id,  # 配送方法ID
        description,  # 商品説明
        category_id,  # カテゴリID
        keyword,  # 検索ワード
        tagid,  # 検索タグ
        sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
        stock,  # 在庫数
        images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
    ):
        myrtn = 0
        mycode = ''
        mymsg = ''
        try:
            self.logger.info('wowma_register_item_info in.')
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

            # 商品コード（管理用）　設定
            my_item_gcode = dom.createElement("itemManagementName")
            my_register_item.appendChild(my_item_gcode)
            my_item_gcode.appendChild(dom.createTextNode(str(item_gcode)))

            # 商品価格　設定
            my_item_price = dom.createElement("itemPrice")
            my_register_item.appendChild(my_item_price)
            # 優先価格が指定されていたらそれを登録。なければ通常価格を
            if int(item_fixed_price) > 0:
                my_item_price.appendChild(dom.createTextNode(str(item_fixed_price)))
            else:
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

            # 商品詳細　設定 (descriptionは短いのでタイトルを仮に格納。PC,SP用それぞれに商品説明を格納）
            my_item_description = dom.createElement("description")
            my_register_item.appendChild(my_item_description)
            my_item_description.appendChild(dom.createTextNode(item_name))

            my_item_description_pc = dom.createElement("descriptionForPC")
            my_register_item.appendChild(my_item_description_pc)
            my_item_description_pc.appendChild(dom.createTextNode(description))

            my_item_description_sp = dom.createElement("descriptionForSP")
            my_register_item.appendChild(my_item_description_sp)
            my_item_description_sp.appendChild(dom.createTextNode(description))

            # categoryId　設定
            my_item_category_id = dom.createElement("categoryId")
            my_register_item.appendChild(my_item_category_id)
            my_item_category_id.appendChild(dom.createTextNode(str(category_id)))

            # 検索キーワード
            tmp_list_keyword = keyword.split(" ")

            self.logger.info('wowma_register_item_info keyword.[{}] len[{}]'.format(keyword, len(tmp_list_keyword)))

            my_cnt = 1
            for tmp_i, tmp_keyword in enumerate(tmp_list_keyword):
                # if tmp_i == 3:
                if my_cnt == 4:
                    break
                if tmp_keyword == '':
                    continue
                my_keywords = dom.createElement("searchKeywords")
                my_register_item.appendChild(my_keywords)

                my_keyword = dom.createElement("searchKeyword")
                my_keyword.appendChild(dom.createTextNode(str(tmp_keyword)))
                my_keywords.appendChild(my_keyword)

                my_keyword_seq = dom.createElement("searchKeywordSeq")
                # my_keyword_seq.appendChild(dom.createTextNode(str(tmp_i + 1)))
                my_keyword_seq.appendChild(dom.createTextNode(str(my_cnt)))
                my_keywords.appendChild(my_keyword_seq)
                self.logger.info('wowma_register_item_info tmp_keyword.[{}] seq[{}]'.format(tmp_keyword, str(tmp_i + 1)))
                my_cnt += 1

            # 検索タグ
            self.logger.info('wowma_register_item_info 1_1.')
            self.logger.info('wowma_register_item_info tagid.[{}] len[{}]'.format(tagid, len(str(tagid))))
            if tagid and str(tagid) != '':
                if len(str(tagid)) > 0:
                    tmp_list_tagid = tagid.split(" ")
                    if tmp_list_tagid:
                        # self.logger.info('wowma_update_item_info 1_2.')
                        for tmp_tagid in tmp_list_tagid:
                            # self.logger.info('wowma_update_item_info 1_3.')
                            my_tags = dom.createElement("tags")
                            my_register_item.appendChild(my_tags)

                            my_tagid = dom.createElement("tagId")
                            my_tagid.appendChild(dom.createTextNode(str(tmp_tagid)))
                            my_tags.appendChild(my_tagid)

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

            # print(dom.toprettyxml(indent="  "))

            # params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info('wowma_register_item_info response.status[' + str(response.status_code) + ']')
            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            # print('wowma_register_item_info response.status[' + str(response.status_code) + ']')
            # print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            # print('WowmaTestCall response[' + ET.parse(response.text) + ']')

            myrtn = document.getElementsByTagName("status")[0].firstChild.nodeValue  # 0なら成功、1　失敗
            self.logger.info('wowma_register_item_info myrtn[' + str(myrtn) + ']')
            if int(myrtn) == 0:
                # 成功したらlotNumberとitemCodeが取れてるはず。エラー時の、code とmessageは含まれない
                mycode = str(document.getElementsByTagName("lotNumber")[0].firstChild.nodeValue)
                mymsg = str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue)
            else:
                self.logger.info('wowma_register_item_info error. code:[{}]'.format(mycode))
                self.logger.info('wowma_register_item_info message:[{}]'.format(mymsg))
                mycode = str(document.getElementsByTagName("code")[0].firstChild.nodeValue)
                # codeが２つ以上返ってくる場合がある
                mycode_2 = ''
                if len(document.getElementsByTagName("code")) > 1:
                    mycode_2 = str(document.getElementsByTagName("code")[1].firstChild.nodeValue)
                mymsg = str(document.getElementsByTagName("message")[0].firstChild.nodeValue)

                # 既に登録済みだったら、wowmaのロットナンバーを取りに行って更新をかける wow_lotnum
                if mycode == "PME0106" or mycode_2 == "PME0106":
                    myrtn, mycode, mymsg = self.wowma_update_item_info(
                        item_name,
                        item_code,
                        item_gcode,
                        item_price,  # 通常価格
                        item_fixed_price,  # 優先価格
                        postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
                        postage,  # 個別送料
                        delivery_method_id,  # 配送方法ID
                        description,  # 商品説明
                        category_id,  # カテゴリID
                        keyword,  # 検索ワード
                        tagid,  # 検索タグ
                        sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
                        stock,  # 在庫数
                        images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                    )

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return 1, mycode, traceback.format_exc()

        return myrtn, mycode, mymsg

    # 商品情報更新API
    def wowma_update_item_info(
        self,
        item_name,
        item_code,  # 商品コード
        item_gcode,  # 管理用商品コード
        item_price,  # 通常価格
        item_fixed_price,  # 優先価格
        postage_segment,  # 送料設定区分 1:送料別/2:送料込み/3:個別送料
        postage,  # 個別送料
        delivery_method_id,  # 配送方法ID
        description,  # 商品説明
        category_id,  # カテゴリID
        keyword,  # 検索ワード
        tagid,  # 検索タグ
        sale_status,  # 販売ステータス 1:販売中/2:販売終了商品
        stock,  # 在庫数
        images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
    ):
        myrtn = 0
        mycode = ''
        mymsg = ''
        try:
            self.logger.info('wowma_update_item_info in.')
            method = "updateItemInfo"

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            my_register_item = dom.createElement("updateItem")
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
            # 優先価格が指定されていたらそれを登録。なければ通常価格を
            if int(item_fixed_price) > 0:
                my_item_price.appendChild(dom.createTextNode(str(item_fixed_price)))
            else:
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

            # 商品詳細　設定 (descriptionは短いのでタイトルを仮に格納。PC,SP用それぞれに商品説明を格納）
            my_item_description = dom.createElement("description")
            my_register_item.appendChild(my_item_description)
            my_item_description.appendChild(dom.createTextNode(item_name))

            my_item_description_pc = dom.createElement("descriptionForPC")
            my_register_item.appendChild(my_item_description_pc)
            my_item_description_pc.appendChild(dom.createTextNode(description))

            my_item_description_sp = dom.createElement("descriptionForSP")
            my_register_item.appendChild(my_item_description_sp)
            my_item_description_sp.appendChild(dom.createTextNode(description))

            # categoryId　設定
            my_item_category_id = dom.createElement("categoryId")
            my_register_item.appendChild(my_item_category_id)
            my_item_category_id.appendChild(dom.createTextNode(str(category_id)))

            # 検索キーワード
            tmp_list_keyword = keyword.split(" ")

            for tmp_i, tmp_keyword in enumerate(tmp_list_keyword):
                if tmp_i == 3:
                    break
                my_keywords = dom.createElement("searchKeywords")
                my_register_item.appendChild(my_keywords)

                my_keyword = dom.createElement("searchKeyword")
                my_keyword.appendChild(dom.createTextNode(str(tmp_keyword)))
                my_keywords.appendChild(my_keyword)

                my_keyword_seq = dom.createElement("searchKeywordSeq")
                my_keyword_seq.appendChild(dom.createTextNode(str(tmp_i + 1)))
                my_keywords.appendChild(my_keyword_seq)

            # 検索タグ
            self.logger.info('wowma_update_item_info 1_1.')
            self.logger.info('wowma_update_item_info tagid.[{}] len[{}]'.format(tagid, len(str(tagid))))
            if tagid and str(tagid) != '':
                if len(str(tagid)) > 0:
                    tmp_list_tagid = tagid.split(" ")
                    if tmp_list_tagid:
                        self.logger.info('wowma_update_item_info 1_2.')
                        for tmp_tagid in tmp_list_tagid:
                            self.logger.info('wowma_update_item_info 1_3.')
                            my_tags = dom.createElement("tags")
                            my_register_item.appendChild(my_tags)

                            my_tagid = dom.createElement("tagId")
                            my_tagid.appendChild(dom.createTextNode(str(tmp_tagid)))
                            my_tags.appendChild(my_tagid)
            """
            else:
                # tag指定がなければカラ登録しとかないといけない
                for i in range(64):
                    my_tags = dom.createElement("tags")
                    my_register_item.appendChild(my_tags)

                    my_tagid = dom.createElement("tagId")
                    my_tagid.appendChild(dom.createTextNode(''))
                    my_tags.appendChild(my_tagid)
            """

            # saleStatus設定
            my_item_sale_status = dom.createElement("saleStatus")
            my_register_item.appendChild(my_item_sale_status)
            my_item_sale_status.appendChild(dom.createTextNode(str(sale_status)))

            # stock設定
            my_item_stock = dom.createElement("stock")
            my_register_item.appendChild(my_item_stock)
            my_item_stock.appendChild(dom.createTextNode(str(stock)))

            # 画像情報設定

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
            #self.logger.info('send_xml:[{}]'.format(dom.toprettyxml(indent="  ")))

            #params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info('wowma_update_item_info response.status[' + str(response.status_code) + ']')
            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            #print('wowma_register_item_info response.status[' + str(response.status_code) + ']')
            #print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('WowmaTestCall response[' + ET.parse(response.text) + ']')

            myrtn = str(document.getElementsByTagName("status")[0].firstChild.nodeValue) # 0なら成功、1　失敗
            if myrtn == '1':
                self.logger.info('wowma_update_item_info error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_update_item_info code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                mycode = str(document.getElementsByTagName("code")[0].firstChild.nodeValue)
                self.logger.info('wowma_update_item_info message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                mymsg = str(document.getElementsByTagName("message")[0].firstChild.nodeValue)
            elif myrtn == '0':  # 正常終了
                # lotNumberをcodeにセットして返却する
                mycode = str(document.getElementsByTagName("lotNumber")[0].firstChild.nodeValue)


        except Exception as e:
            self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return 1, mycode, traceback.format_exc()

        self.logger.info('wowma_update_item_info out.')
        return myrtn, mycode, mymsg

    # 商品情報取得API
    def wowma_search_item_info(self,
                               item_code,  # 商品コード
                               wow_lotnum,  # ロットナンバー
                               ):
        mycode = ''
        mymsg = ''
        try:
            self.logger.info('wowma_search_item_info in.')
            method = "searchItemInfo"

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            # 商品コードかロットナンバーを必ず指定
            if item_code:
                my_search_cd = dom.createElement("itemCode")
                my_search_cd.appendChild(dom.createTextNode(item_code))
            else:
                my_search_cd = dom.createElement("lotNumber")
                my_search_cd.appendChild(dom.createTextNode(str(wow_lotnum)))
            request_dom.appendChild(my_search_cd)

            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info('wowma_search_item_info response.status[' + str(response.status_code) + ']')
            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            myrtn = str(document.getElementsByTagName("status")[0].firstChild.nodeValue)  # 0なら成功、1　失敗
            if myrtn == '1':
                self.logger.info('wowma_search_item_info error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_search_item_info code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                mycode = str(document.getElementsByTagName("code")[0].firstChild.nodeValue)
                self.logger.info('wowma_search_item_info message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                mymsg = str(document.getElementsByTagName("message")[0].firstChild.nodeValue)
            elif myrtn == '0':  # 正常終了
                # lotNumberをcodeにセットして返却する
                # かつ、諸々とれた情報はセットして返したいが・・ひとまず lotNumberだけでもいい
                mycode = str(document.getElementsByTagName("lotNumber")[0].firstChild.nodeValue)

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return 1, mycode, traceback.format_exc()

        self.logger.info('wowma_search_item_info out.')
        return myrtn, mycode, mymsg

    # 商品在庫更新API
    def wowma_update_stock(self, item_code, stock_count, sales_status):
        myrtn = 0
        mycode = ''
        mymsg = ''
        my_lotnum = 0
        my_item_code_rtn = 0
        try:
            self.logger.info('wowma_update_stock in.')
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

            # 販売ステータス　設定　在庫が0なら、2:販売終了商品　に。1以上なら 1:販売中商品に
            my_sales_status = dom.createElement("saleStatus")
            my_stock_update_item.appendChild(my_sales_status)
            my_sales_status.appendChild(dom.createTextNode(sales_status))
            """
            if stock_count == 0:  # 2:販売終了商品　に
                my_sales_status.appendChild(dom.createTextNode('2'))
            else:  # 1:販売中商品　に
                my_sales_status.appendChild(dom.createTextNode('1'))
            """

            #params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info('wowma_update_stock response.status[' + str(response.status_code) + ']')
            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            #print('wowma_update_stock response.status[' + str(response.status_code) + ']')
            #print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('WowmaTestCall response[' + ET.parse(response.text) + ']')
            myrtn = int(document.getElementsByTagName("status")[0].firstChild.nodeValue)  # 0なら成功、1　失敗
            self.logger.info('wowma_update_stock myrtn[' + str(myrtn) + ']')
            if myrtn == 1:
                self.logger.info('wowma_update_stock error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_update_stock code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                mycode = str(document.getElementsByTagName("code")[0].firstChild.nodeValue)
                self.logger.info('wowma_update_stock message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                mymsg = str(document.getElementsByTagName("message")[0].firstChild.nodeValue)
            else:
                # 成功（return=0）の場合
                my_lotnum = int(document.getElementsByTagName("lotNumber")[0].firstChild.nodeValue)
                my_item_code_rtn = int(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue)

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return 1, mycode, traceback.format_exc(), my_lotnum, my_item_code_rtn

        return myrtn, mycode, mymsg, my_lotnum, my_item_code_rtn

    # 価格更新API
    def wowma_update_item_price(
        self,
        item_code,  # itemCode
        item_price,  # itemPrice 通常販売価格
        item_fixed_price,  # itemPrice 固定販売価格
    ):
        mycode = ''
        mymsg = ''
        my_lotnum = 0
        my_item_code_rtn = 0
        try:
            self.logger.info('wowma_update_item_price in.')
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

            # 優先価格が指定されていたらそれを登録。なければ通常価格を
            if int(item_fixed_price) > 0:
                my_item_price.appendChild(dom.createTextNode(str(item_fixed_price)))
            else:
                my_item_price.appendChild(dom.createTextNode(str(item_price)))

            # params = {'shopId': '58067114'}
            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            myrtn = int(document.getElementsByTagName("status")[0].firstChild.nodeValue) # 0なら成功、1　失敗
            if myrtn == 1:
                self.logger.info('wowma_update_item_price error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_update_item_price code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_update_item_price message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                mycode = str(document.getElementsByTagName("code")[0].firstChild.nodeValue)
                mymsg = str(document.getElementsByTagName("message")[0].firstChild.nodeValue)
            else:
                # 成功（return=0）の場合
                my_lotnum = int(document.getElementsByTagName("lotNumber")[0].firstChild.nodeValue)
                my_item_code_rtn = int(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue)

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return 1, mycode, traceback.format_exc(), my_lotnum, my_item_code_rtn

        return myrtn, mycode, mymsg, my_lotnum, my_item_code_rtn

    # 商品削除API
    def wowma_delete_item_infos(
        self,
        item_code,  # itemCode
    ):
        try:
            self.logger.info('wowma_delete_item_infos in.')
            method = "deleteItemInfos"
            ret_msg = ""

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            my_update_item_info = dom.createElement("deleteItemInfo")
            request_dom.appendChild(my_update_item_info)

            # 商品コード　設定
            my_item_code = dom.createElement("itemCode")
            my_update_item_info.appendChild(my_item_code)
            my_item_code.appendChild(dom.createTextNode(str(item_code)))

            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url+method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            self.logger.info(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            myrtn = int(document.getElementsByTagName("status")[0].firstChild.nodeValue) # 0なら成功、1　失敗
            if myrtn == 1:
                self.logger.info('wowma_delete_item_infos error occurred itemcd:[' \
                                 + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_delete_item_infos code:[' \
                                 + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + ']')
                self.logger.info('wowma_delete_item_infos message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                ret_msg = '[' + str(document.getElementsByTagName("itemCode")[0].firstChild.nodeValue) + '][' \
                    + str(document.getElementsByTagName("code")[0].firstChild.nodeValue) + '][' \
                    + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']'

        except Exception as e:
            self.logger.info(traceback.format_exc())
            print(traceback.format_exc())
            ret_msg = traceback.format_exc()
            return False, ret_msg

        self.logger.info('wowma_delete_item_infos out.')
        return myrtn, ret_msg

    # 受注情報一括取得API ここでは新規分など、注文ステータス、注文期間だけで絞る。ほんとはもっとパラメータ指定は可能
    def wowma_get_order_all_list(
        self, start_date, end_date,
        date_type, order_status_1, order_status_2
    ):
        try:
            self.logger.info('wowma_get_order_all_list in.')
            method = 'searchTradeInfoListProc'
            params = {'shopId': self.shop_id, 'startDate': start_date, 'endDate': end_date, 'dateType': date_type,
                      'orderStatus': order_status_1, 'orderStatus2': order_status_2, 'totalCount': 1000}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('wowma_get_order_all_list response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            self.logger.info('wowma_get_order_all_list doc[{}]'.format(document))
            self.logger.info('wowma_get_order_all_list end.')
            return document

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return False

    # 受注番号取得API 注文者名などを特定した取得は別途。ここでは新規分など、注文ステータス、注文期間だけで絞る
    def wowma_get_order_list(self, start_date, end_date, date_type, order_status_1, order_status_2):
        try:
            self.logger.info('wowma_get_order_list in.')
            method = 'searchTradeNoListProc'
            params = {'shopId': self.shop_id, 'startDate': start_date, 'endDate': end_date, 'dateType': date_type,
                      'orderStatus': order_status_1, 'orderStatus2': order_status_2, 'totalCount': 1000}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('wowma_get_order_detail response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            self.logger.info('wowma_get_order_list end.')
            return document

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return False

    # 受注情報詳細取得API
    def wowma_get_order_detail(self, order_id):
        try:
            self.logger.info('wowma_get_order_detail in.')
            method = 'searchTradeInfoProc'
            params = {'shopId': self.shop_id, 'orderId': order_id}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('wowma_get_order_detail response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('WowmaTestCall response[' + ET.parse(response.text) + ']')
            return document

        except Exception as e:
            #self.logger.debug(traceback.format_exc())
            print(traceback.format_exc())
            return False

        return False

    # 受注ステータス更新API
    """
    新規受付
    新規予約
    予約中
    発送前入金待ち
    与信待ち
    発送待ち
    発送後入金待ち
    完了
    保留
    """
    def wowma_update_trade_sts_proc(self, order_id, order_status):
        try:
            self.logger.info('wowma_update_trade_sts_proc in.')
            method = 'updateTradeStsProc'
            ret_msg = ''
            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            # 受注ステータス　設定
            my_order_id = dom.createElement("orderId")
            request_dom.appendChild(my_order_id)
            my_order_id.appendChild(dom.createTextNode(str(order_id)))

            # 受注ステータス　設定
            my_order_status = dom.createElement("orderStatus")
            request_dom.appendChild(my_order_status)
            my_order_status.appendChild(dom.createTextNode(str(order_status)))

            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url + method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース
            self.logger.debug(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            myrtn = int(document.getElementsByTagName("status")[0].firstChild.nodeValue)  # 0なら成功、1　失敗
            if myrtn != 0:
                self.logger.debug('wowma_update_trade_sts_proc rtn[{}]'.format(myrtn))
                self.logger.debug('wowma_update_trade_sts_proc message:[' \
                                 + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                ret_msg = '[' + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']'

        except Exception as e:
            self.logger.info(traceback.format_exc())
            print(traceback.format_exc())
            ret_msg = traceback.format_exc()
            return False, ret_msg

        self.logger.info('wowma_update_trade_sts_proc out.')
        ret_msg = 'ok [{}]'.format(order_id)
        return myrtn, ret_msg

    # 受注情報個別更新API
    def wowma_update_trade_info_proc(self, order_id, shipping_date, shipping_carrier, shipping_number):
        try:
            self.logger.info('wowma_update_trade_info_proc in.')
            ret_msg = ''
            method = 'updateTradeInfoProc'
            #params = {'shopId': self.shop_id, 'orderId': order_id, 'shippingDate': shipping_date,
            #          'shippingCarrier': shipping_carrier,'shippingNumber': shipping_number}

            # xmlを生成
            dom = md.parseString(self.xml_template)
            request_dom = dom.getElementsByTagName("request")[0]

            # 受注ステータス　設定
            my_order_id = dom.createElement("orderId")
            request_dom.appendChild(my_order_id)
            my_order_id.appendChild(dom.createTextNode(str(order_id)))

            # 発送日　設定
            my_shipping_date = dom.createElement("shippingDate")
            request_dom.appendChild(my_shipping_date)
            my_shipping_date.appendChild(dom.createTextNode(shipping_date))

            # 発送キャリア　設定
            my_shipping_carrier = dom.createElement("shippingCarrier")
            request_dom.appendChild(my_shipping_carrier)
            my_shipping_carrier.appendChild(dom.createTextNode(shipping_carrier))

            # 追跡番号　設定
            my_shipping_number = dom.createElement("shippingNumber")
            request_dom.appendChild(my_shipping_number)
            my_shipping_number.appendChild(dom.createTextNode(str(shipping_number)))

            params = dom.toprettyxml().encode("utf-8")
            response = requests.post(self.target_url + method, headers=self.post_headers, data=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース
            self.logger.debug(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示

            myrtn = int(document.getElementsByTagName("status")[0].firstChild.nodeValue)  # 0なら成功、1　失敗
            if myrtn != 0:
                self.logger.debug('wowma_update_trade_info_proc rtn[{}]'.format(myrtn))
                self.logger.debug('wowma_update_trade_info_proc message:[' \
                                  + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']')
                ret_msg = '[' + str(document.getElementsByTagName("message")[0].firstChild.nodeValue) + ']'

        except Exception as e:
            self.logger.info(traceback.format_exc())
            print(traceback.format_exc())
            ret_msg = traceback.format_exc()
            return False, ret_msg

        self.logger.info('wowma_update_trade_info_proc out.')
        ret_msg = 'ok [{}]'.format(order_id)
        return myrtn, ret_msg

    # 販売実績取得API
    def wowma_search_sell_performance_status(self):
        try:
            self.logger.info('wowma_search_sell_performance_status in.')
            method = 'searchSellPerformanceStatus'
            params = {'shopId': self.shop_id}
            response = requests.get(self.target_url + method, headers=self.get_headers, params=params)
            root = ET.fromstring(response.text)
            document = md.parseString(ET.tostring(root, 'utf-8'))  # minidomモジュールが XML Elementをパース

            print('wowma_search_sell_performance_status response.status[' + str(response.status_code) + ']')
            print(document.toprettyxml(indent="  "))  # パースされたXML情報をインデント付きで文字列に変換して表示
            #print('WowmaTestCall response[' + ET.parse(response.text) + ']')
            return

        except Exception as e:
            self.logger.info(traceback.format_exc())
            #print(traceback.format_exc())
            return False

        return "none."

    def wowma_send_gmail_order_accept_exec(self, order_id):
        self.logger.info('wowma_send_gmail_order_accept_exec in')
        myrtn = 0
        ret_msg = ''
        try:
            gmail = GmailAccess()
            if not gmail.exec_send_mail(self, sender, to, subject, message):
                self.logger.info('wowma_send_gmail_order_accept_exec fail.[{}]'.format(traceback.format_exc()))

        except :
            raise
        self.logger.info('wowma_send_gmail_order_accept_exec out')
        return myrtn, ret_msg
