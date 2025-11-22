# coding: utf-8
import base64
from django.shortcuts import render
from django.http import HttpResponse
import sys, io, six
import datetime
import sqlite3
from contextlib import closing
import re
import json
from time import sleep
import lxml.html

import hashlib
from hashlib import sha256
from base64 import b64encode

from oauth2client.service_account import ServiceAccountCredentials
import time
import hmac
import logging
import xml.etree.ElementTree as ET
import urllib.parse
import urllib.request
import requests
import sys
import linecache
import traceback
import os

from yaget.integrations.chrome_driver import CommonChromeDriver

from sp_api.api import Feeds
from sp_api.api import Sellers, Catalog, Products, CatalogItems
from sp_api.base.marketplaces import Marketplaces

# こちらは python-amazon-sp-api を組み込んでみる版

"""
参考にしたサイト
★SP-API　API一覧
https://github.com/jlevers/selling-partner-api/tree/main/docs/Api

★これ組み込むほうが早いかも
pip install python-amazon-sp-api
https://sp-api-docs.saleweaver.com/endpoints/catalog/

こんな感じで使えそう
https://www.shinkainoblog.com/programing/amazon-selling-partner-api%E3%81%AE%E3%83%A1%E3%83%A2/#toc6




SP-APIのドキュメント（公式）
https://developer.amazonservices.jp/

日本語のgit hub　ドキュメント
https://github.com/amzn/selling-partner-api-docs/tree/main/guides/ja-JP

★デベロッパー向け
https://github.com/amzn/selling-partner-api-docs/blob/main/guides/ja-JP/developer-guide/SellingPartnerApiDeveloperGuide(%E6%97%A5%E6%9C%AC%E8%AA%9E).md

SP-APIの準備
https://zats-firm.com/2021/09/07/amazon-mws-%e3%81%8b%e3%82%89-sp-api-%e3%81%b8%e3%81%ae%e7%a7%bb%e8%a1%8c-%e6%ba%96%e5%82%99%e7%b7%a8/#AWS_IAM

PYTHONでたたく
https://zats-firm.com/2021/09/09/amazon-mws-%e3%81%8b%e3%82%89-sp-api-%e3%81%b8%e3%81%ae%e7%a7%bb%e8%a1%8c-python%e3%81%a7sp-api%e3%82%92%e3%81%9f%e3%81%9f%e3%81%8f%e7%b7%a8/


"""

# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import (
    YaAmaGoodsDetail,
    YaShopAmaGoodsDetail,
    YaShopImportAmaGoodsDetail,
    YaItemList,
    YaShopImportSpApiAmaGoodsDetail,
    AsinDetail,
    QooAsinDetail,
    QooAsinRelationDetail,
    AsinBlacklistAsin,
    AsinBlacklistKeyword,
    AsinBlacklistBrand,
    WowmaGoodsDetail,
)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# reload(sys)
# sys.setdefaultencoding('utf-8')
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# listmatchingproductsについてこちら
# https://lets-hack.tech/programming/languages/python/mws/

# 共通設定
dbname = '/app/amget/amget.sqlite3'
# スクレイピング時のchromeデータ保持領域
USER_DATA_DIR = '/app/yaget/userdata/'


AMAZON_CREDENTIAL = {
    # 環境変数から取得（未設定なら空文字）
    'SELLER_ID':      os.getenv('AWS_SELLER_ID', ''),
    'ACCESS_KEY_ID':  os.getenv('AWS_ACCESS_KEY_ID', ''),
    'ACCESS_SECRET':  os.getenv('AWS_SECRET_ACCESS_KEY', ''),}

MARKETPLACES = {
  "CA": ("https://mws.amazonservices.ca", "A2EUQ1WTGCTBG2"),
  "US": ("https://mws.amazonservices.com", "ATVPDKIKX0DER"),
  "DE": ("https://mws-eu.amazonservices.com", "A1PA6795UKMFR9"),
  "ES": ("https://mws-eu.amazonservices.com", "A1RKKUPIHCS9HS"),
  "FR": ("https://mws-eu.amazonservices.com", "A13V1IB3VIYZZH"),
  "IN": ("https://mws.amazonservices.in", "A21TJRUUN4KGV"),
  "IT": ("https://mws-eu.amazonservices.com", "APJ6JRA9NG5V4"),
  "UK": ("https://mws-eu.amazonservices.com", "A1F83G8C2ARO7P"),
  "JP": ("https://mws.amazonservices.jp", "A1VC38T7YXB528"),
  "CN": ("https://mws.amazonservices.com.cn", "AAHKV2X7AFYLW"),
  "MX": ("https://mws.amazonservices.com.mx", "A1AM78C64UM0Y8")
}

DOMAIN = 'mws.amazonservices.jp'
ORDERENDPOINT = '/Orders/2013-09-01'

ENDPOINT = '/Products/2011-10-01'


PRODUCTSENDPOINT = '/Products/2011-10-01'

ORDERSNS = {
  "2013-09-01": "https://mws.amazonservices.com/Orders/2013-09-01"
}

PRODUCTSNS = {
  "2011-10-01":"https://mws.amazonservices.com/schema/Products/2011-10-01"
}

class MWSError(Exception):
  pass

def failure(e):
    exc_type, exc_obj, tb=sys.exc_info()
    lineno=tb.tb_lineno
    return str(lineno) + ":" + str(type(e))

def datetime_encode(dt):
  return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def find_orders_by_obj(myobj, element):
  return myobj.find(".//2013-09-01:%s" % element, ORDERSNS)


def set_order(myc, myorder):
  myAmazonOrderId = find_orders_by_obj(myorder, 'AmazonOrderId')
  myAmazonOrderIdval = ' '
  if (myAmazonOrderId is not None):
      myAmazonOrderIdval = myAmazonOrderId.text
  myPurchaseDate = find_orders_by_obj(myorder, 'PurchaseDate')
  myPurchaseDateval = None
  if (myPurchaseDate is not None):
      myPurchaseDateval = myPurchaseDate.text
  myLastUpdateDate = find_orders_by_obj(myorder, 'LastUpdateDate')
  myLastUpdateDateval = None
  if (myLastUpdateDate is not None):
      myLastUpdateDateval = myLastUpdateDate.text
  myFulfillmentChannel = find_orders_by_obj(myorder, 'FulfillmentChannel')
  myFulfillmentChannelval = None
  if (myFulfillmentChannel is not None):
      myFulfillmentChannelval = myFulfillmentChannel.text

  myShippingAddress = find_orders_by_obj(myorder, 'ShippingAddress')
  if (myShippingAddress is not None):
      myShippingAddressName = find_orders_by_obj(myShippingAddress, 'Name')
      myShippingAddressNameval = None
      if (myShippingAddressName is not None):
          myShippingAddressNameval = myShippingAddressName.text
      myShippingAddressAddressLine1 = find_orders_by_obj(myShippingAddress, 'AddressLine1')
      myShippingAddressAddressLine1val = None
      if (myShippingAddressAddressLine1 is not None):
          myShippingAddressAddressLine1val = myShippingAddressAddressLine1.text
      myShippingAddressAddressLine2 = find_orders_by_obj(myShippingAddress, 'AddressLine2')
      myShippingAddressAddressLine2val = None
      if (myShippingAddressAddressLine2 is not None):
          myShippingAddressAddressLine2val = myShippingAddressAddressLine2.text
      myShippingAddressAddressLine3 = find_orders_by_obj(myShippingAddress, 'AddressLine3')
      myShippingAddressAddressLine3val = None
      if (myShippingAddressAddressLine3 is not None):
          myShippingAddressAddressLine3val = myShippingAddressAddressLine3.text
      myShippingAddressCity = find_orders_by_obj(myShippingAddress, 'City')
      myShippingAddressCityval = None
      if (myShippingAddressCity is not None):
          myShippingAddressCityval = myShippingAddressCity.text
      myShippingAddressCounty = find_orders_by_obj(myShippingAddress, 'County')
      myShippingAddressCountyval = None
      if (myShippingAddressCounty is not None):
          myShippingAddressCountyval = myShippingAddressCounty.text
      myShippingAddressDistrict = find_orders_by_obj(myShippingAddress, 'District')
      myShippingAddressDistrictval = None
      if (myShippingAddressDistrict is not None):
          myShippingAddressDistrictval = myShippingAddressDistrict.text
      myShippingAddressStateOrRegion = find_orders_by_obj(myShippingAddress, 'StateOrRegion')
      myShippingAddressStateOrRegionval = None
      if (myShippingAddressStateOrRegion is not None):
          myShippingAddressStateOrRegionval = myShippingAddressStateOrRegion.text
      myShippingAddressPostalCode = find_orders_by_obj(myShippingAddress, 'PostalCode')
      myShippingAddressPostalCodeval = None
      if (myShippingAddressPostalCode is not None):
          myShippingAddressPostalCodeval = myShippingAddressPostalCode.text
      myShippingAddressCountryCode = find_orders_by_obj(myShippingAddress, 'CountryCode')
      myShippingAddressCountryCodeval = None
      if (myShippingAddressCountryCode is not None):
          myShippingAddressCountryCodeval = myShippingAddressCountryCode.text
      myShippingAddressPhone = find_orders_by_obj(myShippingAddress, 'Phone')
      myShippingAddressPhoneval = None
      if (myShippingAddressPhone is not None):
          myShippingAddressPhoneval = myShippingAddressPhone.text
      myShippingAddressAddressType = find_orders_by_obj(myShippingAddress, 'AddressType')
      myShippingAddressAddressTypeval = None
      if (myShippingAddressAddressType is not None):
          myShippingAddressAddressTypeval = myShippingAddressAddressType.text

  mySalesChannel = find_orders_by_obj(myorder, 'SalesChannel')
  mySalesChannelval = None
  if (mySalesChannel is not None):
      mySalesChannelval = mySalesChannel.text
  myShipServiceLevel = find_orders_by_obj(myorder, 'ShipServiceLevel')
  myShipServiceLevelval = None
  if (myShipServiceLevel is not None):
      myShipServiceLevelval = myShipServiceLevel.text
  myPofileFieldsval = None

  myOrderTotal = find_orders_by_obj(myorder, 'OrderTotal')
  if (myOrderTotal is not None):
      myOrderCurrencycode = find_orders_by_obj(myOrderTotal, 'CurrencyCode')
      myOrderCurrencycodeval = None
      if (myOrderCurrencycode is not None):
          myOrderCurrencycodeval = myOrderCurrencycode.text
      myOrderAmount = find_orders_by_obj(myOrderTotal, 'Amount')
      myOrderAmountval = None
      if (myOrderAmount is not None):
          myOrderAmountval = myOrderAmount.text

  myNumberOfItemsShipped = find_orders_by_obj(myorder, 'NumberOfItemsShipped')
  myNumberOfItemsShippedval = None
  if (myNumberOfItemsShipped is not None):
      myNumberOfItemsShippedval = myNumberOfItemsShipped.text
  myNumberOfItemsUnshipped = find_orders_by_obj(myorder, 'NumberOfItemsUnshipped')
  myNumberOfItemsUnshippedval = None
  if (myNumberOfItemsUnshipped is not None):
      myNumberOfItemsUnshippedval = myNumberOfItemsUnshipped.text
  myPaymentExecutionDetail = find_orders_by_obj(myorder, 'PaymentExecutionDetail')
  myPaymentExecutionDetailval = None
  if (myPaymentExecutionDetail is not None):
      myPaymentExecutionDetailval = myPaymentExecutionDetail.text
  myPaymentMethod = find_orders_by_obj(myorder, 'PaymentMethod')
  myPaymentMethodval = None
  if (myPaymentMethod is not None):
      myPaymentMethodval = myPaymentMethod.text
  myPaymentMethodDetails = find_orders_by_obj(myorder, 'PaymentMethodDetails')
  myPaymentMethodDetailsval = None
  if (myPaymentMethodDetails is not None):
      myPaymentMethodDetailsval = myPaymentMethodDetails.text
  myIsReplacementOrder = find_orders_by_obj(myorder, 'IsReplacementOrder')
  myIsReplacementOrderval = None
  if (myIsReplacementOrder is not None):
      myIsReplacementOrderval = myIsReplacementOrder.text
  myMarketplaceId = find_orders_by_obj(myorder, 'MarketplaceId')
  myMarketplaceIdval = None
  if (myMarketplaceId is not None):
      myMarketplaceIdval = myMarketplaceId.text
  myBuyerEmail = find_orders_by_obj(myorder, 'BuyerEmail')
  myBuyerEmailval = None
  if (myBuyerEmail is not None):
      myBuyerEmailval = myBuyerEmail.text
  myBuyerName = find_orders_by_obj(myorder, 'BuyerName')
  myBuyerNameval = None
  if (myBuyerName is not None):
      myBuyerNameval = myBuyerName.text
  myBuyerCountry = find_orders_by_obj(myorder, 'BuyerCountry')
  myBuyerCountryval = None
  if (myBuyerCountry is not None):
      myBuyerCountryval = myBuyerCountry.text
  myBuyerTaxInfo = find_orders_by_obj(myorder, 'BuyerTaxInfo')
  myBuyerTaxInfoval = None
  if (myBuyerTaxInfo is not None):
      myBuyerTaxInfoval = myBuyerTaxInfo.text
  myShipmentServiceLevelCategory = find_orders_by_obj(myorder, 'ShipmentServiceLevelCategory')
  myShipmentServiceLevelCategoryval = None
  if (myShipmentServiceLevelCategory is not None):
      myShipmentServiceLevelCategoryval = myShipmentServiceLevelCategory.text
  myOrderType = find_orders_by_obj(myorder, 'OrderType')
  myOrderTypeval = None
  if (myOrderType is not None):
      myOrderTypeval = myOrderType.text
  myEarliestShipDate = find_orders_by_obj(myorder, 'EarliestShipDate')
  myEarliestShipDateval = None
  if (myEarliestShipDate is not None):
      myEarliestShipDateval = myEarliestShipDate.text
  myLatestShipDate = find_orders_by_obj(myorder, 'LatestShipDate')
  myLatestShipDateval = None
  if (myLatestShipDate is not None):
      myLatestShipDateval = myLatestShipDate.text
  myEarliestDeliveryDate = find_orders_by_obj(myorder, 'EarliestDeliveryDate')
  myEarliestDeliveryDateval = None
  if (myEarliestDeliveryDate is not None):
      myEarliestDeliveryDateval = myEarliestDeliveryDate.text
  myLatestDeliveryDate = find_orders_by_obj(myorder, 'LatestDeliveryDate')
  myLatestDeliveryDateval = None
  if (myLatestDeliveryDate is not None):
      myLatestDeliveryDateval = myLatestDeliveryDate.text
  myIsBusinessOrder = find_orders_by_obj(myorder, 'IsBusinessOrder')
  myIsBusinessOrderval = None
  if (myIsBusinessOrder is not None):
      myIsBusinessOrderval = myIsBusinessOrder.text
  myIsPrime = find_orders_by_obj(myorder, 'IsPrime')
  myIsPrimeval = None
  if (myIsPrime is not None):
      myIsPrimeval = myIsPrime.text
  myPromiseResponseDueDate = find_orders_by_obj(myorder, 'PromiseResponseDueDate')
  myPromiseResponseDueDateval = None
  if (myPromiseResponseDueDate is not None):
      myPromiseResponseDueDateval = myPromiseResponseDueDate.text
  myOrderStatus = find_orders_by_obj(myorder, 'OrderStatus')
  myOrderStatusval = None
  if (myOrderStatus is not None):
      myOrderStatusval = myOrderStatus.text

  sql = 'insert into orders (amazon_order_id,purchase_date,last_update_date,fulfillment_channel,shipping_add_name,shipping_add_line_1,shipping_add_line_2,shipping_add_line_3,shipping_add_city,shipping_add_country,shipping_add_distinct,shipping_add_state,shipping_add_poscode,shipping_add_countrycode,shipping_add_phone,shipping_add_addtype,sales_channel,ship_service_level,profile_fields,order_currencycode,order_amount,number_of_items_shipped,number_of_items_unshipped,payment_execution_detail,payment_method,payment_method_details,is_replacement_order,marketplace_id,buyer_email,buyer_name,buyer_county,buyer_tax_info,shipment_service_level_category,order_type,earliest_ship_date,latest_ship_date,earliest_delivery_date,latest_delivery_date,is_business_order,is_prime,promise_response_due_date,order_status) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
  mydata = (
  myAmazonOrderIdval, myPurchaseDateval, myLastUpdateDateval, myFulfillmentChannelval, myShippingAddressNameval,
  myShippingAddressAddressLine1val, myShippingAddressAddressLine2val, myShippingAddressAddressLine3val,
  myShippingAddressCityval, myShippingAddressCountyval, myShippingAddressDistrictval,
  myShippingAddressStateOrRegionval, myShippingAddressPostalCodeval, myShippingAddressCountryCodeval,
  myShippingAddressPhoneval, myShippingAddressAddressTypeval, mySalesChannelval, myShipServiceLevelval,
  myPofileFieldsval, myOrderCurrencycodeval, myOrderAmountval, myNumberOfItemsShippedval, myNumberOfItemsUnshippedval,
  myPaymentExecutionDetailval, myPaymentMethodval, myPaymentMethodDetailsval, myIsReplacementOrderval,
  myMarketplaceIdval, myBuyerEmailval, myBuyerNameval, myBuyerCountryval, myBuyerTaxInfoval,
  myShipmentServiceLevelCategoryval, myOrderTypeval, myEarliestShipDateval, myLatestShipDateval,
  myEarliestDeliveryDateval, myLatestDeliveryDateval, myIsBusinessOrderval, myIsPrimeval, myPromiseResponseDueDateval,
  myOrderStatusval)
  myc.execute(sql, mydata)
  return


class MWSError(Exception):
  pass


# MWS
#
class BaseObject(object):
    _response = None

    _orders_namespace = {
        "ns": "http://mws.amazonaws.com/doc/2009-01-01/"
    }

    _orders_namespace = {
        "2013-09-01": "https://mws.amazonservices.com/Orders/2013-09-01"
    }

    _products_namespace = {
        "2011-10-01": "http://mws.amazonservices.com/schema/Products/2011-10-01",
        "ns2": "http://mws.amazonservices.com/schema/Products/2011-10-01/default.xsd"
    }

    # VERSION = "2009-01-01"
    #VERSION = "2013-09-01"
    VERSION = "2011-10-01"

    AMAZON_CREDENTIAL = {
        'SELLER_ID': os.getenv('AWS_SELLER_ID',''),
        'ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID',''),
        'ACCESS_SECRET': os.getenv('AWS_SECRET_ACCESS_KEY',''),
    }

    DOMAIN = 'mws.amazonservices.jp'
    ENDPOINT = '/Products/2011-10-01'
    VERSION = "2011-10-01"

    def datetime_encode(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    def __init__(self, logger, AWSAccessKeyId=None, AWSSecretAccessKey=None,
               SellerId=None, Region='JP', Version="", MWSAuthToken=""):

        # logging
        #logging.basicConfig(filename='/app/yaget/log/amamws.log', level=logging.DEBUG)
        #logger = logging.getLogger(__name__)
        #logger.setLevel(10)
        self.logger = logger
        self.logger.info('AmaMws request init in')
        self.logger.debug('AmaMws request debug init in')

        # 引数が優先。未指定なら AMAZON_CREDENTIAL（= 環境変数）を使用
        self.AWSAccessKeyId     = AWSAccessKeyId     or AMAZON_CREDENTIAL['ACCESS_KEY_ID']
        self.AWSSecretAccessKey = AWSSecretAccessKey or AMAZON_CREDENTIAL['ACCESS_SECRET']
        self.SellerId           = SellerId           or AMAZON_CREDENTIAL['SELLER_ID']

        self.Region = Region
        self.Version = Version or self.VERSION

        if Region in MARKETPLACES:
            self.service_domain = MARKETPLACES[self.Region][0]
        else:
            raise MWSError("Incorrrect region supplied {region}".format(**{"region": region}))

    # API
    def request(self, endpoint, method="POST", **kwargs):
        params = {
            'AWSAccessKeyId': self.AWSAccessKeyId,
            'SellerId': self.SellerId,
            'SignatureVersion': '2',
            'Timestamp': self.timestamp,
            'Version': self.Version,
            'SignatureMethod': 'HmacSHA256'
        }

        params.update(kwargs)

        #        signature, query_string = self.signature(method, endpoint, params)

        query_string = '&'.join('{}={}'.format(
            n, urllib.parse.quote(v, safe='')) for n, v in sorted(params.items()))

        canonical = "{}\n{}\n{}\n{}".format(
            'POST', DOMAIN, endpoint, query_string
        )

        h = hmac.new(
            six.b(self.AWSSecretAccessKey),
            six.b(canonical), hashlib.sha256)

        signature = urllib.parse.quote(base64.b64encode(h.digest()), safe='')

        url = 'https://{}{}?{}&Signature={}'.format(
            DOMAIN, endpoint, query_string, signature)

      #        url = self.build_url(endpoint, query_string, signature)

        print("m_url:[%s]", url)
        #self.logger.info('AmaMws request m_url:' + str(url))
        #self.logger.debug('AmaMws request debug m_url:' + str(url))

        try:
            request = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(request) as page:
                self._response = page.read()
        except Exception as e:
            print("message:{0}".format(str(failure(e))))
        #request = urllib.request.Request(url, method=method)
        #with urllib.request.urlopen(request) as page:
        #    self._response = page.read()
        print("doukana response:[%s]", self._response)
        return self

    def signature(self, method, endpoint, params):
        query_string = self.quote_query(params)

        data = method + "\n" + self.service_domain.replace("https://", "") + endpoint + "\n/\n" + query_string

        if type(self.AWSSecretAccessKey) is str:
            self.AWSSecretAccessKey = self.AWSSecretAccessKey.encode('utf-8')

        if type(data) is str:
            data = data.encode('utf-8')

        digest = hmac.new(self.AWSSecretAccessKey, data, sha256).digest()
        return (urllib.parse.quote(b64encode(digest)), query_string)

    def build_url(self, endpoint, query_string, signature):
        return "%s%s/?%s&Signature=%s" % (self.service_domain, endpoint, query_string, signature)

    def enumerate_param(self, param, values):
        """
          Builds a dictionary of an enumerated parameter.
          Takes any iterable and returns a dictionary.
          ie.
          enumerate_param('MarketplaceIdList.Id', (123, 345, 4343))
          returns
          {
              MarketplaceIdList.Id.1: 123,
              MarketplaceIdList.Id.2: 345,
              MarketplaceIdList.Id.3: 4343
          }
        """
        params = {}

        if not param.endswith('.'):
            param = "%s." % param
        for num, value in enumerate(values):
            params['%s%d' % (param, (num + 1))] = value
        return params

    @staticmethod
    def quote_query(query):
        return "&".join("%s=%s" % (
            k, urllib.parse.quote(
                str(query[k]).encode('utf-8'), safe='-_.~'))
                    for k in sorted(query))

    @property
    def timestamp(self):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    @property
    def raw(self):
        return self._response

    # xml
    @property
    def parse(self):
        if self._response is None:
            raise
        # print('start parse')
        # print('my res:[%s]',self._response)

        return ET.fromstring(self._response)

    def find(self, element):
        return self.parse.find(".//ns:%s" % element, self._namespace)

    def find_orders(self, element):
        return self.parse.find(".//2013-09-01:%s" % element, self._orders_namespace)

    def find_orders_all(self, element):
        return self.parse.findall(".//2013-09-01:%s" % element, self._orders_namespace)

    # element には「ASIN」などmws から返ってきたxmlのタグ名を
    def find_list_matched_product(self, element):
        #return self.parse.find("2011-10-01:%s" % element, self._products_namespace)
        return self.parse.find(".//2011-10-01:%s" % element, self._products_namespace)

    # product で取れたxmlのオブジェクト対応
    def find_list_matched_product_by_obj(self, myobj, element):
        #return self.parse.find("2011-10-01:%s" % element, self._products_namespace)
        return myobj.find(".//2011-10-01:%s" % element, self._products_namespace)

    # SalesRankは3つくらい取れそう
    def find_list_matched_product_all(self, element):
        self.logger.info('AmaMws Product find_list_matched_product_all in.')
        #self.logger.info('xml... ' + str(self._response))
        return self.parse.findall(".//2011-10-01:%s" % element, self._products_namespace)

    def find_list_matched_product_all_by_obj(self, myobj, element):
        return myobj.findall(".//2011-10-01:%s" % element, self._products_namespace)

    def find_list_matched_product_default(self, element):
        return self.parse.find(".//ns2:%s" % element, self._products_namespace)

    def find_list_matched_product_default_by_obj(self, myobj, element):
        return myobj.find(".//ns2:%s" % element, self._products_namespace)

    def find_list_matched_product_itemdimention(self, element):
        ItemDimensionsobj = self.find_list_matched_product_default('ItemDimensions')
        if ItemDimensionsobj is not None:
            return ItemDimensionsobj.find('.//ns2:%s' % element, self._products_namespace)
        else:
            return None

    def find_list_matched_product_itemdimention_by_obj(self, myobj, element):
        ItemDimensionsobj = self.find_list_matched_product_default_by_obj(myobj, 'ItemDimensions')
        if ItemDimensionsobj is not None:
            return ItemDimensionsobj.find('.//ns2:%s' % element, self._products_namespace)
        else:
            return None

    def find_list_matched_product_packagedimention(self, element):
        PackageDimensionsobj = self.find_list_matched_product_default('PackageDimensions')
        if PackageDimensionsobj is not None:
            return PackageDimensionsobj.find('.//ns2:%s' % element, self._products_namespace)
        else:
            return None

    def find_list_matched_product_packagedimention_by_obj(self, myobj, element):
        PackageDimensionsobj = self.find_list_matched_product_default_by_obj(myobj, 'PackageDimensions')
        if PackageDimensionsobj is not None:
            return PackageDimensionsobj.find('.//ns2:%s' % element, self._products_namespace)
        else:
            return None


class AmaSPApi(object):

    # Yahoo国内版は、db_entryの指定はなし
    # Yahoo 輸入版、csvでカテゴリなど渡すバージョンは、csvのレコードを db_entryに格納して渡す
    # 本版では、USのAmazon SP-API を叩いてアメリカのasinを集めてくる。
    def __init__(self, logger, bid, gid, my_query, db_entry=None):
        self.logger = logger
        #self.products = Products(logger)
        #self._response = myxml

        # 商品単位となるが一時保持用に変数を用意する
        self._bid = bid
        self._gid = gid
        self._query = my_query
        self.parsedxml_list = []
        self._db_entry = db_entry

        self.logger.info('AmaSPAPI  in. init keyword:[{}]'.format(self._query))
        self.upd_csv = []
        self.target_url = "https://api.amazon.com/auth/o2/token"
        self.api_key = "56f37bab855914fd56d8f1b49215e5899d77dec93b81831052a762864a8049ed"
        self.grant_type = "refresh_token"
        self.jp_refresh_token = os.getenv("LWA_JP_REFRESH_TOKEN", "")
        self.jp_client_id = os.getenv("LWA_JP_CLIENT_ID", "")
        self.jp_client_secret = os.getenv("LWA_JP_CLIENT_SECRET", "")
        self.jp_aws_access_key = os.getenv("AWS_JP_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
        self.jp_aws_secret_access_key = os.getenv("AWS_JP_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", ""))
        self.req_headers = None
        self.get_url = "https://sellingpartnerapi-na.amazon.com"  # 北米
        #self.get_url = "https://sellingpartnerapi-fe.amazon.com" # 日本
        self.access_token = None
        self.marketplace = "ATVPDKIKX0DER" # 北米 ATVPDKIKX0DER  カナダ　A2EUQ1WTGCTBG2 日本 A1VC38T7YXB528
        self.host = "sellingpartnerapi-na.amazon.com"  # 北米
        # self.host = "sellingpartnerapi-fe.amazon.com"  # 日本
        self.region = "us-east-1"  # 北米
        #self.region = "us-west-2"  # 日本
        self.service = "execute-api"

        self.credentials = dict(
            refresh_token=self.refresh_token,
            lwa_app_id=self.client_id,
            lwa_client_secret=self.client_secret,
            aws_secret_key=self.aws_secret_access_key,
            aws_access_key=self.aws_access_key,
            #role_arn='arn:aws:iam::000222965326:user/AWS_IAM_SPAPI_Access_User'
        )

    def spapi_get_participantion(self):

        #response = Sellers(marketplace=Marketplaces.JP, credentials=self.credentials).get_marketplace_participation()
        response = Sellers(marketplace=Marketplaces.US, credentials=self.credentials).get_marketplace_participation()
        self.logger.info('spapi_get_participantion [{}]'.format(response))
        #print(response)
        return

    def spapi_get_catalog_item(self, asin):

        asin = 'B07WXL5YPW'
        response = Catalog(marketplace=Marketplaces.US, credentials=self.credentials).get_item(asin)
        self.logger.info('spapi_get_catalog_item [{}]'.format(response))
        #print(response)
        return

    def spapi_list_item_by_keyword(self):

        keyword = 'Nintendo Switch'
        keyword = 'Watch Burgmeister BM505-122'
        #keyword = 'Watch Burgmeister Manila BM518-316'
        keyword = self._query
        response = Catalog(marketplace=Marketplaces.US, credentials=self.credentials).list_items(Query=keyword)
        #print(response)
        #response_ = ast.literal_eval(response)  # ValueError: malformed node or string:  と怒られる
        #print(response.headers)
        #print(response.payload)
        self.logger.info('spapi_list_item_by_keyword len[{}]'.format(len(response('Items'))))
        #print(len(response('Items')))  # Itemの個数はこれで取れる
        for item in response('Items'):
            MarketplaceASIN = item['Identifiers']['MarketplaceASIN']
            self.logger.info('marketplaceid:[{}] asin:[{}]'.format(
                MarketplaceASIN['MarketplaceId'], MarketplaceASIN['ASIN']))
            #print('marketplaceid:[{}] asin:[{}]'.format(MarketplaceASIN['MarketplaceId'], MarketplaceASIN['ASIN']))

            # 関連商品
            Relationships = item['Relationships']
            for relationship in Relationships:
                rel_MarketplaceASIN = relationship['Identifiers']['MarketplaceASIN']
                self.logger.info('rel_marketplaceid:[{}] asin:[{}]'.format(rel_MarketplaceASIN['MarketplaceId'],
                                                            rel_MarketplaceASIN['ASIN']))
                """
                print('rel_marketplaceid:[{}] asin:[{}]'.format(rel_MarketplaceASIN['MarketplaceId'],
                                                            rel_MarketplaceASIN['ASIN']))
                """

            # セールスランキング
            rank_cat_1 = ''
            rank_1 = ''
            SalesRankings = item['SalesRankings']
            for SalesRanking in SalesRankings:
                self.logger.info('salesrank_ProductCategoryId:[{}] Rank:[{}]'.format(SalesRanking['ProductCategoryId'],
                                                            SalesRanking['Rank']))
                rank_cat_1 = SalesRanking['ProductCategoryId']
                rank_1 = SalesRanking['Rank']
                """
                print('salesrank_ProductCategoryId:[{}] Rank:[{}]'.format(SalesRanking['ProductCategoryId'],
                                                            SalesRanking['Rank']))
                """

            # 属性
            AttributeSets = item['AttributeSets']
            for AttributeSet in AttributeSets:
                actor = ''
                if 'Actor' in AttributeSet:
                    actor = AttributeSet['Actor'][0]  # 複数あるが1つ目だけをとりあえず
                artist = ''
                if 'Artist' in AttributeSet:
                    artist = AttributeSet['Artist'][0]  # 複数あるが1つ目だけをとりあえず
                aspectRatio = ''
                if 'AspectRatio' in AttributeSet:
                    aspectRatio = AttributeSet['AspectRatio']
                audienceRating = ''
                if 'AudienceRating' in AttributeSet:
                    audienceRating = AttributeSet['AudienceRating']
                author = ''
                if 'Author' in AttributeSet:
                    author = AttributeSet['Author'][0]  # 複数あるが1つ目だけをとりあえず
                backFinding = ''
                if 'BackFinding' in AttributeSet:
                    backFinding = AttributeSet['BackFinding']
                bandMaterialType = ''
                if 'BandMaterialType' in AttributeSet:
                    bandMaterialType = AttributeSet['BandMaterialType']
                binding = ''
                if 'Binding' in AttributeSet:
                    binding = AttributeSet['Binding']
                blurayRegion = ''
                if 'BlurayRegion' in AttributeSet:
                    blurayRegion = AttributeSet['BlurayRegion']
                brand = ''
                if 'Brand' in AttributeSet:
                    brand = AttributeSet['Brand']
                ceroAgeRating = ''
                if 'CeroAgeRating' in AttributeSet:
                    ceroAgeRating = AttributeSet['CeroAgeRating']
                chainType = ''
                if 'ChainType' in AttributeSet:
                    chainType = AttributeSet['ChainType']
                claspType = ''
                if 'ClaspType' in AttributeSet:
                    claspType = AttributeSet['ClaspType']
                color = ''
                if 'Color' in AttributeSet:
                    color = AttributeSet['Color']
                self.logger.info('attr_Binding:[{}] Brand:[{}] Color:[{}]'.format(
                    binding, brand, color))
                """
                print('attr_Binding:[{}] Brand:[{}] Color:[{}]'.format(
                    binding, brand, color))
                """
                cpuManufacturer = ''
                if 'CpuManufacturer' in AttributeSet:
                    cpuManufacturer = AttributeSet['CpuManufacturer']
                cpuSpeed_val = ''
                cpuSpeed_units = ''
                if 'CpuSpeed' in AttributeSet:
                    if 'value' in AttributeSet['CpuSpeed']:
                        cpuSpeed_val = AttributeSet['CpuSpeed']['value']
                    if 'Units' in AttributeSet['CpuSpeed']:
                        cpuSpeed_units = AttributeSet['CpuSpeed']['Units']
                cpuType = ''
                if 'CpuType' in AttributeSet:
                    cpuType = AttributeSet['CpuType']
                creator_val = ''
                creator_Role = ''
                if 'Creator' in AttributeSet:
                    if 'value' in AttributeSet['Creator']:
                        creator_val = AttributeSet['Creator']['value']
                    if 'Role' in AttributeSet['Creator']:
                        creator_Role = AttributeSet['Creator']['Role']
                department = ''
                if 'Department' in AttributeSet:
                    department = AttributeSet['Department']
                director = ''
                if 'Director' in AttributeSet:
                    director = AttributeSet['Director'][0]  # 複数あるが1つ目だけをとりあえず
                display_size_value = ''
                display_size_Units = ''
                if 'DisplaySize' in AttributeSet:
                    if 'value' in AttributeSet['DisplaySize']:
                        display_size_value = AttributeSet['DisplaySize']['value']
                    if 'Units' in AttributeSet['DisplaySize']:
                        display_size_Units = AttributeSet['DisplaySize']['Units']
                edition = ''
                if 'Edition' in AttributeSet:
                    edition = AttributeSet['Edition']
                episodeSequence = ''
                if 'EpisodeSequence' in AttributeSet:
                    episodeSequence = AttributeSet['EpisodeSequence']
                esrbAgeRating = ''
                if 'EsrbAgeRating' in AttributeSet:
                    esrbAgeRating = AttributeSet['EsrbAgeRating']
                feature = ''
                if 'Feature' in AttributeSet:
                    feature = AttributeSet['Feature'][0]  # 複数あるが1つ目だけをとりあえず
                flavor = ''
                if 'Flavor' in AttributeSet:
                    flavor = AttributeSet['Flavor']
                format_val = ''
                if 'Format' in AttributeSet:
                    format_val = AttributeSet['Format'][0]  # 複数あるが1つ目だけをとりあえず
                gemType = ''
                if 'GemType' in AttributeSet:
                    gemType = AttributeSet['GemType'][0]  # 複数あるが1つ目だけをとりあえず
                genre = ''
                if 'Genre' in AttributeSet:
                    genre = AttributeSet['Genre']
                golfClubFlex = ''
                if 'GolfClubFlex' in AttributeSet:
                    golfClubFlex = AttributeSet['GolfClubFlex']
                golfClubFlex_value = ''
                golfClubFlex_Units = ''
                if 'GolfClubLoft' in AttributeSet:
                    if 'value' in AttributeSet['GolfClubLoft']:
                        golfClubFlex_value = AttributeSet['GolfClubLoft']['value']
                    if 'Units' in AttributeSet['GolfClubLoft']:
                        golfClubFlex_Units = AttributeSet['GolfClubLoft']['Units']
                handOrientation = ''
                if 'HandOrientation' in AttributeSet:
                    handOrientation = AttributeSet['HandOrientation']
                hardDiskInterface = ''
                if 'HardDiskInterface' in AttributeSet:
                    hardDiskInterface = AttributeSet['HardDiskInterface']
                HardDiskSize_value = ''
                HardDiskSize_Units = ''
                if 'HardDiskSize' in AttributeSet:
                    if 'value' in AttributeSet['HardDiskSize']:
                        HardDiskSize_value = AttributeSet['HardDiskSize']['value']
                    if 'Units' in AttributeSet['HardDiskSize']:
                        HardDiskSize_Units = AttributeSet['HardDiskSize']['Units']
                hardware_platform = ''
                if 'HardwarePlatform' in AttributeSet:
                    hardware_platform = AttributeSet['HardwarePlatform']
                hazardousMaterialType = ''
                if 'HazardousMaterialType' in AttributeSet:
                    hazardousMaterialType = AttributeSet['HazardousMaterialType']

                is_adult_product= ''
                if 'IsAdultProduct' in AttributeSet:
                    is_adult_product = AttributeSet['IsAdultProduct']
                self.logger.info('attr_DisplaySize:[{}] HardwarePlatform:[{}] IsAdultProduct:[{}]'.format(
                    display_size_value, hardware_platform, is_adult_product))
                """
                print('attr_DisplaySize:[{}] HardwarePlatform:[{}] IsAdultProduct:[{}]'.format(
                    display_size_value, hardware_platform, is_adult_product))
                """

                item_dim_height_val = ''
                item_dim_height_units = ''
                item_dim_length_val = ''
                item_dim_length_units = ''
                item_dim_weight_val = ''
                item_dim_weight_units = ''
                item_dim_width_val = ''
                item_dim_width_units = ''

                if 'ItemDimensions' in AttributeSet:
                    if 'Height' in AttributeSet['ItemDimensions']:
                        item_dim_height_val = AttributeSet['ItemDimensions']['Height']['value']
                        item_dim_height_units = AttributeSet['ItemDimensions']['Height']['Units']
                    if 'Length' in AttributeSet['ItemDimensions']:
                        item_dim_length_val = AttributeSet['ItemDimensions']['Length']['value']
                        item_dim_length_units = AttributeSet['ItemDimensions']['Length']['Units']
                    if 'Weight' in AttributeSet['ItemDimensions']:
                        item_dim_weight_val = AttributeSet['ItemDimensions']['Weight']['value']
                        item_dim_weight_units = AttributeSet['ItemDimensions']['Weight']['Units']
                    if 'Width' in AttributeSet['ItemDimensions']:
                        item_dim_width_val = AttributeSet['ItemDimensions']['Width']['value']
                        item_dim_width_units = AttributeSet['ItemDimensions']['Width']['Units']

                self.logger.info('attr_ItemDimensions_Height:[{}{}] Length:[{}{}] Weight:[{}{}] Width:[{}{}]'.format(
                    item_dim_height_val, item_dim_height_units,
                    item_dim_length_val, item_dim_length_units,
                    item_dim_weight_val, item_dim_weight_units,
                    item_dim_width_val, item_dim_width_units,
                ))
                """
                print('attr_ItemDimensions_Height:[{}{}] Length:[{}{}] Weight:[{}{}] Width:[{}{}]'.format(
                    item_dim_height_val, item_dim_height_units,
                    item_dim_length_val, item_dim_length_units,
                    item_dim_weight_val, item_dim_weight_units,
                    item_dim_width_val, item_dim_width_units,
                ))
                """

                isAutographed= ''
                if 'IsAutographed' in AttributeSet:
                    isAutographed = AttributeSet['IsAutographed']
                isEligibleForTradeIn= ''
                if 'IsEligibleForTradeIn' in AttributeSet:
                    isEligibleForTradeIn = AttributeSet['IsEligibleForTradeIn']
                isMemorabilia= ''
                if 'IsMemorabilia' in AttributeSet:
                    isMemorabilia = AttributeSet['IsMemorabilia']
                issuesPerYear= ''
                if 'IssuesPerYear' in AttributeSet:
                    issuesPerYear = AttributeSet['IssuesPerYear']
                itemPartNumber = ''
                if 'ItemPartNumber' in AttributeSet:
                    itemPartNumber = AttributeSet['ItemPartNumber']
                label = ''
                if 'Label' in AttributeSet:
                    label = AttributeSet['Label']
                Languages = ''
                if 'Languages' in AttributeSet:
                    Languages = AttributeSet['Languages'][0]  # 複数あるが1つ目だけをとりあえず
                legalDisclaimer = ''
                if 'LegalDisclaimer' in AttributeSet:
                    legalDisclaimer = AttributeSet['LegalDisclaimer']
                list_price_amount = ''
                list_price_currency_code = ''
                if 'ListPrice' in AttributeSet:
                    list_price_amount = AttributeSet['ListPrice']['Amount']
                    list_price_currency_code = AttributeSet['ListPrice']['CurrencyCode']
                self.logger.info('label:[{}] Languages:[{}] list_price:[{}({})]'.format(
                    label, Languages, list_price_amount, list_price_currency_code))
                """
                print('label:[{}] Languages:[{}] list_price:[{}({})]'.format(
                    label, Languages, list_price_amount, list_price_currency_code))
                """

                manufacturer = ''
                if 'Manufacturer' in AttributeSet:
                    manufacturer = AttributeSet['Manufacturer']
                ManufacturerMaximumAge_value = ''
                ManufacturerMaximumAge_Units = ''
                if 'ManufacturerMaximumAge' in AttributeSet:
                    if 'value' in AttributeSet['ManufacturerMaximumAge']:
                        ManufacturerMaximumAge_value = AttributeSet['ManufacturerMaximumAge']['value']
                    if 'Units' in AttributeSet['ManufacturerMaximumAge']:
                        ManufacturerMaximumAge_Units = AttributeSet['ManufacturerMaximumAge']['Units']
                ManufacturerMinimumAge_value = ''
                ManufacturerMinimumAge_Units = ''
                if 'ManufacturerMinimumAge' in AttributeSet:
                    if 'value' in AttributeSet['ManufacturerMinimumAge']:
                        ManufacturerMinimumAge_value = AttributeSet['ManufacturerMinimumAge']['value']
                    if 'Units' in AttributeSet['ManufacturerMinimumAge']:
                        ManufacturerMinimumAge_Units = AttributeSet['ManufacturerMinimumAge']['Units']
                manufacturerPartsWarrantyDescription = ''
                if 'ManufacturerPartsWarrantyDescription' in AttributeSet:
                    manufacturerPartsWarrantyDescription = AttributeSet['ManufacturerPartsWarrantyDescription']
                materialType = ''
                if 'MaterialType' in AttributeSet:
                    materialType = AttributeSet['MaterialType'][0]  # 複数あるが1つ目だけをとりあえず
                maximumResolution_value = ''
                maximumResolution_Units = ''
                if 'MaximumResolution' in AttributeSet:
                    if 'value' in AttributeSet['MaximumResolution']:
                        maximumResolution_value = AttributeSet['MaximumResolution']['value']
                    if 'Units' in AttributeSet['MaximumResolution']:
                        maximumResolution_Units = AttributeSet['MaximumResolution']['Units']
                mediaType = ''
                if 'MediaType' in AttributeSet:
                    mediaType = AttributeSet['MediaType'][0]  # 複数あるが1つ目だけをとりあえず
                metalStamp = ''
                if 'MetalStamp' in AttributeSet:
                    metalStamp = AttributeSet['MetalStamp']
                metalType = ''
                if 'MetalType' in AttributeSet:
                    metalType = AttributeSet['MetalType']
                model = ''
                if 'Model' in AttributeSet:
                    model = AttributeSet['Model']
                numberOfDiscs = ''
                if 'NumberOfDiscs' in AttributeSet:
                    numberOfDiscs = AttributeSet['NumberOfDiscs']
                numberOfIssues = ''
                if 'NumberOfIssues' in AttributeSet:
                    numberOfIssues = AttributeSet['NumberOfIssues']
                number_of_items = ''
                if 'NumberOfItems' in AttributeSet:
                    number_of_items = AttributeSet['NumberOfItems']
                self.logger.info('Manufacturer:[{}] Model:[{}] NumberOfItems:[{}]'.format(
                    manufacturer, model, number_of_items))
                """
                print('Manufacturer:[{}] Model:[{}] NumberOfItems:[{}]'.format(
                    manufacturer, model, number_of_items))
                """
                numberOfPages = ''
                if 'NumberOfPages' in AttributeSet:
                    numberOfPages = AttributeSet['NumberOfPages']
                numberOfTracks = ''
                if 'NumberOfTracks' in AttributeSet:
                    numberOfTracks = AttributeSet['NumberOfTracks']

                operating_system = ''
                if 'OperatingSystem' in AttributeSet:
                    for system_name in AttributeSet['OperatingSystem']:  # ここは文字列でつなげる。必要であれば分割
                        operating_system += system_name + ' '
                self.logger.info('operating_system:[{}]'.format(operating_system))
                #print('operating_system:[{}]'.format(operating_system))

                opticalZoom_value = ''
                opticalZoom_Units = ''
                if 'OpticalZoom' in AttributeSet:
                    if 'value' in AttributeSet['OpticalZoom']:
                        opticalZoom_value = AttributeSet['OpticalZoom']['value']
                    if 'Units' in AttributeSet['OpticalZoom']:
                        opticalZoom_Units = AttributeSet['OpticalZoom']['Units']

                pac_dim_height_val = ''
                pac_dim_height_units = ''
                pac_dim_length_val = ''
                pac_dim_length_units = ''
                pac_dim_weight_val = ''
                pac_dim_weight_units = ''
                pac_dim_width_val = ''
                pac_dim_width_units = ''

                if 'PackageDimensions' in AttributeSet:
                    if 'Height' in AttributeSet['PackageDimensions']:
                        pac_dim_height_val = AttributeSet['PackageDimensions']['Height']['value']
                        pac_dim_height_units = AttributeSet['PackageDimensions']['Height']['Units']
                    if 'Length' in AttributeSet['PackageDimensions']:
                        pac_dim_length_val = AttributeSet['PackageDimensions']['Length']['value']
                        pac_dim_length_units = AttributeSet['PackageDimensions']['Length']['Units']
                    if 'Weight' in AttributeSet['PackageDimensions']:
                        pac_dim_weight_val = AttributeSet['PackageDimensions']['Weight']['value']
                        pac_dim_weight_units = AttributeSet['PackageDimensions']['Weight']['Units']
                    if 'Width' in AttributeSet['PackageDimensions']:
                        pac_dim_width_val = AttributeSet['PackageDimensions']['Width']['value']
                        pac_dim_width_units = AttributeSet['PackageDimensions']['Width']['Units']

                self.logger.info('attr_PackageDimensions_Height:[{}{}] Length:[{}{}] Weight:[{}{}] Width:[{}{}]'.format(
                    pac_dim_height_val, pac_dim_height_units,
                    pac_dim_length_val, pac_dim_length_units,
                    pac_dim_weight_val, pac_dim_weight_units,
                    pac_dim_width_val, pac_dim_width_units,
                ))
                """
                print('attr_PackageDimensions_Height:[{}{}] Length:[{}{}] Weight:[{}{}] Width:[{}{}]'.format(
                    pac_dim_height_val, pac_dim_height_units,
                    pac_dim_length_val, pac_dim_length_units,
                    pac_dim_weight_val, pac_dim_weight_units,
                    pac_dim_width_val, pac_dim_width_units,
                ))
                """

                package_quantity = 0
                if 'PackageQuantity' in AttributeSet:
                    package_quantity = int(AttributeSet['PackageQuantity'])
                part_number = ''
                if 'PartNumber' in AttributeSet:
                    part_number = AttributeSet['PartNumber']
                pegi_rating = ''
                if 'PegiRating' in AttributeSet:
                    pegi_rating = AttributeSet['PegiRating']
                self.logger.info('package_quantity:[{}] part_number:[{}] pegi_rating:[{}]'.format(
                    package_quantity, part_number, pegi_rating))
                platform = ''
                if 'Platform' in AttributeSet:
                    platform = AttributeSet['Platform']
                processorCount = ''
                if 'ProcessorCount' in AttributeSet:
                    processorCount = AttributeSet['ProcessorCount']
                product_group = ''
                if 'ProductGroup' in AttributeSet:
                    product_group = AttributeSet['ProductGroup']
                product_type_name = ''
                if 'ProductTypeName' in AttributeSet:
                    product_type_name = AttributeSet['ProductTypeName']
                productTypeSubcategory = ''
                if 'ProductTypeSubcategory' in AttributeSet:
                    productTypeSubcategory = AttributeSet['ProductTypeSubcategory']
                publicationDate = ''
                if 'PublicationDate' in AttributeSet:
                    publicationDate = AttributeSet['PublicationDate']
                publisher = ''
                if 'Publisher' in AttributeSet:
                    publisher = AttributeSet['Publisher']
                regionCode = ''
                if 'RegionCode' in AttributeSet:
                    regionCode = AttributeSet['RegionCode']
                release_date = ''
                if 'ReleaseDate' in AttributeSet:
                    release_date = AttributeSet['ReleaseDate']
                print('platform:[{}] product_group:[{}] product_type_name:[{}] publisher[{}] release_date[{}]'.format(
                    platform, product_group, product_type_name, publisher, release_date))
                ringSize = ''
                if 'RingSize' in AttributeSet:
                    ringSize = AttributeSet['RingSize']
                runningTime_value = ''
                runningTime_Units = ''
                if 'RunningTime' in AttributeSet:
                    if 'value' in AttributeSet['RunningTime']:
                        runningTime_value = AttributeSet['RunningTime']['value']
                    if 'Units' in AttributeSet['RunningTime']:
                        runningTime_Units = AttributeSet['RunningTime']['Units']
                shaftMaterial = ''
                if 'ShaftMaterial' in AttributeSet:
                    shaftMaterial = AttributeSet['ShaftMaterial']
                scent = ''
                if 'Scent' in AttributeSet:
                    scent = AttributeSet['Scent']
                seasonSequence = ''
                if 'SeasonSequence' in AttributeSet:
                    seasonSequence = AttributeSet['SeasonSequence']
                seikodoProductCode = ''
                if 'SeikodoProductCode' in AttributeSet:
                    seikodoProductCode = AttributeSet['SeikodoProductCode']
                size = ''
                if 'Size' in AttributeSet:
                    size = AttributeSet['Size']
                sizePerPearl = ''
                if 'SizePerPearl' in AttributeSet:
                    sizePerPearl = AttributeSet['SizePerPearl']

                small_image_height_units = ''
                small_image_height_value = ''
                small_image_width_units = ''
                small_image_width_value = ''
                small_image_url = ''
                if 'SmallImage' in AttributeSet:
                    if 'Height' in AttributeSet['SmallImage']:
                        small_image_height_units = AttributeSet['SmallImage']['Height']['Units']
                        small_image_height_value = AttributeSet['SmallImage']['Height']['value']
                    if 'Width' in AttributeSet['SmallImage']:
                        small_image_width_units = AttributeSet['SmallImage']['Width']['Units']
                        small_image_width_value = AttributeSet['SmallImage']['Width']['value']
                    if 'URL' in AttributeSet['SmallImage']:
                        small_image_url = AttributeSet['SmallImage']['URL']

                self.logger.info('small_img height:[{} {}] width:[{} {}] URL:[{}]'.format(
                    small_image_height_units, small_image_height_value,
                    small_image_width_units, small_image_width_value,
                    small_image_url,
                ))
                """
                print('small_img height:[{} {}] width:[{} {}] URL:[{}]'.format(
                    small_image_height_units, small_image_height_value,
                    small_image_width_units, small_image_width_value,
                    small_image_url,
                ))
                """

                studio = ''
                if 'Studio' in AttributeSet:
                    studio = AttributeSet['Studio']
                subscriptionLength_value = ''
                subscriptionLength_Units = ''
                if 'SubscriptionLength' in AttributeSet:
                    if 'value' in AttributeSet['SubscriptionLength']:
                        subscriptionLength_value = AttributeSet['SubscriptionLength']['value']
                    if 'Units' in AttributeSet['SubscriptionLength']:
                        subscriptionLength_Units = AttributeSet['SubscriptionLength']['Units']
                systemMemorySize_value = ''
                systemMemorySize_Units = ''
                if 'SystemMemorySize' in AttributeSet:
                    if 'value' in AttributeSet['SystemMemorySize']:
                        systemMemorySize_value = AttributeSet['SystemMemorySize']['value']
                    if 'Units' in AttributeSet['SubscriptionLength']:
                        systemMemorySize_Units = AttributeSet['SystemMemorySize']['Units']
                systemMemoryType = ''
                if 'SystemMemoryType' in AttributeSet:
                    systemMemoryType = AttributeSet['SystemMemoryType']
                theatricalReleaseDate = ''
                if 'TheatricalReleaseDate' in AttributeSet:
                    theatricalReleaseDate = AttributeSet['TheatricalReleaseDate']
                title = ''
                if 'Title' in AttributeSet:
                    title = AttributeSet['Title']
                self.logger.info('studio:[{}] title:[{}]'.format(
                    studio, title))
                totalDiamondWeight_value = ''
                totalDiamondWeight_Units = ''
                if 'TotalDiamondWeight' in AttributeSet:
                    if 'value' in AttributeSet['TotalDiamondWeight']:
                        totalDiamondWeight_value = AttributeSet['TotalDiamondWeight']['value']
                    if 'Units' in AttributeSet['TotalDiamondWeight']:
                        totalDiamondWeight_Units = AttributeSet['TotalDiamondWeight']['Units']
                totalGemWeight_value = ''
                totalGemWeight_Units = ''
                if 'TotalGemWeight' in AttributeSet:
                    if 'value' in AttributeSet['TotalGemWeight']:
                        totalGemWeight_value = AttributeSet['TotalGemWeight']['value']
                    if 'Units' in AttributeSet['TotalGemWeight']:
                        totalGemWeight_Units = AttributeSet['TotalGemWeight']['Units']
                warranty = ''
                if 'Warranty' in AttributeSet:
                    warranty = AttributeSet['Warranty']
                weeeTaxValue_amount = ''
                weeeTaxValue_code = ''
                if 'WeeeTaxValue' in AttributeSet:
                    weeeTaxValue_amount = AttributeSet['WeeeTaxValue']['Amount']
                    weeeTaxValue_code = AttributeSet['WeeeTaxValue']['CurrencyCode']

                # ここからDB登録 ====================================
                if not YaShopImportSpApiAmaGoodsDetail.objects.filter(asin=MarketplaceASIN['ASIN']).exists():
                    self.logger.debug("AmaSPApi start DB update_or_create")
                    obj, created = YaShopImportSpApiAmaGoodsDetail.objects.update_or_create(
                        asin=MarketplaceASIN['ASIN'] if MarketplaceASIN['ASIN'] else '',
                        title=title if title else '',
                        url=small_image_url if small_image_url else '',
                        amount=float(list_price_amount) if list_price_amount else 0,
                        binding=binding if binding else '',
                        brand=brand if brand else '',
                        color=color if color else '',
                        department=department if department else '',
                        is_adlt=False if is_adult_product == "false" else True,
                        i_height=float(item_dim_height_val) if item_dim_height_val else 0,
                        i_length=float(item_dim_length_val) if item_dim_length_val else 0,
                        i_width=float(item_dim_width_val) if item_dim_width_val else 0,
                        i_weight=float(item_dim_weight_val) if item_dim_weight_val else 0,
                        p_height=float(pac_dim_height_val) if pac_dim_height_val else 0,
                        p_length=float(pac_dim_length_val) if pac_dim_length_val else 0,
                        p_width=float(pac_dim_width_val) if pac_dim_width_val else 0,
                        p_weight=float(pac_dim_weight_val) if pac_dim_weight_val else 0,
                        rank_cat_1=rank_cat_1 if rank_cat_1 else '',
                        rank_1=int(rank_1) if rank_1 else 0,
                        rank_cat_2='',
                        rank_2=0,
                        rank_cat_3='',
                        rank_3=0,
                        shopid=self._bid,
                        gid=self._gid,
                        csv_no=self._db_entry.csv_no,
                        y_cat_1=self._db_entry.y_cat_1,
                        y_cat_2=self._db_entry.y_cat_2,
                        myshop_cat_1=self._db_entry.myshop_cat_1,
                        myshop_cat_2=self._db_entry.myshop_cat_2,
                    )
                    obj.save()
                self.logger.debug("AmaSPApi set DB end ")

        self.logger.info(response('Items'))
        # print(response('Items'))
        return

# ここまでがSP-APIで追加分。以下はMWSの残骸だから使わないが参考に #####################################

    def get_list_matching_products(self):
        self.products.logger.info('AmaMws get_list_matching_products in')

        try:
            tmpobj = self.products.ListMatchingProducts(urllib.parse.quote(self._query))
            # tmpobj = self.products.ListMatchingProducts(urllib.parse.quote_plus(self._query, encoding="utf-8"))
            # tmpobj = self.products.ListMatchingProducts(self._query)

            self.products.logger.info('AmaMws get_list_matching_products out')
            self.products._response = self.products.PostMWS(tmpobj)
            # self.products.logger.info('AmaMws get_list_matching_products _response:{0}'.format(str(self.products._response)))
        except Exception as e:
            self.products.logger.info('get_list_matching_products except:{0}'.format(str(failure(e))))
            print("message:{0}".format(str(failure(e))))
        if self.products._response is not None:
            return True
        else:
            return False
        #products = Products()
        #return self.products.request_list_matching_products(Query)

    # element には「ASIN」などmws から返ってきたxmlのタグ名を
    def find_list_matched_product_ns2(self, element):
        return self.products.find_list_matched_product_ns2(element)

    # element には「ASIN」などmws から返ってきたxmlのタグ名を
    def find_list_matched_product(self, element):
        return self.products.find_list_matched_product(element)

    def set_list_matched_product(self, product):

        parsedxml = {}

        key_normal_list = ["ASIN", "MarketplaceId"]
        for key_normal in key_normal_list:
            # 以下は productを引数にとらず一つだけ取ってきていた名残
            #findobj = self.find_list_matched_product(key_normal)
            findobj = self.products.find_list_matched_product_by_obj(product, key_normal)
            if findobj is None:
                return None # とれなかったらNG
            else:
                parsedxml[key_normal] = findobj.text

        # 初期値はstrのものを対象
        key_default_str_list = [
            "Title",
            "URL",
            "Amount",
            "Binding",
            "Brand",
            "Color",
            "Department",
            "IsAdultProduct",
        ]
        for key_default in key_default_str_list:
            #findobj = self.find_list_matched_product_default(key_default)
            findobj = self.products.find_list_matched_product_default_by_obj(product, key_default)
            if findobj is None:
                parsedxml[key_default] = ''
            else:
                parsedxml[key_default] = findobj.text

        # dimentionに関する値
        key_dimention_str_list = [
            "Height",
            "Length",
            "Width",
            "Weight",
        ]
        # itemdimentionに関する値
        for key_default in key_dimention_str_list:
            #findobj = self.find_list_matched_product_itemdimention(key_default)
            findobj = self.products.find_list_matched_product_itemdimention_by_obj(product, key_default)
            if findobj is None:
                parsedxml["i_" + key_default] = ''
            else:
                parsedxml["i_" + key_default] = findobj.text

        # packagedimentionに関する値
        for key_default in key_dimention_str_list: # リストはitemもpackageも同じ
            #findobj = self.find_list_matched_product_packagedimention(key_default)
            findobj = self.products.find_list_matched_product_packagedimention_by_obj(product, key_default)
            if findobj is None:
                parsedxml["p_" + key_default] = ''
            else:
                parsedxml["p_" + key_default] = findobj.text

        # SalesRankに関わるもの
        key_salesrank_list = ["ProductCategoryId", "Rank"]
        i = 0
        #findobj_list = self.find_list_matched_product_all("SalesRank")
        findobj_list = self.products.find_list_matched_product_all_by_obj(product, "SalesRank")
        #self.products.logger.info("AmaMws SalesRank findobj_list text:{0}".format(str(findobj_list)))
        if findobj_list:
            for findobj in findobj_list: # SalesRankは3つ
                i += 1
                #self.products.logger.info("AmaMws SalesRank findobj text:{0}".format(str(findobj)))

                for key_normal in key_salesrank_list:
                    finditem = findobj.find(".//2011-10-01:%s" % key_normal, self.products._products_namespace)

                    if finditem is None:
                        parsedxml[str(i) +  "_" + key_normal] = ''
                    else:
                        parsedxml[str(i) +  "_" + key_normal] = finditem.text
        if i < 3:
            parsedxml['3_Rank'] = 0
            parsedxml['3_ProductCategoryId'] = ''
        if i < 2:
            parsedxml['2_Rank'] = 0
            parsedxml['2_ProductCategoryId'] = ''
        if i < 1:
            parsedxml['1_Rank'] = 0
            parsedxml['1_ProductCategoryId'] = ''

        return parsedxml

    # Productで返ってきたリストは全部登録する
    def set_list_matched_product_all(self):
        self.products.logger.info('AmaMws set_list_matched_product_all in')

        try:
            product_list = self.products.find_list_matched_product_all("Product")
            for product in product_list:
                parsedxml = self.set_list_matched_product(product)
                if parsedxml:
                    # あったので登録
                    self.parsedxml_list.append(parsedxml)

                    # db登録してしまおう
                    self.set_db_product(parsedxml)
        except Exception as e:
            t, v, tb = sys.exc_info()
            self.products.logger.info("AmaMws set_list_matched_product_all except:{0}".format(str(failure(e))))
            #self.products.logger.info('AmaMws set_list_matched_product_all_add_except:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            self.products.logger.info('AmaMws set_list_matched_product_all_add_except:{0}'.format(str(traceback.format_exception(t,v,tb))))

        self.products.logger.info('AmaMws set_list_matched_product_all out')
        return

    # Productで返ってきたリストは全部登録する
    # yahoo shopping用
    def set_shop_list_matched_product_all(self):
        self.products.logger.debug('AmaMws set_shop_list_matched_product_all in')

        try:
            product_list = self.products.find_list_matched_product_all("Product")
            for product in product_list:
                parsedxml = self.set_list_matched_product(product)
                if parsedxml:
                    # あったので登録
                    self.parsedxml_list.append(parsedxml)

                    # db登録してしまおう
                    self.set_shop_db_product(parsedxml)
        except Exception as e:
            t, v, tb = sys.exc_info()
            self.products.logger.info("AmaMws set_shop_list_matched_product_all except:{0}".format(str(failure(e))))
            #self.products.logger.info('AmaMws set_shop_list_matched_product_all:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            self.products.logger.info('AmaMws set_shop_list_matched_product_all:{0}'.format(str(traceback.format_exception(t,v,tb))))

        self.products.logger.debug('AmaMws set_shop_list_matched_product_all out')
        return

    # Productで返ってきたリストは全部登録する
    # yahoo shopping 輸入用
    def set_shop_import_list_matched_product_all(self):
        self.products.logger.debug('AmaMws set_shop_import_list_matched_product_all in')

        try:
            product_list = self.products.find_list_matched_product_all("Product")
            for product in product_list:
                parsedxml = self.set_list_matched_product(product)
                if parsedxml:
                    # あったので登録
                    self.parsedxml_list.append(parsedxml)

                    # db登録してしまおう
                    self.set_shop_import_db_product(parsedxml)
        except Exception as e:
            t, v, tb = sys.exc_info()
            self.products.logger.info("AmaMws set_shop_import_list_matched_product_all except:{0}".format(str(failure(e))))
            #self.products.logger.info('AmaMws set_shop_import_list_matched_product_all:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            self.products.logger.info('AmaMws set_shop_import_list_matched_product_all:{0}'.format(str(traceback.format_exception(t,v,tb))))

        self.products.logger.debug('AmaMws set_shop_import_list_matched_product_all out')
        return

    def set_db_product(self, parsedxml):
        # ASINは重複をチェックする、しかし商品ごとにぶら下がるので・・やっぱforeignkeyはいらんかも
        asin = parsedxml["ASIN"] if parsedxml["ASIN"] else ''
        #self.products.logger.info("AmaMws set_db_product  in asin:{0}".format(str(asin)))

        #self.products.logger.info("AmaMws set_db_product  in 3_Rank:{0}".format(str(parsedxml["3_Rank"])))
        #self.products.logger.info("AmaMws set_db_product  in gid:{0}".format(str(self._gid)))

        if not YaAmaGoodsDetail.objects.filter(asin=parsedxml["ASIN"]).exists():
            self.products.logger.info("AmaMws set_db_product start update_or_create")
            obj, created = YaAmaGoodsDetail.objects.update_or_create(
                asin = parsedxml["ASIN"] if parsedxml["ASIN"] else '',
                title = parsedxml["Title"] if parsedxml["Title"] else '',
                url=parsedxml["URL"] if parsedxml["URL"] else '',
                amount=float(parsedxml["Amount"]) if parsedxml["Amount"] else 0,
                binding=parsedxml["Binding"] if parsedxml["Binding"] else '',
                brand=parsedxml["Brand"] if parsedxml["Brand"] else '',
                color=parsedxml["Color"] if parsedxml["Color"] else '',
                department=parsedxml["Department"] if parsedxml["Department"] else '',
                is_adlt = False if parsedxml["IsAdultProduct"] == "false" else True,
                i_height = float(parsedxml["i_Height"]) if parsedxml["i_Height"] else 0,
                i_length = float(parsedxml["i_Length"]) if parsedxml["i_Length"] else 0,
                i_width = float(parsedxml["i_Width"]) if parsedxml["i_Width"] else 0,
                i_weight = float(parsedxml["i_Weight"]) if parsedxml["i_Weight"] else 0,
                p_height = float(parsedxml["p_Height"]) if parsedxml["p_Height"] else 0,
                p_length = float(parsedxml["p_Length"]) if parsedxml["p_Length"] else 0,
                p_width = float(parsedxml["p_Width"]) if parsedxml["p_Width"] else 0,
                p_weight = float(parsedxml["p_Weight"]) if parsedxml["p_Weight"] else 0,
                rank_cat_1 = parsedxml["1_ProductCategoryId"] if parsedxml["1_ProductCategoryId"] else '',
                rank_1 = int(parsedxml["1_Rank"]) if parsedxml["1_Rank"] else 0,
                rank_cat_2 = parsedxml["2_ProductCategoryId"] if parsedxml["2_ProductCategoryId"] else '',
                rank_2 = int(parsedxml["2_Rank"]) if parsedxml["2_Rank"] else 0,
                rank_cat_3 = parsedxml["3_ProductCategoryId"] if parsedxml["3_ProductCategoryId"] else '',
                rank_3 = int(parsedxml["3_Rank"]) if parsedxml["3_Rank"] else 0,
                bid = self._bid,
                gid = self._gid,
            )
            obj.save()
        self.products.logger.info("AmaMws set_db_product end ")
        return

    def set_shop_db_product(self, parsedxml):
        # yahoo shopping用
        # ASINは重複をチェックする、しかし商品ごとにぶら下がるので・・やっぱforeignkeyはいらんかも
        asin = parsedxml["ASIN"] if parsedxml["ASIN"] else ''
        #self.products.logger.info("AmaMws set_shop_db_product  in asin:{0}".format(str(asin)))

        #self.products.logger.info("AmaMws set_shop_db_product  in 3_Rank:{0}".format(str(parsedxml["3_Rank"])))
        #self.products.logger.info("AmaMws set_shop_db_product  in gid:{0}".format(str(self._gid)))

        if not YaShopAmaGoodsDetail.objects.filter(asin=parsedxml["ASIN"]).exists():
            self.products.logger.debug("AmaMws set_shop_db_product start update_or_create")
            obj, created = YaShopAmaGoodsDetail.objects.update_or_create(
                asin = parsedxml["ASIN"] if parsedxml["ASIN"] else '',
                title = parsedxml["Title"] if parsedxml["Title"] else '',
                url=parsedxml["URL"] if parsedxml["URL"] else '',
                amount=float(parsedxml["Amount"]) if parsedxml["Amount"] else 0,
                binding=parsedxml["Binding"] if parsedxml["Binding"] else '',
                brand=parsedxml["Brand"] if parsedxml["Brand"] else '',
                color=parsedxml["Color"] if parsedxml["Color"] else '',
                department=parsedxml["Department"] if parsedxml["Department"] else '',
                is_adlt = False if parsedxml["IsAdultProduct"] == "false" else True,
                i_height = float(parsedxml["i_Height"]) if parsedxml["i_Height"] else 0,
                i_length = float(parsedxml["i_Length"]) if parsedxml["i_Length"] else 0,
                i_width = float(parsedxml["i_Width"]) if parsedxml["i_Width"] else 0,
                i_weight = float(parsedxml["i_Weight"]) if parsedxml["i_Weight"] else 0,
                p_height = float(parsedxml["p_Height"]) if parsedxml["p_Height"] else 0,
                p_length = float(parsedxml["p_Length"]) if parsedxml["p_Length"] else 0,
                p_width = float(parsedxml["p_Width"]) if parsedxml["p_Width"] else 0,
                p_weight = float(parsedxml["p_Weight"]) if parsedxml["p_Weight"] else 0,
                rank_cat_1 = parsedxml["1_ProductCategoryId"] if parsedxml["1_ProductCategoryId"] else '',
                rank_1 = int(parsedxml["1_Rank"]) if parsedxml["1_Rank"] else 0,
                rank_cat_2 = parsedxml["2_ProductCategoryId"] if parsedxml["2_ProductCategoryId"] else '',
                rank_2 = int(parsedxml["2_Rank"]) if parsedxml["2_Rank"] else 0,
                rank_cat_3 = parsedxml["3_ProductCategoryId"] if parsedxml["3_ProductCategoryId"] else '',
                rank_3 = int(parsedxml["3_Rank"]) if parsedxml["3_Rank"] else 0,
                shopid = self._bid,
                gid = self._gid,
            )
            obj.save()
        self.products.logger.debug("AmaMws set_shop_db_product end ")
        return

    def set_shop_import_db_product(self, parsedxml):
        # yahoo shopping 輸入用
        # ASINは重複をチェックする、しかし商品ごとにぶら下がるので・・やっぱforeignkeyはいらんかも
        asin = parsedxml["ASIN"] if parsedxml["ASIN"] else ''
        #self.products.logger.info("AmaMws set_shop_import_db_product  in asin:{0}".format(str(asin)))

        #self.products.logger.info("AmaMws set_shop_import_db_product  in 3_Rank:{0}".format(str(parsedxml["3_Rank"])))
        #self.products.logger.info("AmaMws set_shop_import_db_product  in gid:{0}".format(str(self._gid)))

        if not YaShopImportAmaGoodsDetail.objects.filter(asin=parsedxml["ASIN"]).exists():
            self.products.logger.debug("AmaMws set_shop_import_db_product start update_or_create")
            obj, created = YaShopImportAmaGoodsDetail.objects.update_or_create(
                asin = parsedxml["ASIN"] if parsedxml["ASIN"] else '',
                title = parsedxml["Title"] if parsedxml["Title"] else '',
                url=parsedxml["URL"] if parsedxml["URL"] else '',
                amount=float(parsedxml["Amount"]) if parsedxml["Amount"] else 0,
                binding=parsedxml["Binding"] if parsedxml["Binding"] else '',
                brand=parsedxml["Brand"] if parsedxml["Brand"] else '',
                color=parsedxml["Color"] if parsedxml["Color"] else '',
                department=parsedxml["Department"] if parsedxml["Department"] else '',
                is_adlt = False if parsedxml["IsAdultProduct"] == "false" else True,
                i_height = float(parsedxml["i_Height"]) if parsedxml["i_Height"] else 0,
                i_length = float(parsedxml["i_Length"]) if parsedxml["i_Length"] else 0,
                i_width = float(parsedxml["i_Width"]) if parsedxml["i_Width"] else 0,
                i_weight = float(parsedxml["i_Weight"]) if parsedxml["i_Weight"] else 0,
                p_height = float(parsedxml["p_Height"]) if parsedxml["p_Height"] else 0,
                p_length = float(parsedxml["p_Length"]) if parsedxml["p_Length"] else 0,
                p_width = float(parsedxml["p_Width"]) if parsedxml["p_Width"] else 0,
                p_weight = float(parsedxml["p_Weight"]) if parsedxml["p_Weight"] else 0,
                rank_cat_1 = parsedxml["1_ProductCategoryId"] if parsedxml["1_ProductCategoryId"] else '',
                rank_1 = int(parsedxml["1_Rank"]) if parsedxml["1_Rank"] else 0,
                rank_cat_2 = parsedxml["2_ProductCategoryId"] if parsedxml["2_ProductCategoryId"] else '',
                rank_2 = int(parsedxml["2_Rank"]) if parsedxml["2_Rank"] else 0,
                rank_cat_3 = parsedxml["3_ProductCategoryId"] if parsedxml["3_ProductCategoryId"] else '',
                rank_3 = int(parsedxml["3_Rank"]) if parsedxml["3_Rank"] else 0,
                shopid = self._bid,
                gid = self._gid,
                csv_no=self._db_entry.csv_no,
                y_cat_1=self._db_entry.y_cat_1,
                y_cat_2=self._db_entry.y_cat_2,
                myshop_cat_1=self._db_entry.myshop_cat_1,
                myshop_cat_2=self._db_entry.myshop_cat_2,
            )
            obj.save()
        self.products.logger.debug("AmaMws set_shop_import_db_product end ")
        return


class AmaSPApiAsinDetail(object):

    # Yahoo 輸入版、csvでカテゴリなど渡すバージョンは、csvのレコードを db_entryに格納して渡す
    # 本版では、USのAmazon SP-API を叩いてアメリカのasinを集めてくる。
    def __init__(self, logger, db_entry=None):
        self.logger = logger

        # 商品単位となるが一時保持用に変数を用意する
        self.parsedxml_list = []
        self._db_entry = db_entry

        self.logger.info('AmaSPApiAsinDetail  in. init keyword:[{}]'.format(self._query))
        self.upd_csv = []
        self.target_url = "https://api.amazon.com/auth/o2/token"
        self.api_key = "56f37bab855914fd56d8f1b49215e5899d77dec93b81831052a762864a8049ed"
        self.grant_type = "refresh_token"
        self.us_refresh_token = os.getenv("LWA_US_REFRESH_TOKEN", "")
        self.us_client_id = os.getenv("LWA_US_CLIENT_ID", "")
        self.us_client_secret = os.getenv("LWA_US_CLIENT_SECRET", "")
        self.us_aws_access_key = os.getenv("AWS_US_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
        self.us_aws_secret_access_key = os.getenv("AWS_US_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", ""))
        self.req_headers = None
        self.us_get_url = "https://sellingpartnerapi-na.amazon.com"  # 北米
        self.jp_get_url = "https://sellingpartnerapi-fe.amazon.com" # 日本
        self.access_token = None
        self.us_marketplace = "ATVPDKIKX0DER"  # 北米 ATVPDKIKX0DER  カナダ　A2EUQ1WTGCTBG2 日本 A1VC38T7YXB528
        self.jp_marketplace = "A1VC38T7YXB528"  # 北米 ATVPDKIKX0DER  カナダ　A2EUQ1WTGCTBG2 日本 A1VC38T7YXB528
        self.us_host = "sellingpartnerapi-na.amazon.com"  # 北米
        self.jp_host = "sellingpartnerapi-fe.amazon.com"  # 日本
        self.us_region = "us-east-1"  # 北米
        #self.region = "us-west-2"  # 日本
        self.service = "execute-api"

        self.us_credentials = dict(
            refresh_token=self.us_refresh_token,
            lwa_app_id=self.us_client_id,
            lwa_client_secret=self.us_client_secret,
            aws_secret_key=self.us_aws_secret_access_key,
            aws_access_key=self.us_aws_access_key,
            #role_arn='arn:aws:iam::000222965326:user/AWS_IAM_SPAPI_Access_User'
        )

    def spapi_get_participantion(self):

        # USから取得する
        #response = Sellers(marketplace=Marketplaces.JP, credentials=self.credentials).get_marketplace_participation()
        response = Sellers(
            marketplace=Marketplaces.US, credentials=self.us_credentials
        ).get_marketplace_participation()
        self.logger.info('spapi_get_participantion [{}]'.format(response))
        #print(response)
        return

    def spapi_get_catalog_item(self, asin):

        #asin = 'B07WXL5YPW'
        response = Catalog(marketplace=Marketplaces.US, credentials=self.us_credentials).get_item(asin)
        self.logger.info('spapi_get_catalog_item [{}]'.format(response))
        #print(response)

        res = json.loads(self.response)
        self.logger.info('spapi_get_catalog_item result_asin [{}]'.format(res["asin"]))
        """
        parsedxml = self.set_asin_data(res)
        if parsedxml:
            # db登録してしまおう
            self.set_db_product(parsedxml)
        """

        return

    def set_asin_data(self, asin_response):

        parsedxml = {}

        key_normal_list = ["ASIN", "MarketplaceId"]
        for key_normal in key_normal_list:
            # 以下は productを引数にとらず一つだけ取ってきていた名残
            #findobj = self.find_list_matched_product(key_normal)
            findobj = self.products.find_list_matched_product_by_obj(asin_response, key_normal)
            if findobj is None:
                return None  # とれなかったらNG
            else:
                parsedxml[key_normal] = findobj.text

        # 初期値はstrのものを対象
        key_default_str_list = [
            "Title",
            "URL",
            "Amount",
            "Binding",
            "Brand",
            "Color",
            "Department",
            "IsAdultProduct",
        ]
        for key_default in key_default_str_list:
            #findobj = self.find_list_matched_product_default(key_default)
            findobj = self.products.find_list_matched_product_default_by_obj(asin_response, key_default)
            if findobj is None:
                parsedxml[key_default] = ''
            else:
                parsedxml[key_default] = findobj.text

        # dimentionに関する値
        key_dimention_str_list = [
            "Height",
            "Length",
            "Width",
            "Weight",
        ]
        # itemdimentionに関する値
        for key_default in key_dimention_str_list:
            #findobj = self.find_list_matched_product_itemdimention(key_default)
            findobj = self.products.find_list_matched_product_itemdimention_by_obj(
                asin_response, key_default)
            if findobj is None:
                parsedxml["i_" + key_default] = ''
            else:
                parsedxml["i_" + key_default] = findobj.text

        # packagedimentionに関する値
        for key_default in key_dimention_str_list: # リストはitemもpackageも同じ
            #findobj = self.find_list_matched_product_packagedimention(key_default)
            findobj = self.products.find_list_matched_product_packagedimention_by_obj(
                asin_response, key_default)
            if findobj is None:
                parsedxml["p_" + key_default] = ''
            else:
                parsedxml["p_" + key_default] = findobj.text

        # SalesRankに関わるもの
        key_salesrank_list = ["ProductCategoryId", "Rank"]
        i = 0
        #findobj_list = self.find_list_matched_product_all("SalesRank")
        findobj_list = self.products.find_list_matched_product_all_by_obj(
            asin_response, "SalesRank")
        #self.products.logger.info("AmaMws SalesRank findobj_list text:{0}".format(str(findobj_list)))
        if findobj_list:
            for findobj in findobj_list: # SalesRankは3つ
                i += 1
                #self.products.logger.info("AmaMws SalesRank findobj text:{0}".format(str(findobj)))

                for key_normal in key_salesrank_list:
                    finditem = findobj.find(".//2011-10-01:%s" % key_normal, self.products._products_namespace)

                    if finditem is None:
                        parsedxml[str(i) +  "_" + key_normal] = ''
                    else:
                        parsedxml[str(i) +  "_" + key_normal] = finditem.text
        if i < 3:
            parsedxml['3_Rank'] = 0
            parsedxml['3_ProductCategoryId'] = ''
        if i < 2:
            parsedxml['2_Rank'] = 0
            parsedxml['2_ProductCategoryId'] = ''
        if i < 1:
            parsedxml['1_Rank'] = 0
            parsedxml['1_ProductCategoryId'] = ''

        return parsedxml

    def set_db_product(self, parsedxml):
        # ASINは重複をチェックする、しかし商品ごとにぶら下がるので・・やっぱforeignkeyはいらんかも
        asin = parsedxml["ASIN"] if parsedxml["ASIN"] else ''

        if not AsinDetail.objects.filter(asin=parsedxml["ASIN"]).exists():
            self.logger.info("AmaSPApiAsinDetail set_db_product start update_or_create")
            obj, created = AsinDetail.objects.update_or_create(
                asin=parsedxml["ASIN"] if parsedxml["ASIN"] else '',
                title=parsedxml["Title"] if parsedxml["Title"] else '',
                url=parsedxml["URL"] if parsedxml["URL"] else '',
                amount=float(parsedxml["Amount"]) if parsedxml["Amount"] else 0,
                binding=parsedxml["Binding"] if parsedxml["Binding"] else '',
                brand=parsedxml["Brand"] if parsedxml["Brand"] else '',
                color=parsedxml["Color"] if parsedxml["Color"] else '',
                department=parsedxml["Department"] if parsedxml["Department"] else '',
                is_adlt=False if parsedxml["IsAdultProduct"] == "false" else True,
                i_height=float(parsedxml["i_Height"]) if parsedxml["i_Height"] else 0,
                i_length=float(parsedxml["i_Length"]) if parsedxml["i_Length"] else 0,
                i_width=float(parsedxml["i_Width"]) if parsedxml["i_Width"] else 0,
                i_weight=float(parsedxml["i_Weight"]) if parsedxml["i_Weight"] else 0,
                p_height=float(parsedxml["p_Height"]) if parsedxml["p_Height"] else 0,
                p_length=float(parsedxml["p_Length"]) if parsedxml["p_Length"] else 0,
                p_width=float(parsedxml["p_Width"]) if parsedxml["p_Width"] else 0,
                p_weight=float(parsedxml["p_Weight"]) if parsedxml["p_Weight"] else 0,
                rank_cat_1=parsedxml["1_ProductCategoryId"] if parsedxml["1_ProductCategoryId"] else '',
                rank_1=int(parsedxml["1_Rank"]) if parsedxml["1_Rank"] else 0,
                rank_cat_2=parsedxml["2_ProductCategoryId"] if parsedxml["2_ProductCategoryId"] else '',
                rank_2=int(parsedxml["2_Rank"]) if parsedxml["2_Rank"] else 0,
                rank_cat_3=parsedxml["3_ProductCategoryId"] if parsedxml["3_ProductCategoryId"] else '',
                rank_3=int(parsedxml["3_Rank"]) if parsedxml["3_Rank"] else 0,
                bid=self._bid,
                gid=self._gid,
            )
            obj.save()
        self.logger.info("AmaSPApiAsinDetail set_db_product end ")
        return


class AmaSPApiQooAsinDetail(object):

    # Qoo10用ではあるが、SP-APIからAma情報を取ってくるまで。
    # csvでカテゴリなど渡すバージョンは、
    # csvのレコードを QooAsinDetail テーブル db_entryに格納して渡す
    # 本版では、日本のAmazon SP-API を叩いてAsin詳細を取り、
    # ブラックリストのチェックや子Asinのチェックなど行う
    def __init__(self, logger, db_entry=None):
        self.logger = logger

        # 商品単位となるが一時保持用に変数を用意する
        self.parsedxml_list = []
        self._db_entry = db_entry
        self._common_chrome_driver = None

        self.logger.info('AmaSPApiAsinDetail  in. init')

        # SP-APIの登録情報等
        self.upd_csv = []
        self.target_url = "https://api.amazon.com/auth/o2/token"
        self.api_key = "56f37bab855914fd56d8f1b49215e5899d77dec93b81831052a762864a8049ed"
        self.grant_type = "refresh_token"
        self.us_refresh_token = os.getenv("LWA_US_REFRESH_TOKEN", "")
        self.us_client_id = os.getenv("LWA_US_CLIENT_ID", "")
        self.us_client_secret = os.getenv("LWA_US_CLIENT_SECRET", "")
        self.us_aws_access_key = os.getenv("AWS_US_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
        self.us_aws_secret_access_key = os.getenv("AWS_US_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", ""))        # 以下修正まだ！ JPの値を ######
        # ユーザID SPAPI-Qoo-2
        self.jp_refresh_token = os.getenv("LWA_JP_REFRESH_TOKEN", "")
        self.jp_client_id = os.getenv("LWA_JP_CLIENT_ID", "")
        self.jp_client_secret = os.getenv("LWA_JP_CLIENT_SECRET", "")
        self.jp_aws_access_key = os.getenv("AWS_JP_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
        self.jp_aws_secret_access_key = os.getenv("AWS_JP_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", ""))        # 以上修正まだ！ ######
        self.req_headers = None
        self.us_get_url = "https://sellingpartnerapi-na.amazon.com"  # 北米
        self.jp_get_url = "https://sellingpartnerapi-fe.amazon.com" # 日本
        self.access_token = None
        self.us_marketplace = "ATVPDKIKX0DER"  # 北米 ATVPDKIKX0DER  カナダ　A2EUQ1WTGCTBG2 日本 A1VC38T7YXB528
        self.jp_marketplace = "A1VC38T7YXB528"  # 日本 A1VC38T7YXB528
        self.us_host = "sellingpartnerapi-na.amazon.com"  # 北米
        self.jp_host = "sellingpartnerapi-fe.amazon.com"  # 日本
        self.us_region = "us-east-1"  # 北米
        self.jp_region = "us-west-2"  # 日本
        self.service = "execute-api"

        self.jp_credentials = dict(
            refresh_token=self.jp_refresh_token,
            lwa_app_id=self.jp_client_id,
            lwa_client_secret=self.jp_client_secret,
            aws_secret_key=self.jp_aws_secret_access_key,
            aws_access_key=self.jp_aws_access_key,
            #role_arn='arn:aws:iam::000222965326:user/AWS_IAM_SPAPI_Access_User'
        )

        self.us_credentials = dict(
            refresh_token=self.us_refresh_token,
            lwa_app_id=self.us_client_id,
            lwa_client_secret=self.us_client_secret,
            aws_secret_key=self.us_aws_secret_access_key,
            aws_access_key=self.us_aws_access_key,
            #role_arn='arn:aws:iam::000222965326:user/AWS_IAM_SPAPI_Access_User'
        )

        # 保存するパラメータ関連。asin単位で覚えておくイメージ
        self._my_res = None
        self._my_res_cat = None
        self._my_res_seller = None

        self._is_seller_ok = False  # 出品対象としてOKとなる出品者が存在するか。FBAかつ中国セラーなど
        self._is_blacklist_ok = True  # ブラックリストチェック。デフォルトはOK扱いにしておこう

        self._is_blacklist_ok_asin = True  # ASINの判定結果 False:NG判定 True:OK
        self._is_blacklist_ok_img = True  # 画像による判定結果 False:NG判定 True:OK
        self._is_blacklist_ok_keyword = True  # キーワードによる判定結果 False:NG判定 True:OK
        self._blacklist_keyword_flg = 0  # どこでブラックリストに引っかかったかフラグ立てる
        # デフォルト：0000000000　例えばタイトルとブランドがNGなら 00101 とする。
        # 末尾桁→タイトルの判定結果、NGなら１
        # 10の桁→商品説明の判定結果、NGなら１
        # 100の桁→ブランドの判定結果、NGなら１

        self._total_offer_count = 0  # セラー数
        self._buybox_listing_price = 0  # カート価格
        self._buybox_condition = ''  # カート出品状態
        self._buybox_offer_condition = ''  # カートのオファー出品状況 上と似てるが
        self._buybox_shipping_price = 0  # カート送料
        self._buybox_quantitytier = 0  # カートの在庫数
        self._buybox_currency_cd = ''  # カートの通貨コード
        self._shipfrom_country = ''  # カート出品者の所在国
        self._num_offers_amazon = 0  # NumberOfOffersのamazon出品者数
        self._num_offers_merchant = 0  # NumberOfOffersのMerchant出品者数
        self._sales_rank_1 = 0  # ランキングカテゴリ1のランク
        self._sales_rank_2 = 0  # ランキングカテゴリ2のランク
        self._sales_rank_3 = 0  # ランキングカテゴリ2のランク
        self._sales_rank_cat_1 = ''  # ランキングカテゴリ1の名称
        self._sales_rank_cat_2 = ''  # ランキングカテゴリ2の名称
        self._sales_rank_cat_3 = ''  # ランキングカテゴリ3の名称
        self._ok_seller_feedback_rate = 0  # OKと判断されたセラーのfeedback rate
        self._ok_seller_id = ''  # OKと判断されたセラーのid

        # 以下はDBにセットされるパラメータ
        # SP-API より取得するパラメータ
        self._asin = ''
        self._binding = ''
        self._color = ''
        self._is_adlt = ''
        self._brand = ''
        self._label = ''
        self._list_price_amount = 0
        self._list_price_code = ''
        self._manufacturer = ''
        self._package_quantity = 0
        self._part_number = ''
        self._platform = ''
        self._product_group = ''
        self._product_type_name = ''
        self._release_date = ''
        self._publisher = ''
        self._size = ''
        self._small_image = ''
        self._studio = ''
        self._title = ''
        self._i_height = 0
        self._i_length = 0
        self._i_width = 0
        self._i_weight = 0
        self._p_height = 0
        self._p_length = 0
        self._p_width = 0
        self._p_weight = 0
        self._i_height_unit = ''
        self._i_length_unit = ''
        self._i_width_unit = ''
        self._i_weight_unit = ''
        self._p_height_unit = ''
        self._p_length_unit = ''
        self._p_width_unit = ''
        self._p_weight_unit = ''
        self._rank = []
        self._rank_cat = []
        self._actor = ''
        self._aspectRatio = 0
        self._audienceRating = 0
        self._author = ''
        self._backFinding = ''
        self._bandMaterialType = ''
        self._blurayRegion = ''
        self._ceroAgeRating = 0
        self._chainType = ''
        self._claspType = ''
        self._cpuManufacturer = ''
        self._cpuSpeed_value = 0
        self._cpuSpeed_unit = ''
        self._cpuType = ''
        self._creator_value = 0
        self._creator_unit = ''
        self._department = ''
        self._director = ''
        self._displaySize_value = 0
        self._displaySize_unit = ''
        self._edition = ''
        self._episodeSequence = ''
        self._esrbAgeRating = 0
        self._feature = ''
        self._flavor = ''
        self._format_val = ''
        self._gemType = ''
        self._genre = ''
        self._golfClubFlex = ''
        self._golfClubLoft_value = 0
        self._golfClubLoft_unit = ''
        self._handOrientation = ''
        self._hardDiskInterface = ''
        self._hardDiskSize_value = 0
        self._hardDiskSize_unit = ''
        self._hardwarePlatform = ''
        self._hazardousMaterialType = ''
        self._isAutographed = ''
        self._isEligibleForTradeIn = ''
        self._isMemorabilia = ''
        self._issuesPerYear = ''
        self._itemPartNumber = 0
        self._languages = ''
        self._legalDisclaimer = ''
        self._manufacturerMaximumAge_value = 0
        self._manufacturerMaximumAge_unit = ''
        self._manufacturerMinimumAge_value = 0
        self._manufacturerMinimumAge_unit = ''
        self._manufacturerPartsWarrantyDescription = ''
        self._materialType = ''
        self._maximumResolution_value = 0
        self._maximumResolution_unit = ''
        self._mediaType = ''
        self._metalStamp = ''
        self._metalType = ''
        self._model = ''
        self._numberOfDiscs = 0
        self._numberOfIssues = 0
        self._numberOfItems = 0
        self._numberOfPages = 0
        self._numberOfTracks = 0
        self._operatingSystem = ''
        self._opticalZoom_value = 0
        self._opticalZoom_unit = ''
        self._pegiRating = 0
        self._processorCount = 0
        self._productTypeSubcategory = ''
        self._publicationDate = ''
        self._regionCode = ''
        self._ringSize = ''
        self._runningTime_value = 0
        self._runningTime_unit = ''
        self._shaftMaterial = ''
        self._scent = ''
        self._seasonSequence = ''
        self._seikodoProductCode = ''
        self._sizePerPearl = ''
        self._small_image_url = ''
        self._small_image_height_value = 0
        self._small_image_height_units = ''
        self._small_image_width_value = 0
        self._small_image_width_units = ''
        self._subscriptionLength_value = 0
        self._subscriptionLength_unit = ''
        self._systemMemorySize_value = 0
        self._systemMemorySize_unit = ''
        self._systemMemoryType = ''
        self._theatricalReleaseDate = ''
        self._totalDiamondWeight_value = 0
        self._totalDiamondWeight_unit = ''
        self._totalGemWeight_value = 0
        self._totalGemWeight_unit = ''
        self._warranty = ''
        self._weeeTaxValue_amount = 0
        self._weeeTaxValue_currency_code = ''
        self._shipping_size = 0  # 送料区分。商品・パッケージサイズから算出
        # カテゴリ関連
        self._p_cat_id = [''] * 3  # カテゴリID ListOfCategories>Categories>ProductCategoryId
        self._p_cat_name = [''] * 3  # カテゴリID ListOfCategories>Categories>ProductCategoryName
        # ランキング関連
        self._rank_p_cat_id = [''] * 3  # ProductCategoryId
        self._rank_p_cat_rank = [''] * 3  # Rank

        # Amaページよりスクレイピングして取得するパラメータ
        self._product_title = ''
        self._description = ''
        self._p_o_f = [''] * 10  # 商品の詳細 product_overview_features
        self._f_b = [''] * 10  # 商品特徴 feature_bullets
        self._p_d_t_s_th = [''] * 10  # 画面下部_詳細情報（ない場合もある）productDetails_techSpec_section_1
        self._p_d_t_s_td = [''] * 10  # 画面下部_詳細情報（ない場合もある）productDetails_techSpec_section_1
        self._p_d = [''] * 10  # 画面下部_商品の説明 productDescription
        self._p_a_s_m_0 = ''  # 商品詳細コンテンツ
        self._p_a_m_w = [''] * 5  # 商品詳細コンテンツ

        # サムネイル画像
        # span id = a-autoid-10-announce という具合だが、連番はどこからついているか分からない。
        self._img_tag = [''] * 20  # サムネイル画像
        # 関連商品
        self._relation_asin = []
        self._parent_asin = []
        self._marketplace_id = []
        self._seller_id = []
        self._seller_sku = []
        self._rel_color = []
        self._rel_edition = []
        self._rel_flavor = []
        self._rel_gem_type = []
        self._rel_golf_club_flex = []
        self._rel_hand_orientation = []
        self._rel_hardware_platform = []
        self._rel_material_type = []
        self._rel_metal_type = []
        self._rel_model = []
        self._rel_operating_system = []
        self._rel_product_type_subcategory = []
        self._rel_ring_size = []
        self._rel_shaft_material = []
        self._rel_scent = []
        self._rel_size = []
        self._rel_size_per_pearl = []
        self._rel_golf_club_loft_value = []
        self._rel_golf_club_loft_units = []
        self._rel_total_diamond_weight_value = []
        self._rel_total_diamond_weight_units = []
        self._rel_total_gem_weight_value = []
        self._rel_total_gem_weight_units = []
        self._rel_package_quantity = []
        self._rel_item_dimensions_height_value = []
        self._rel_item_dimensions_height_units = []
        self._rel_item_dimensions_length_value = []
        self._rel_item_dimensions_length_units = []
        self._rel_item_dimensions_width_value = []
        self._rel_item_dimensions_width_units = []
        self._rel_item_dimensions_weight_value = []
        self._rel_item_dimensions_weight_units = []

    def spapi_get_participantion(self, region):

        # USから取得する
        #response = Sellers(marketplace=Marketplaces.JP, credentials=self.credentials).get_marketplace_participation()
        if region == 'us':
            response = Sellers(
                marketplace=Marketplaces.US, credentials=self.us_credentials
            ).get_marketplace_participation()
        else:
            # jpでセット
            response = Sellers(
                marketplace=Marketplaces.JP, credentials=self.jp_credentials
            ).get_marketplace_participation()

        self.logger.info('spapi_get_participantion [{}]'.format(response))
        # print(response)
        return

    def spapi_get_catalog_item_for_all(self, region, asin):
        """指定されたasinの情報をSP-API経由（JP）で取得する。
           かつスクレイピングもかけて画像ファイルなどは取得する
           新規のasinに対する情報取得用。もしくはデータ入れ替え時に使うこと。
            キーワードはブラックリストと突き合わせてNG判定も行う。
            結果は QooAsinDetail に格納

        Args:
            region (_type_): 'jp' を指定する。
            asin (_type_): asin コード

        Return:
            True
            False (エラー発生時)
        """

        self.logger.info('---> spapi_get_catalog_item_for_all start.')
        # asin = 'B07WXL5YPW'

        # torでAmazonページをスクレイピングして詳細情報を取ってみよう
        # self.get_ama_src_with_tor()
        # スクレイピングの結果をインスタンス変数にセットするだけ。DB登録はまだ
        # self.set_params_from_scraping_result()

        # Catalog から商品の概要を取得
        self._my_res = self.get_catalog_get_item(asin, region)
        # self.logger.info('---> spapi_get_catalog_item response [{}] type[{}]'.format(my_res,type(my_res)))
        # Identifiers　が以下で取れる　{'MarketplaceASIN': {'MarketplaceId': 'A1VC38T7YXB528', 'ASIN': 'B07WXL5YPW'}}
        #self.logger.info('---> response Identifiers [{}]'.format(my_res['Identifiers']))
        self.logger.info('---> response AttributeSets [{}]'.format(self._my_res['AttributeSets']))

        # Catalog から商品のカテゴリを取得
        self._my_res_cat = self.get_catalog_list_categories(asin, region)
        self.logger.info('---> response list_categories [{}]'.format(self._my_res_cat))

        # Products から商品（新品）の出品者情報を取得
        self._my_res_seller = self.get_products_get_item_offers(asin, region)
        self.logger.info('--->> get_products_get_item_offers response [{}] type[{}]'.format(
            self._my_res_seller, type(self._my_res_seller)))

        # CatalogItems から商品の画像情報を取得 →あまり大した情報が取れないからスルー
        # my_res_catalog_item = self.get_catalogitems_get_catalog_item(asin, region)
        # self.logger.info('--->>> get_catalogitems_get_catalog_item response [{}] type[{}]'.format(
        #    my_res_catalog_item,type(my_res_catalog_item)))

        # APIの呼び出し結果をインスタンス変数にセットするだけ。DB登録はまだ
        self.set_params_from_api_result()

        # 出品者の状況から取り扱いの判定
        self._is_seller_ok = self.chk_seller_ok()

        # ブラックリスト判定
        self._is_blacklist_ok = self.chk_black_list()

        # DB登録
        self.set_db_product()
        self.logger.info('AmaSPApiQooAsinDetail spapi_get_catalog_item_for_all db_set is done.')

        #self.logger.info('spapi_get_catalog_item result_asin [{}]'.format(res["asin"]))
        """
        parsedxml = self.set_asin_data(res)
        if parsedxml:
            # db登録してしまおう
            self.set_db_product(parsedxml)
        """

        self.logger.info('---> spapi_get_catalog_item_for_all end.')
        return True

    def chk_seller_ok(self):
        # 出品者の状況から出品OKかどうかの判定を行う
        self.logger.info('-> chk_seller_ok in.')

        summary = self._my_res_seller.get('Summary', None)
        if summary:
            # offer 数 セラーが１でも今のところはOKとする。
            if summary.get('TotalOfferCount', None):
                self._total_offer_count = int(summary.get('TotalOfferCount', None))

            # まずカート関連情報の保存
            if summary.get('BuyBoxPrices', None):

                # BuyBoxPricesは配列だが、最初にヒットしたものをチェックするか
                for l, buybox in enumerate(summary.get('BuyBoxPrices', None)):

                    self._buybox_listing_price = \
                        buybox['ListingPrice']['Amount']
                    self._buybox_currency_cd = \
                        buybox['ListingPrice']['CurrencyCode']
                    self._buybox_condition = \
                        buybox.get('condition', '')
                    self._buybox_shipping_price = \
                        buybox['Shipping']['Amount']
                    # ※在庫数はココでチェックしてみる。違ってたら他を・・
                    # https://sp-api-docs.saleweaver.com/redoc/productPricingV0.html#operation/getItemOffers
                    self._buybox_quantitytier = \
                        int(buybox.get('quantityTier', 0))

            # 出品者状況の保存
            if summary.get('BuyBoxEligibleOffers', None) is not None:
                for offer in summary.get('BuyBoxEligibleOffers', None):
                    self._buybox_offer_condition = offer.get('condition', None)
                    if offer.get('fulfillmentChannel', None) == 'Amazon':
                        self._num_offers_amazon = offer.get('OfferCount', 0)
                    elif offer.get('fulfillmentChannel', None) == 'Merchant':
                        self._num_offers_merchant = offer.get('OfferCount', 0)

            # ランキングの保存
            if summary.get('SalesRankings', None) is not None:
                for k, ranking in enumerate(
                        summary.get('SalesRankings', None)):
                    self._rank_p_cat_id[k] = ranking.get(
                        'ProductCategoryId', '')
                    self._rank_p_cat_rank[k] = ranking.get('Rank', '')
                    if k >= 2:
                        # 変数は3つまで
                        break

        offers = self._my_res_seller.get('Offers', None)
        if offers:
            # 以下でOKかどうかの判定
            for offer in offers:
                # SubConditionがnewのみ
                self.logger.info('---> offer [{}]'.format(offer))
                subcondition = offer.get('SubCondition', None)
                if subcondition:
                    if subcondition.upper() == 'NEW':
                        # CNのcountryのみOKとする
                        #if offer.get('ShipsFrom', None)['Country'] == 'CN':

                        # セラーのレートは90% 以上にしておきますか
                        if offer.get('SellerFeedbackRating', None)\
                            ['SellerPositiveFeedbackRating'] >= 90:

                            # FBAのみ
                            # うーんIsFulfilledByAmazonでみるか、isPrimeでみるか。どちらかであればOK
                            #if offer.get('IsFulfilledByAmazon', None) == 'True':
                            isprime = offer.get('PrimeInformation', None)
                            if isprime:
                                isprime = isprime.get('IsPrime', None)
                            isfulfilledbyamason = offer.get('IsFulfilledByAmazon', None)
                            if isprime is True\
                                    or isfulfilledbyamason is True:

                                # すぐ発送可能か
                                if offer.get('ShippingTime', None)['availabilityType'] == 'NOW':
                                    # ここまで条件が揃ってたら出品OKとしよう。
                                    # １セラーでも該当したらOK扱いに
                                    self._ok_seller_feedback_rate = \
                                        offer.get('SellerFeedbackRating', None)\
                                            ['SellerPositiveFeedbackRating']
                                    self._ok_seller_id = offer.get('SellerId', None)
                                    self._shipfrom_country = offer.get('ShipsFrom', None)
                                    self.logger.info('-> chk_seller_ok  this item OK to sell.')
                                    return True
                                else:
                                    self.logger.info('-> chk_seller_ok  すぐ発送可能じゃない、NG [{}]'.format(offer.get('ShippingTime', None)['availabilityType']))
                            else:
                                self.logger.info('-> chk_seller_ok  プライムじゃない、NG IsPrime[{}] isFillfullByAma[{}]'.format(isprime, isfulfilledbyamason))
                        else:
                            self.logger.info('-> chk_seller_ok  セラーのレートは90%未満、NG')
                    else:
                        self.logger.info('-> chk_seller_ok  SubConditionがnewなし、NG')
                else:
                    self.logger.info('-> chk_seller_ok  SubConditionなし、NG')
        else:
            self.logger.info('-> chk_seller_ok  offerなし、NG')

        self.logger.info('-> chk_seller_ok  this item NG to sell.')
        return False

    def chk_black_list(self):
        # ブラックリストに含まれるキーワードと
        # 商品タイトル、概要、ブランド、メーカー等との突き合わせ判定を行う
        # 続いてブラックリストASINとのマッチ
        # ret: True (問題なし) False:NG
        self.logger.info('-> chk_black_list in.')

        # 判定結果はそれぞれDBの以下項目にセットする
        # is_blacklist_ok_asin is_blacklist_ok_img is_blacklist_ok_keyword
        # blacklist_keyword_flg (形式は 0000000000 のビット形式)
        # フラグの建て方は以下
        # https://kiwamiden.com/how-to-handle-multiple-flags-with-one-integer
        FLAG_A = 1  # BrandでNG : FLAG_AをON
        FLAG_B = 2  # Publisher : FLAG_BをON
        FLAG_C = 4  # Manufacturer : FLAG_CをON
        FLAG_D = 8  # Label : FLAG_DをON
        FLAG_E = 16  # Title : FLAG_EをON
        FLAG_F = 32  # Title keyword : FLAG_FをON
        FLAG_G = 64  # description keyword : FLAG_GをON
        FLAG_H = 128  # 商品の詳細 product_overview_features : FLAG_HをON
        FLAG_I = 256  # feature_bullets : FLAG_IをON
        FLAG_J = 512  # productDescription : FLAG_JをON
        FLAG_K = 1024  # スクレイピングの結果判断に使う
        FLAG_L = 2048  # スクレイピングの結果判断に使う
        FLAG_M = 4096  # スクレイピングの結果判断に使う
        FLAG_N = 8192  # スクレイピングの結果判断に使う

        # asinとの突き合わせ
        if self._asin == '':
            # asinが未設定はおかしい。処理しない
            self.logger.info('-> chk_black_list asin is blank . something wrong...')
            return False

        # asinのチェック
        if AsinBlacklistAsin.objects.filter(asin=self._asin).exists():
            # blacklist のasinに該当
            self.logger.info('-> ### chk_black_list asin blacklisted. ng [{}]'.format(self._asin))
            self._is_blacklist_ok_asin = False
            return False

        # ブランドのチェック
        # 完全一致でみてるが、in にしよう。__contains
        if AsinBlacklistBrand.objects.filter(brand__contains=self._brand).exists():
            # Brand でNG
            self.logger.info('-> ### chk_black_list brand blacklisted. ng [Brand] [{}]'.format(self._brand))
            self._is_blacklist_ok_keyword = False
            self._blacklist_keyword_flg |= FLAG_A  # BrandでNG : FLAG_AをON
            return False

        if AsinBlacklistBrand.objects.filter(brand__contains=self._publisher).exists():
            # Publisher でNG
            self.logger.info('-> ### chk_black_list brand blacklisted. ng [Publisher] [{}]'.format(self._publisher))
            self._is_blacklist_ok_keyword = False
            self._blacklist_keyword_flg |= FLAG_B  # Publisher : FLAG_BをON
            return False

        if AsinBlacklistBrand.objects.filter(brand__contains=self._manufacturer).exists():
            # Manufacturer でNG
            self.logger.info('-> ### chk_black_list brand blacklisted. ng [Manufacturer] [{}]'.format(self._manufacturer))
            self._is_blacklist_ok_keyword = False
            self._blacklist_keyword_flg |= FLAG_C  # Manufacturer : FLAG_CをON
            return False

        if AsinBlacklistBrand.objects.filter(brand__contains=self._label).exists():
            # Label でNG
            self.logger.info('-> ### chk_black_list brand blacklisted. ng [Label] [{}]'.format(self._label))
            self._is_blacklist_ok_keyword = False
            self._blacklist_keyword_flg |= FLAG_D  # Label : FLAG_DをON
            return False

        # ★タイトルは、inで確認しないとだめかな？ __contains にしよう。
        if AsinBlacklistBrand.objects.filter(brand__contains=self._title).exists():
            # Title でNG
            self.logger.info('-> ### chk_black_list brand blacklisted. ng [Title] [{}]'.format(self._title))
            self._is_blacklist_ok_keyword = False
            self._blacklist_keyword_flg |= FLAG_E  # Title : FLAG_EをON
            return False

        # キーワードのチェック
        # どこかで引っかかったら、以降はチェックせずloop抜けますか
        for tmpkeyword in AsinBlacklistKeyword.objects.all():
            if tmpkeyword.keyword in self._title:
                # Title でNG
                self.logger.info(
                    '-> ### chk_black_list keyword blacklisted. ng [Title] [{}]'.format(tmpkeyword.keyword))
                self._is_blacklist_ok_keyword = False
                self._blacklist_keyword_flg |= FLAG_F  # Title keyword : FLAG_FをON
                return False

            if tmpkeyword.keyword in self._description:
                # description でNG
                self.logger.info(
                    '-> ### chk_black_list keyword blacklisted. ng [description] [{}]'.format(tmpkeyword.keyword))
                self._is_blacklist_ok_keyword = False
                self._blacklist_keyword_flg |= FLAG_G  # description keyword : FLAG_GをON
                return False

            for i in range(10):
                if tmpkeyword.keyword in self._p_o_f[i]:
                    # 商品の詳細 product_overview_features
                    self.logger.info(
                        '-> ### chk_black_list keyword blacklisted. ng [product_overview_features] [{}]'.format(tmpkeyword.keyword))
                    self._is_blacklist_ok_keyword = False
                    self._blacklist_keyword_flg |= FLAG_H  #  商品の詳細 product_overview_features : FLAG_HをON
                    return False
                if tmpkeyword.keyword in self._f_b[i]:
                    # 商品特徴 feature_bullets
                    self.logger.info(
                        '-> ### chk_black_list keyword blacklisted. ng [feature_bullets] [{}]'.format(
                            tmpkeyword.keyword))
                    self._is_blacklist_ok_keyword = False
                    self._blacklist_keyword_flg |= FLAG_I  # feature_bullets : FLAG_IをON
                    return False
                if tmpkeyword.keyword in self._p_d[i]:
                    # 画面下部_商品の説明 productDescription
                    self.logger.info(
                        '-> ### chk_black_list keyword blacklisted. ng [productDescription] [{}]'.format(
                            tmpkeyword.keyword))
                    self._is_blacklist_ok_keyword = False
                    self._blacklist_keyword_flg |= FLAG_J  # productDescription : FLAG_JをON
                    return False

            if tmpkeyword.keyword in self._p_a_s_m_0:
                # 商品詳細コンテンツ_p_a_s_m_0 でNG
                self.logger.info(
                    '-> ### chk_black_list keyword blacklisted. ng [商品詳細コンテンツ_p_a_s_m_0] [{}]'.format(tmpkeyword.keyword))
                self._is_blacklist_ok_keyword = False
                self._blacklist_keyword_flg |= FLAG_K  # description keyword : FLAG_KをON
                return False

            for i in range(5):
                if tmpkeyword.keyword in self._p_a_m_w[i]:
                    # 商品詳細コンテンツ_p_a_m_w
                    self.logger.info(
                        '-> ### chk_black_list keyword blacklisted. ng [商品詳細コンテンツ_p_a_m_w] [{}]'.format(
                            tmpkeyword.keyword))
                    self._is_blacklist_ok_keyword = False
                    self._blacklist_keyword_flg |= FLAG_L  # productDescription : FLAG_LをON
                    return False

            if self._is_blacklist_ok_keyword is False:
                return False

        self.logger.info('-> chk_black_list out.')
        return True

    def get_catalog_list_categories(self, asin, region):
        # Catalog から商品の属するカテゴリを取得
        # asin = 'B07WXL5YPW'
        self.logger.debug('-> get_catalog_list_categories in.')

        if region == 'us':
            response = Catalog(
                MarketplaceId=Marketplaces.US,
                credentials=self.us_credentials,
                ).list_categories(asin)
        else:
            self.logger.debug('-> get_catalog_list_categories 1.')
            my_catalog = Catalog(
                marketplace=Marketplaces.JP,
                credentials=self.jp_credentials,
                )
            response = my_catalog.list_categories(ASIN=asin)
            """
            response = Catalog(
                marketplace=Marketplaces.JP,
                credentials=self.jp_credentials,
                ).list_categories(asin)
            """
        return response()

    def get_catalog_get_item(self, asin, region):
        # Catalog から商品の概要を取得
        # asin = 'B07WXL5YPW'

        # 2022/08/01
        # conoha-01 の、/usr/lib/python3.6/site-packages/sp_api/api/catalog/catalog.py
        # のget_itemを直接変えて、v0 から2022-04-01　に変えた。
        # marketplace は marketplaceIds に変わってる。
        # includedData で取得対象のカテゴリを選べる。
        # https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-v2022-04-01-use-case-guide
        includedData = 'attributes,dimensions,identifiers,images,productTypes,salesRanks,summaries,relationships,vendorDetails'
        if region == 'us':
            response = Catalog(
                MarketplaceId=Marketplaces.US,
                credentials=self.us_credentials,
                ).get_item(asin)
        else:
            """
            response = Catalog(
                MarketplaceId=Marketplaces.JP,
                credentials=self.jp_credentials,
                includedData=includedData,).get_item(asin)
            """
            response = Catalog(
                marketplace=Marketplaces.JP,
                credentials=self.jp_credentials,
                ).get_item(asin)
        return response()

    def get_catalogitems_get_catalog_item(self, asin, region):
        # CatalogItems から商品の画像情報を取得
        # asin = 'B07WXL5YPW'
        if region == 'us':
            response = CatalogItems(
                marketplace=Marketplaces.US, credentials=self.us_credentials
                ).get_catalog_item(asin)
        else:
            response = CatalogItems(
                marketplace=Marketplaces.JP, credentials=self.jp_credentials
                ).get_catalog_item(asin)
        return response()

    def get_products_get_item_offers(self, asin, region):
        # Products から商品（新品）の出品者情報を取得
        if region == 'us':
            response = Products(
                marketplace=Marketplaces.US, credentials=self.us_credentials
                ).get_item_offers(asin=asin, item_condition='New')
        else:
            response = Products(
                marketplace=Marketplaces.JP, credentials=self.jp_credentials
                ).get_item_offers(asin=asin, item_condition='New')
        return response()
        # 出力イメージ
        # {'ASIN': 'B07WXL5YPW',
        #  'status': 'Success',
        #  'ItemCondition': 'NEW',
        #  'Identifier': {'MarketplaceId': 'A1VC38T7YXB528',
        #   'ItemCondition': 'New',
        #   'ASIN': 'B07WXL5YPW'},
        #  'Summary': {'LowestPrices': [{'condition': 'used',
        #     'fulfillmentChannel': 'Merchant',
        #     'LandedPrice': {'CurrencyCode': 'JPY', 'Amount': 25899.0},
        #     'ListingPrice': {'CurrencyCode': 'JPY', 'Amount': 25559.0},
        #     'Shipping': {'CurrencyCode': 'JPY', 'Amount': 340.0},
        #     'Points': {'PointsNumber': 0}},
        #    {'condition': 'new',
        #     'fulfillmentChannel': 'Merchant',
        #     'LandedPrice': {'CurrencyCode': 'JPY', 'Amount': 33480.0},
        #     'ListingPrice': {'CurrencyCode': 'JPY', 'Amount': 33480.0},
        #     'Shipping': {'CurrencyCode': 'JPY', 'Amount': 0.0}}],
        #   'BuyBoxPrices': [{'condition': 'new',
        #     'LandedPrice': {'CurrencyCode': 'JPY', 'Amount': 32640.0},
        #     'ListingPrice': {'CurrencyCode': 'JPY', 'Amount': 32970.0},
        #     'Shipping': {'CurrencyCode': 'JPY', 'Amount': 0.0},
        #     'Points': {'PointsNumber': 330}},
        #    {'condition': 'used',
        #     'LandedPrice': {'CurrencyCode': 'JPY', 'Amount': 28215.0},
        #     'ListingPrice': {'CurrencyCode': 'JPY', 'Amount': 28500.0},
        #     'Shipping': {'CurrencyCode': 'JPY', 'Amount': 0.0},
        #     'Points': {'PointsNumber': 285}}],
        #   'NumberOfOffers': [{'condition': 'used',
        #     'fulfillmentChannel': 'Merchant',
        #     'OfferCount': 44},
        #    {'condition': 'new', 'fulfillmentChannel': 'Amazon', 'OfferCount': 22},
        #    {'condition': 'collectible',
        #     'fulfillmentChannel': 'Merchant',
        #     'OfferCount': 1},
        #    {'condition': 'used', 'fulfillmentChannel': 'Amazon', 'OfferCount': 24},
        #    {'condition': 'new', 'fulfillmentChannel': 'Merchant', 'OfferCount': 40}],
        #   'BuyBoxEligibleOffers': [{'condition': 'used',
        #     'fulfillmentChannel': 'Merchant',
        #     'OfferCount': 40},
        #    {'condition': 'new', 'fulfillmentChannel': 'Amazon', 'OfferCount': 22},
        #    {'condition': 'collectible',
        #     'fulfillmentChannel': 'Merchant',
        #     'OfferCount': 1},
        #    {'condition': 'used', 'fulfillmentChannel': 'Amazon', 'OfferCount': 24},
        #    {'condition': 'new', 'fulfillmentChannel': 'Merchant', 'OfferCount': 37}],
        #   'SalesRankings': [{'ProductCategoryId': 'video_games_display_on_website',
        #     'Rank': 6},
        #    {'ProductCategoryId': '4731379051', 'Rank': 2}],
        #   'ListPrice': {'CurrencyCode': 'JPY', 'Amount': 29980.0},
        #   'CompetitivePriceThreshold': {'CurrencyCode': 'JPY', 'Amount': 32640.0},
        #   'TotalOfferCount': 131},
        #  'Offers': [{'Shipping': {'CurrencyCode': 'JPY', 'Amount': 0.0},
        #    'ListingPrice': {'CurrencyCode': 'JPY', 'Amount': 32970.0},
        #    'ShippingTime': {'maximumHours': 0,
        #     'minimumHours': 0,
        #     'availabilityType': 'NOW'},
        #    'PrimeInformation': {'IsPrime': True, 'IsNationalPrime': True},
        #    'Points': {'PointsNumber': 330},
        #    'SubCondition': 'new',
        #    'SellerId': 'AN1VRQENFRJN5',
        #    'IsFeaturedMerchant': True,
        #    'IsBuyBoxWinner': True,
        #    'IsFulfilledByAmazon': True},
        #   {'Shipping': {'CurrencyCode': 'JPY', 'Amount': 0.0},
        #    'ListingPrice': {'CurrencyCode': 'JPY', 'Amount': 33480.0},
        #    'ShippingTime': {'maximumHours': 24,
        #     'minimumHours': 24,
        #     'availabilityType': 'NOW'},
        #    'SellerFeedbackRating': {'FeedbackCount': 460,
        #     'SellerPositiveFeedbackRating': 96.0},
        #    'ShipsFrom': {'Country': 'JP'},
        #    'PrimeInformation': {'IsPrime': False, 'IsNationalPrime': False},
        #    'SubCondition': 'new',
        #    'SellerId': 'A2DNCF9Q801XL6',
        #    'ConditionNotes': '■新品・未開封です。★複数台まとめ購入歓迎★送料無料。バッテリー強化版。■プライム対応：ヤマト宅急便にてプチプチで梱包し、迅速に発送しております。15時までにご注文の場合即日発送させていただきます。お急ぎ便対応。■店舗併用販売をしていますので売切れの場合はご注文を速やかにキャンセル、ご返金をさせていただきます。■保証印欄は未記入品となります。■お客様のご都合による、返品・出荷後のキャンセルにつきましては原則お受けしておりません、ご了承ください。',
        #    'IsFeaturedMerchant': True,
        #    'IsBuyBoxWinner': False,
        #    'IsFulfilledByAmazon': False},

    def set_asin_data(self, asin_response):

        parsedxml = {}

        key_normal_list = ["ASIN", "MarketplaceId"]
        for key_normal in key_normal_list:
            # 以下は productを引数にとらず一つだけ取ってきていた名残
            #findobj = self.find_list_matched_product(key_normal)
            findobj = self.products.find_list_matched_product_by_obj(asin_response, key_normal)
            if findobj is None:
                return None  # とれなかったらNG
            else:
                parsedxml[key_normal] = findobj.text

        # 初期値はstrのものを対象
        key_default_str_list = [
            "Title",
            "URL",
            "Amount",
            "Binding",
            "Brand",
            "Color",
            "Department",
            "IsAdultProduct",
        ]
        for key_default in key_default_str_list:
            #findobj = self.find_list_matched_product_default(key_default)
            findobj = self.products.find_list_matched_product_default_by_obj(product, key_default)
            if findobj is None:
                parsedxml[key_default] = ''
            else:
                parsedxml[key_default] = findobj.text

        # dimentionに関する値
        key_dimention_str_list = [
            "Height",
            "Length",
            "Width",
            "Weight",
        ]
        # itemdimentionに関する値
        for key_default in key_dimention_str_list:
            #findobj = self.find_list_matched_product_itemdimention(key_default)
            findobj = self.products.find_list_matched_product_itemdimention_by_obj(product, key_default)
            if findobj is None:
                parsedxml["i_" + key_default] = ''
            else:
                parsedxml["i_" + key_default] = findobj.text

        # packagedimentionに関する値
        for key_default in key_dimention_str_list: # リストはitemもpackageも同じ
            #findobj = self.find_list_matched_product_packagedimention(key_default)
            findobj = self.products.find_list_matched_product_packagedimention_by_obj(product, key_default)
            if findobj is None:
                parsedxml["p_" + key_default] = ''
            else:
                parsedxml["p_" + key_default] = findobj.text

        # SalesRankに関わるもの
        key_salesrank_list = ["ProductCategoryId", "Rank"]
        i = 0
        #findobj_list = self.find_list_matched_product_all("SalesRank")
        findobj_list = self.products.find_list_matched_product_all_by_obj(product, "SalesRank")
        #self.products.logger.info("AmaMws SalesRank findobj_list text:{0}".format(str(findobj_list)))
        if findobj_list:
            for findobj in findobj_list:  # SalesRankは3つ
                i += 1
                #self.products.logger.info("AmaMws SalesRank findobj text:{0}".format(str(findobj)))

                for key_normal in key_salesrank_list:
                    finditem = findobj.find(".//2011-10-01:%s" % key_normal, self.products._products_namespace)

                    if finditem is None:
                        parsedxml[str(i) +  "_" + key_normal] = ''
                    else:
                        parsedxml[str(i) +  "_" + key_normal] = finditem.text
        if i < 3:
            parsedxml['3_Rank'] = 0
            parsedxml['3_ProductCategoryId'] = ''
        if i < 2:
            parsedxml['2_Rank'] = 0
            parsedxml['2_ProductCategoryId'] = ''
        if i < 1:
            parsedxml['1_Rank'] = 0
            parsedxml['1_ProductCategoryId'] = ''

        return parsedxml

    # スクレイピングの結果をインスタンス変数にセットするだけ。DB登録はまだ
    def set_params_from_scraping_result(self):
        self.logger.info('-> set_params_from_scraping_result in.')

        dom = lxml.html.fromstring(
            self._common_chrome_driver.driver.page_source
        )
        self.logger.debug('===> start read dom.')

        # タイトル
        self.logger.debug('===> title')
        self._product_title = self.get_adjust_keyword(
            dom.xpath("//span[@id='productTitle']")[0].text)
        self.logger.debug(self._product_title)

        # meta description
        self.logger.debug('===> meta description')
        self._description = self.get_adjust_keyword(
            dom.xpath("//meta[@name='description']")[0].get('content'))
        self.logger.debug(self._description)

        # 商品の詳細（ない場合もある）
        self.logger.debug('===> product detail')
        product_overview_features = dom.xpath("//div[@id='productOverview_feature_div']/div/table/tbody/tr")
        if len(product_overview_features) > 0:
            self.logger.debug('===> product_overview_features len[{}]'.format(len(product_overview_features)))
            for i_0, j_0 in enumerate(product_overview_features):
                j_0_items = j_0.findall('td')
                if len(j_0_items) > 0:
                    for i_0_0, j_0_0 in enumerate(j_0_items):
                        # self.logger.debug('===> j_0_0_items item[{}]'.format(j_0_0))
                        self._p_o_f[i_0_0] = j_0_0.find('span').text  # 商品の詳細 product_overview_features
                        self.logger.debug(
                            '===> product_overview_features item[{}] text[{}]'.format(i_0_0, self._p_o_f[i_0_0]))
                        if i_0_0 >= 9:
                            break

        # 商品特徴
        feature_bullets = dom.xpath("//div[@id='feature-bullets']/ul/li/span")
        self.logger.debug('===> feature_bullets len[{}]'.format(len(feature_bullets)))
        for i_1, j_1 in enumerate(feature_bullets):
            self._f_b[i_1] = j_1.text
            self.logger.debug('===> feature_bullets item[{}] text[{}]'.format(i_1, self._f_b[i_1]))
            if i_1 >= 9:
                break

        # 画面下部_詳細情報（ない場合もある） th と tdはセット
        productDetails_techSpec_section_1 = dom.xpath("//table[@id='productDetails_techSpec_section_1']/tbody/tr")
        if len(productDetails_techSpec_section_1) > 0:
            self.logger.debug(
                '===> productDetails_techSpec_section_1 len[{}]'.format(len(productDetails_techSpec_section_1)))
            for i_2, j_2 in enumerate(productDetails_techSpec_section_1):
                self._p_d_t_s_th[i_2] = j_2.find('th').text
                self._p_d_t_s_td[i_2] = j_2.find('td').text
                self.logger.debug(
                    '===> productDetails_techSpec_section_1 item[{}] th_text[{}]'.format(i_2, self._p_d_t_s_th[i_2]))
                self.logger.debug(
                    '===> productDetails_techSpec_section_1 item[{}] td_text[{}]'.format(i_2, self._p_d_t_s_th[i_2]))
                if i_2 >= 9:
                    break

        # 画面下部_商品の説明
        # https://www.amazon.co.jp/dp/B08FC6K5J2/ref=b2b_gw_d_bmx_gp_41ac8gqo_sccl_5/358-8809905-4375650
        productDescription = self.logger.debug(dom.xpath("//div[@id='productDescription']/p/span"))
        if productDescription and len(productDescription) > 0:
            self.logger.debug('===> productDescription len[{}]'.format(len(productDescription)))
            for i_3, j_3 in enumerate(productDescription):
                self._p_d[i_3] = j_3.text
                self.logger.debug('===> productDescription item[{}] text[{}]'.format(i_3, self._p_d[i_3]))
                if i_3 >= 9:
                    break

        # サムネイル画像
        # span id = a-autoid-10-announce という具合だが、連番はどこからついているか分からない。
        img_tags = dom.xpath("//span[contains(@id,'a-autoid-') and contains(@id,'-announce')]/img/@src")
        if len(img_tags) > 0:
            self.logger.debug('===> img_tags len[{}]'.format(len(img_tags)))
            for i_4, j_4 in enumerate(img_tags):
                self.logger.debug('===> img_tags item[{}] td_text[{}]'.format(i_4, j_4))
                chk_str = re.sub(r'(.+?_AC_)(.+?)(_.jpg)', r'\1L1500\3', j_4)
                self._img_tag[i_4] = chk_str
                self.logger.debug('===> img_tags chk_str[{}]'.format(self._img_tag[i_4]))
                if i_4 >= 19:
                    break

        self.logger.info('-> set_params_from_scraping_result out.')
        return

    # 文字列から不要文字を削除する
    def get_adjust_keyword(self, moto_key):
        """
        半角スペースで分割し直すなら以下必要だが
        tmp_list_moto = moto_key.split(" ")
        tmp_list_unique = list(set(tmp_list_moto))
        ret_str = ' '.join(tmp_list_unique)
        """

        # 不要文字は削除
        ret_str = moto_key.replace('\'s ',' ')
        ret_str = ret_str.replace('\'s','')
        ret_str = re.sub('Amazon.co.jp: ', "", ret_str)
        return ret_str

    def set_params_from_api_result(self):
        self.logger.info('-> set_params_from_api_result in.')

        # ASIN
        self._asin = self._my_res["Identifiers"]["MarketplaceASIN"]["ASIN"]
        self.logger.info('---> asin [{}]'.format(self._asin))

        # AttributeSets
        # 中身はこれ
        # https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-v0-reference#attributesetlist
        for attribute in self._my_res['AttributeSets']:
            self.logger.info('---> param AttributeSets [{}]'.format(attribute))
            self._actor = ''
            if attribute.get('Actor', None):
                self._actor = attribute.get('Actor', '')[0]
            self._artist = ''
            if attribute.get('Artist', None):
                self._artist = attribute.get('Artist', '')[0]
            self._aspectRatio = float(attribute.get('AspectRatio', 0))
            self._audienceRating = float(attribute.get('AudienceRating', 0))
            self._author = ''
            if attribute.get('Author', None):
                self._author = attribute.get('Author', '')[0]
            self._backFinding = attribute.get('BackFinding', '')
            self._bandMaterialType = attribute.get('BandMaterialType', '')
            self._binding = attribute.get('Binding', '')
            self._blurayRegion = attribute.get('BlurayRegion', '')
            self._brand = attribute.get('Brand', '')
            self._ceroAgeRating = float(attribute.get('CeroAgeRating', 0))
            self._chainType = attribute.get('ChainType', '')
            self._claspType = attribute.get('ClaspType', '')
            self._color = attribute.get('Color', '')
            self._cpuManufacturer = attribute.get('cpuManufacturer', '')
            if attribute.get('CpuSpeed', None):
                self._cpuSpeed_value = float(attribute.get('CpuSpeed', 0).get('value'))
                self._cpuSpeed_unit = attribute.get('CpuSpeed', '').get('Units')
            self._cpuType = attribute.get('CpuType', '')
            if attribute.get('Creator', None):
                self._creator_value = attribute.get('Creator', '').get('value')
                self._creator_unit = attribute.get('Creator', '').get('Role')
            self._department = attribute.get('Department', '')
            self._director = ''
            if attribute.get('Director', None):
                self._director = attribute.get('Director', '')[0]
            if attribute.get('DisplaySize', None):
                self._displaySize_value = float(attribute.get('DisplaySize', 0).get('value'))
                self._displaySize_unit = attribute.get('DisplaySize', '').get('Units')
            self._edition = attribute.get('Edition', '')
            self._episodeSequence = attribute.get('EpisodeSequence', '')
            self._esrbAgeRating = float(attribute.get('EsrbAgeRating', 0))
            if attribute.get('Feature', None):
                self._feature = attribute.get('Feature', '')
            self._flavor = attribute.get('Flavor', '')
            if attribute.get('Format', None):
                self._format_val = attribute.get('Format', '')
            if attribute.get('GemType', None):
                self._gemType = attribute.get('GemType', '')
            self._genre = attribute.get('Genre', '')
            self._golfClubFlex = attribute.get('GolfClubFlex', '')
            if attribute.get('GolfClubLoft', None):
                self._golfClubLoft_value = float(attribute.get('GolfClubLoft', 0).get('value'))
                self._golfClubLoft_unit = attribute.get('GolfClubLoft', '').get('Units')
            self._handOrientation = attribute.get('HandOrientation', '')
            self._hardDiskInterface = attribute.get('HardDiskInterface', '')
            if attribute.get('HardDiskSize', None):
                self._hardDiskSize_value = float(attribute.get('HardDiskSize', 0).get('value'))
                self._hardDiskSize_unit = attribute.get('HardDiskSize', '').get('Units')
            self._hardwarePlatform = attribute.get('HardwarePlatform', '')
            self._hazardousMaterialType = attribute.get('HazardousMaterialType', '')
            self._is_adlt = attribute.get('IsAdultProduct', False)
            self._isAutographed = attribute.get('IsAutographed', False)
            self._isEligibleForTradeIn = attribute.get('IsEligibleForTradeIn', False)
            self._isMemorabilia = attribute.get('IsMemorabilia', False)
            self._issuesPerYear = attribute.get('IssuesPerYear', '')
            self._itemPartNumber = float(attribute.get('ItemPartNumber', 0))
            self._label = attribute.get('Label', '')
            if attribute.get('Languages', None):
                self._languages = attribute.get('Languages', '')[0]
            self._legalDisclaimer = attribute.get('LegalDisclaimer', '')
            if attribute.get('ListPrice', None):
                self._list_price_amount = attribute.get('ListPrice', 0).get('Amount', 0)
                self._list_price_code = attribute.get('ListPrice', '').get('CurrencyCode', '')
            self._manufacturer = attribute.get('Manufacturer', '')
            if attribute.get('ManufacturerMaximumAge', None):
                self._manufacturerMaximumAge_value = float(attribute.get('ManufacturerMaximumAge', 0).get('value'))
                self._manufacturerMaximumAge_unit = attribute.get('ManufacturerMaximumAge', '').get('Units')
            if attribute.get('ManufacturerMinimumAge', None):
                self._manufacturerMinimumAge_value = float(attribute.get('ManufacturerMinimumAge', 0).get('value'))
                self._manufacturerMinimumAge_unit = attribute.get('ManufacturerMinimumAge', '').get('Units')
            self._manufacturerPartsWarrantyDescription = attribute.get('ManufacturerPartsWarrantyDescription', '')
            if attribute.get('MaterialType', None):
                self._materialType = attribute.get('MaterialType', '')[0]
            if attribute.get('MaximumResolution', None):
                self._maximumResolution_value = float(attribute.get('MaximumResolution', 0).get('value'))
                self._maximumResolution_unit = attribute.get('MaximumResolution', '').get('Units')
            if attribute.get('MediaType', None):
                self._mediaType = attribute.get('MediaType', '')[0]
            self._metalStamp = attribute.get('MetalStamp', '')
            self._metalType = attribute.get('MetalType', '')
            self._model = attribute.get('Model', '')
            self._numberOfDiscs = int(attribute.get('NumberOfDiscs', 0))
            self._numberOfIssues = int(attribute.get('NumberOfIssues', 0))
            self._numberOfItems = int(attribute.get('NumberOfItems', 0))
            self._numberOfPages = int(attribute.get('NumberOfPages', 0))
            self._numberOfTracks = int(attribute.get('NumberOfTracks', 0))
            if attribute.get('OperatingSystem', None):
                self._operatingSystem = attribute.get('OperatingSystem', '')[0]
            if attribute.get('OpticalZoom', None):
                self._opticalZoom_value = float(attribute.get('OpticalZoom', 0).get('value'))
                self._opticalZoom_unit = attribute.get('OpticalZoom', '').get('Units')
            self._package_quantity = int(attribute.get('PackageQuantity', 0))
            self._part_number = attribute.get('PartNumber', 0)
            self._pegiRating = float(attribute.get('PegiRating', 0))
            self._platform = attribute.get('Platform', '')
            self._processorCount = int(attribute.get('ProcessorCount', 0))
            self._product_group = attribute.get('ProductGroup', '')
            self._product_type_name = attribute.get('ProductTypeName', '')
            self._productTypeSubcategory = attribute.get('ProductTypeSubcategory', '')
            self._publicationDate = attribute.get('PublicationDate', '')
            self._publisher = attribute.get('Publisher', '')
            self._regionCode = attribute.get('RegionCode', '')
            self._release_date = attribute.get('ReleaseDate', '')
            self._ringSize = attribute.get('RingSize', '')
            if attribute.get('RunningTime', None):
                self._runningTime_value = float(attribute.get('RunningTime', 0).get('value'))
                self._runningTime_unit = attribute.get('RunningTime', '').get('Units')
            self._shaftMaterial = attribute.get('ShaftMaterial', '')
            self._scent = attribute.get('Scent', '')
            self._seasonSequence = attribute.get('SeasonSequence', '')
            self._seikodoProductCode = attribute.get('SeikodoProductCode', '')
            self._size = attribute.get('Size', '')
            self._sizePerPearl = attribute.get('SizePerPearl', '')
            if attribute.get('SmallImage', None):
                self._small_image_url = attribute.get('SmallImage', '').get('URL', '')
                self._small_image_height_value = float(attribute.get('SmallImage', '').get('Height', 0).get('value'))
                self._small_image_height_units = attribute.get('SmallImage', '').get('Height', 0).get('Units')
                self._small_image_width_value = float(attribute.get('SmallImage', '').get('Width', 0).get('value'))
                self._small_image_width_units = attribute.get('SmallImage', '').get('Width', 0).get('Units')
            self._studio = attribute.get('Studio', '')
            if attribute.get('SubscriptionLength', None):
                self._subscriptionLength_value = float(attribute.get('SubscriptionLength', 0).get('value'))
                self._subscriptionLength_unit = attribute.get('SubscriptionLength', '').get('Units')
            if attribute.get('SystemMemorySize', None):
                self._systemMemorySize_value = float(attribute.get('SystemMemorySize', 0).get('value'))
                self._systemMemorySize_unit = attribute.get('SystemMemorySize', '').get('Units')
            self._systemMemoryType = attribute.get('SystemMemoryType', '')
            self._theatricalReleaseDate = attribute.get('TheatricalReleaseDate', '')
            self._title = attribute.get('Title', '')
            if attribute.get('TotalDiamondWeight', None):
                self._totalDiamondWeight_value = float(attribute.get('TotalDiamondWeight', 0).get('value'))
                self._totalDiamondWeight_unit = attribute.get('TotalDiamondWeight', '').get('Units')
            if attribute.get('TotalGemWeight', None):
                self._totalGemWeight_value = float(attribute.get('TotalGemWeight', 0).get('value'))
                self._totalGemWeight_unit = attribute.get('TotalGemWeight', '').get('Units')
            self._warranty = attribute.get('Warranty', '')
            if attribute.get('WeeeTaxValue', None):
                self._weeeTaxValue_amount = float(attribute.get('WeeeTaxValue', 0).get('Amount'))
                self._weeeTaxValue_currency_code = attribute.get('WeeeTaxValue', '').get('CurrencyCode')

            i_dim = attribute.get('ItemDimensions', None)
            if i_dim is not None:
                i_dim_h = i_dim.get('Height', None)
                if i_dim_h is not None:
                    self._i_height = float(i_dim_h.get('value', 0))
                    self._i_height_unit = i_dim_h.get('Units', '')
                i_dim_l = i_dim.get('Length', None)
                if i_dim_l is not None:
                    self._i_length = float(i_dim_l.get('value', 0))
                    self._i_length_unit = i_dim_l.get('Units', '')
                i_dim_wi = i_dim.get('Width', None)
                if i_dim_wi is not None:
                    self._i_width = float(i_dim_wi.get('value', 0))
                    self._i_width_unit = i_dim_wi.get('Units', '')
                i_dim_we = i_dim.get('Weight', None)
                if i_dim_we is not None:
                    self._i_weight = float(i_dim_we.get('value', 0))
                    self._i_weight_unit = i_dim_we.get('Units', '')
            p_dim = attribute.get('PackageDimensions', None)
            if p_dim is not None:
                p_dim_h = p_dim.get('Height', None)
                if p_dim_h is not None:
                    self._p_height = float(p_dim_h.get('value', 0))
                    self._p_height_unit = p_dim_h.get('Units', '')
                p_dim_l = p_dim.get('Length', None)
                if p_dim_l is not None:
                    self._p_length = float(p_dim_l.get('value', 0))
                    self._p_length_unit = p_dim_l.get('Units', '')
                p_dim_wi = p_dim.get('Width', None)
                if p_dim_wi is not None:
                    self._p_width = float(p_dim_wi.get('value', 0))
                    self._p_width_unit = p_dim_wi.get('Units', '')
                p_dim_we = p_dim.get('Weight', None)
                if p_dim_we is not None:
                    self._p_weight = float(p_dim_we.get('value', 0))
                    self._p_weight_unit = p_dim_we.get('Units', '')
            self.logger.info('---> attribute Binding [{}]'.format(self._binding))

        # カテゴリ
        if self._my_res_cat:
            for i, res_cat_obj in enumerate(self._my_res_cat):
                # parentもほんとは取れるがまた後ほど。
                self._p_cat_id[i] = res_cat_obj.get('ProductCategoryId', '')
                self._p_cat_name[i] = res_cat_obj.get('ProductCategoryName', '')
                if i >= 2:
                    # 変数は3つまで
                    break

        # ランキング関連
        self._rank = [0] * 3
        self._rank_cat = [''] * 3
        if self._my_res.get('SalesRankings', None):
            for j, rank in enumerate(self._my_res['SalesRankings']):
                self._rank[j] = rank.get('Rank', 0)
                self._rank_cat[j] = rank.get('ProductCategoryId', 0)
                if j >= 2:
                    break

        # 関連商品
        if self._my_res.get('Relationships', None):
            for k, relation in enumerate(self._my_res['Relationships']):
                self.logger.debug('---> Relationships [{}][{}]'.format(k, relation))
                self._parent_asin.append(relation.get('', ''))
                identifiers = relation.get('Identifiers', None)
                if identifiers is not None:
                    self._relation_asin.append(relation['Identifiers']['MarketplaceASIN']['ASIN'])
                    self._marketplace_id.append(relation['Identifiers']['MarketplaceASIN']['MarketplaceId'])
                    skuidentifier = identifiers.get('SKUIdentifier', None)
                    if skuidentifier is not None:
                        self._seller_id.append(relation['Identifiers']['SKUIdentifier']['SellerId'])
                        self._seller_sku.append(relation['Identifiers']['SKUIdentifier']['SellerSKU'])
                    else:
                        self._seller_id.append('')
                        self._seller_sku.append('')
                else:
                    self._relation_asin.append('')
                    self._marketplace_id.append('')
                    self._seller_id.append('')
                    self._seller_sku.append('')
                self._rel_color.append(relation.get('Color', ''))
                self._rel_edition.append(relation.get('Edition', ''))
                self._rel_flavor.append(relation.get('Flavor', ''))
                self._rel_gem_type.append(relation.get('GemType', ''))
                self._rel_golf_club_flex.append(relation.get('GolfClubFlex', ''))
                self._rel_hand_orientation.append(relation.get('HandOrientation', ''))
                self._rel_hardware_platform.append(relation.get('HardwarePlatform', ''))
                tmp_material_types = relation.get('MaterialType', None)
                material_type_arr = [''] * 3
                if tmp_material_types:
                    for k_1, tmp_material_type in enumerate(tmp_material_types):
                        material_type_arr[k_1] = tmp_material_type
                        if k_1 >= 2:
                            break
                self._rel_material_type.append(material_type_arr)
                self._rel_metal_type.append(relation.get('MetalType', ''))
                self._rel_model.append(relation.get('Model', ''))
                tmp_operating_systems = relation.get('OperatingSystem', None)
                operating_system_arr = [''] * 3
                if tmp_operating_systems is not None:
                    for k_2, tmp_operating_system in enumerate(tmp_operating_systems):
                        operating_system_arr[k_2] = tmp_operating_systems
                        if k_2 >= 2:
                            break
                self._rel_operating_system.append(operating_system_arr)
                self._rel_product_type_subcategory.append(relation.get('ProductTypeSubcategory', ''))
                self._rel_ring_size.append(relation.get('RingSize', ''))
                self._rel_shaft_material.append(relation.get('ShaftMaterial', ''))
                self._rel_scent.append(relation.get('Scent', ''))
                self._rel_size.append(relation.get('Size', ''))
                self._rel_size_per_pearl.append(relation.get('SizePerPearl', ''))
                if relation.get('GolfClubLoft', None):
                    self._rel_golf_club_loft_value.append(relation['GolfClubLoft']['value'])
                    self._rel_golf_club_loft_units.append(relation['GolfClubLoft']['Units'])
                else:
                    self._rel_golf_club_loft_value.append('')
                    self._rel_golf_club_loft_units.append('')
                if relation.get('TotalDiamondWeight', None):
                    self._rel_total_diamond_weight_value.append(relation['TotalDiamondWeight']['value'])
                    self._rel_total_diamond_weight_units.append(relation['TotalDiamondWeight']['Units'])
                else:
                    self._rel_total_diamond_weight_value.append('')
                    self._rel_total_diamond_weight_units.append('')
                if relation.get('TotalGemWeight', None):
                    self._rel_total_gem_weight_value.append(relation['TotalGemWeight']['value'])
                    self._rel_total_gem_weight_units.append(relation['TotalGemWeight']['Units'])
                else:
                    self._rel_total_gem_weight_value.append('')
                    self._rel_total_gem_weight_units.append('')
                self._rel_package_quantity.append(int(relation.get('PackageQuantity', 0)))
                if relation.get('ItemDimensions', None):
                    if relation['ItemDimensions'].get('Height', None):
                        self._rel_item_dimensions_height_value.append(relation['ItemDimensions']['Height']['value'])
                        self._rel_item_dimensions_height_units.append(relation['ItemDimensions']['Height']['Units'])
                    else:
                        self._rel_item_dimensions_height_value.append('')
                        self._rel_item_dimensions_height_units.append('')
                    if relation['ItemDimensions'].get('Length', None):
                        self._rel_item_dimensions_length_value.append(relation['ItemDimensions']['Length']['value'])
                        self._rel_item_dimensions_length_units.append(relation['ItemDimensions']['Length']['Units'])
                    else:
                        self._rel_item_dimensions_length_value.append('')
                        self._rel_item_dimensions_length_units.append('')
                    if relation['ItemDimensions'].get('Width', None):
                        self._rel_item_dimensions_width_value.append(relation['ItemDimensions']['Width']['value'])
                        self._rel_item_dimensions_width_units.append(relation['ItemDimensions']['Width']['Units'])
                    else:
                        self._rel_item_dimensions_width_value.append('')
                        self._rel_item_dimensions_width_units.append('')
                    if relation['ItemDimensions'].get('Weight', None):
                        self._rel_item_dimensions_weight_value.append(relation['ItemDimensions']['Weight']['value'])
                        self._rel_item_dimensions_weight_units.append(relation['ItemDimensions']['Weight']['Units'])
                    else:
                        self._rel_item_dimensions_weight_value.append('')
                        self._rel_item_dimensions_weight_units.append('')
                else:
                    self._rel_item_dimensions_height_value.append('')
                    self._rel_item_dimensions_height_units.append('')
                    self._rel_item_dimensions_length_value.append('')
                    self._rel_item_dimensions_length_units.append('')
                    self._rel_item_dimensions_width_value.append('')
                    self._rel_item_dimensions_width_units.append('')
                    self._rel_item_dimensions_weight_value.append('')
                    self._rel_item_dimensions_weight_units.append('')

        self.logger.info('-> set_params_from_api_result out.')
        return

    def get_shipping_size(self):
        # 送料区分を算出しよう。
        # ロジスピに必要なサイズ区分は以下。
        # https://logisp.jp/price/d2c/
        # 1: ネコポス (高さ2.5cm以下、合計 60サイズ未満)
        # 2: 60サイズ
        # 3: 80サイズ
        # 4: 100サイズ
        # 5: 120サイズ
        # 6: 140サイズ
        # 7: 160サイズ
        # 8: 180サイズ（ロジスピは取り扱いない）
        # 99: サイズNG
        self._shipping_size = 0
        total_size = 0

        # 高さ i_height かp_height 高い方
        my_height = self._i_height if self._i_height > self._p_height else self._p_height
        my_length = self._i_length if self._i_length > self._p_length else self._p_length
        my_width = self._i_width if self._i_width > self._p_width else self._p_width

        # インチだったらセンチに換算 1インチは2.54cm
        if self._i_height_unit == 'inches' or self._p_height_unit == 'inches':
            my_height = my_height * 2.54
        if self._i_length_unit == 'inches' or self._p_length_unit == 'inches':
            my_length = my_length * 2.54
        if self._i_width_unit == 'inches' or self._p_width_unit == 'inches':
            my_width = my_width * 2.54

        # ネコポスサイズの判定　薄いものはあまり余白を考えなくてよいかも
        if my_height <= 2:  # 高さ2cm以下のを考慮に入れよう
            # 余白は合計に5cm足すか
            total_size = sum([my_height, my_length, my_width, 5])
        else:
            tmp_size = sum([my_height, my_length, my_width])
            if tmp_size <= 80:
                # 80サイズ程度なら余白を少し控えめ
                total_size = sum([my_height, my_length, my_width, 10])
            else:
                total_size = sum([my_height, my_length, my_width, 15])

        # 区分設定
        if total_size <= 60 and my_height <= 2:
            # ネコポス
            self._shipping_size = 1
        elif total_size <= 60 and my_height > 2:
            # 2: 60サイズ
            self._shipping_size = 2
        elif total_size > 60 and total_size <= 80:
            # 3: 80サイズ
            self._shipping_size = 3
        elif total_size > 80 and total_size <= 100:
            # 4: 100サイズ
            self._shipping_size = 4
        elif total_size > 100 and total_size <= 120:
            # 5: 120サイズ
            self._shipping_size = 5
        elif total_size > 120 and total_size <= 140:
            # 6: 140サイズ
            self._shipping_size = 6
        elif total_size > 140 and total_size <= 160:
            # 7: 160サイズ
            self._shipping_size = 7
        elif total_size > 160 and total_size <= 180:
            # 8: 180サイズ
            self._shipping_size = 8
        else:
            # サイズNG
            self._shipping_size = 99

        return

    def set_db_product(self):

        self.logger.info('-> AmaSPApiAsinDetail set_db_product in.')

        # この時点でパッケージ・商品サイズから送料区分を算出しよう
        self.get_shipping_size()

        self.logger.info("AmaSPApiAsinDetail set_db_product start update_or_create")
        # obj, created = QooAsinDetail.objects.update_or_create(
        obj = QooAsinDetail.objects.get(asin=self._asin)
        if obj:
            obj.title = self._title
            obj.url = ''
            obj.amount = self._buybox_quantitytier
            obj.binding = self._binding
            obj.brand = self._brand
            obj.color = self._color
            obj.department = self._department
            obj.is_adlt = self._is_adlt
            obj.i_height = self._i_height
            obj.i_height_unit = self._i_height_unit
            obj.i_length = self._i_length
            obj.i_length_unit = self._i_length_unit
            obj.i_width = self._i_width
            obj.i_width_unit = self._i_width_unit
            obj.i_weight = self._i_weight
            obj.i_weight_unit = self._i_weight_unit
            obj.p_height = self._p_height
            obj.p_height_unit = self._p_height_unit
            obj.p_length = self._p_length
            obj.p_length_unit = self._p_length_unit
            obj.p_width = self._p_width
            obj.p_width_unit = self._p_width_unit
            obj.p_weight = self._p_weight
            obj.p_weight_unit = self._p_weight_unit
            obj.rank_cat_1 = self._rank_cat[0]
            obj.rank_1 = int(self._rank[0])
            obj.rank_cat_2 = self._rank_cat[1]
            obj.rank_2 = int(self._rank[1])
            obj.rank_cat_3 = self._rank_cat[2]
            obj.rank_3 = int(self._rank[2])
            obj.actor = self._actor
            obj.aspectRatio = self._aspectRatio
            obj.audienceRating = self._audienceRating
            obj.author = self._author
            obj.backFinding = self._backFinding
            obj.bandMaterialType = self._bandMaterialType
            obj.blurayRegion = self._blurayRegion
            obj.ceroAgeRating = self._ceroAgeRating
            obj.chainType = self._chainType
            obj.claspType = self._claspType
            obj.cpuManufacturer = self._cpuManufacturer
            obj.cpuSpeed_value = self._cpuSpeed_value
            obj.cpuSpeed_unit = self._cpuSpeed_unit
            obj.cpuType = self._cpuType
            obj.creator_value = self._creator_value
            obj.creator_unit = self._creator_unit
            obj.director = self._director
            obj.displaySize_value = self._displaySize_value
            obj.displaySize_unit = self._displaySize_unit
            obj.edition = self._edition
            obj.episodeSequence = self._episodeSequence
            obj.esrbAgeRating = self._esrbAgeRating
            obj.feature = self._feature
            obj.flavor = self._flavor
            obj.format_val = self._format_val
            obj.gemType = self._gemType
            obj.genre = self._genre
            obj.golfClubFlex = self._golfClubFlex
            obj.golfClubLoft_value = self._golfClubLoft_value
            obj.golfClubLoft_unit = self._golfClubLoft_unit
            obj.handOrientation = self._handOrientation
            obj.hardDiskInterface = self._hardDiskInterface
            obj.hardDiskSize_value = self._hardDiskSize_value
            obj.hardDiskSize_unit = self._hardDiskSize_unit
            obj.hardwarePlatform = self._hardwarePlatform
            obj.hazardousMaterialType = self._hazardousMaterialType
            obj.isAutographed = self._isAutographed
            obj.isEligibleForTradeIn = self._isEligibleForTradeIn
            obj.isMemorabilia = self._isMemorabilia
            obj.issuesPerYear = self._issuesPerYear
            obj.itemPartNumber = self._itemPartNumber
            obj.languages = self._languages
            obj.legalDisclaimer = self._legalDisclaimer
            obj.manufacturerMaximumAge_value = self._manufacturerMaximumAge_value
            obj.manufacturerMaximumAge_unit = self._manufacturerMaximumAge_unit
            obj.manufacturerMinimumAge_value = self._manufacturerMinimumAge_value
            obj.manufacturerMinimumAge_unit = self._manufacturerMinimumAge_unit
            obj.manufacturerPartsWarrantyDescription = self._manufacturerPartsWarrantyDescription
            obj.materialType = self._materialType
            obj.maximumResolution_value = self._maximumResolution_value
            obj.maximumResolution_unit = self._maximumResolution_unit
            obj.mediaType = self._mediaType
            obj.metalStamp = self._metalStamp
            obj.metalType = self._metalType
            obj.model = self._model
            obj.numberOfDiscs = self._numberOfDiscs
            obj.numberOfIssues = self._numberOfIssues
            obj.numberOfItems = self._numberOfItems
            obj.numberOfPages = self._numberOfPages
            obj.numberOfTracks = self._numberOfTracks
            obj.operatingSystem = self._operatingSystem
            obj.opticalZoom_value = self._opticalZoom_value
            obj.opticalZoom_unit = self._opticalZoom_unit
            obj.pegiRating = self._pegiRating
            obj.processorCount = self._processorCount
            obj.productTypeSubcategory = self._productTypeSubcategory
            obj.publicationDate = self._publicationDate
            obj.regionCode = self._regionCode
            obj.ringSize = self._ringSize
            obj.runningTime_value = self._runningTime_value
            obj.runningTime_unit = self._runningTime_unit
            obj.shaftMaterial = self._shaftMaterial
            obj.scent = self._scent
            obj.seasonSequence = self._seasonSequence
            obj.seikodoProductCode = self._seikodoProductCode
            obj.sizePerPearl = self._sizePerPearl
            obj.label = self._label
            obj.list_price_amount = self._list_price_amount
            obj.list_price_code = self._list_price_code
            obj.manufacturer = self._manufacturer
            obj.package_quantity = self._package_quantity
            obj.part_number = self._part_number
            obj.platform = self._platform
            obj.product_group = self._product_group
            obj.product_type_name = self._product_type_name
            obj.release_date = self._release_date
            obj.publisher = self._publisher
            obj.size = self._size
            obj.small_image_url = self._small_image_url
            obj.small_image_height_value = self._small_image_height_value
            obj.small_image_height_units = self._small_image_height_units
            obj.small_image_width_value = self._small_image_width_value
            obj.small_image_width_units = self._small_image_width_units
            obj.subscriptionLength_value = self._subscriptionLength_value
            obj.subscriptionLength_unit = self._subscriptionLength_unit
            obj.systemMemorySize_value = self._systemMemorySize_value
            obj.systemMemorySize_unit = self._systemMemorySize_unit
            obj.systemMemoryType = self._systemMemoryType
            obj.theatricalReleaseDate = self._theatricalReleaseDate
            obj.totalDiamondWeight_value = self._totalDiamondWeight_value
            obj.totalDiamondWeight_unit = self._totalDiamondWeight_unit
            obj.totalGemWeight_value = self._totalGemWeight_value
            obj.totalGemWeight_unit = self._totalGemWeight_unit
            obj.warranty = self._warranty
            obj.weeeTaxValue_amount = self._weeeTaxValue_amount
            obj.weeeTaxValue_currency_code = self._weeeTaxValue_currency_code
            obj.studio = self._studio
            # obj.ここから以下は格納できているか確認必
            # カテゴリは ListOfCategories Categories ProductCategoryId
            # ProductCategoryName, parent などから取れそう
            # https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-v0-reference#attributesetlist
            obj.p_cat_id_0 = self._p_cat_id[0]
            obj.p_cat_id_1 = self._p_cat_id[1]
            obj.p_cat_id_2 = self._p_cat_id[2]
            obj.p_cat_name_0 = self._p_cat_name[0]
            obj.p_cat_name_1 = self._p_cat_name[1]
            obj.p_cat_name_2 = self._p_cat_name[2]
            obj.buybox_listing_price = int(self._buybox_listing_price) # カート価格
            obj.buybox_currency_cd = self._buybox_currency_cd  # カード通貨コー
            obj.buybox_condition = self._buybox_condition  # カート出品状
            obj.buybox_shipping_price = self._buybox_shipping_price  # カート送
            obj.shipfrom_country = self._shipfrom_country  # 出品者の所在
            obj.num_offers_amazon = self._num_offers_amazon  # NumberOfOffersのamazon出品者
            obj.num_offers_merchant = self._num_offers_merchant  # NumberOfOffersのMerchant出品者
            obj.ok_seller_feedback_rate = self._ok_seller_feedback_rate  # OKと判断されたセラーのfeedback rat
            obj.ok_seller_id = self._ok_seller_id  # OKと判断されたセラーのi
            obj.is_seller_ok = self._is_seller_ok  # 出品OKかどうかの出品者状態による判断
            obj.is_blacklist_ok = self._is_blacklist_ok  # 出品OKかどうかのブラックリスト判定結果
            obj.is_blacklist_ok_asin = self._is_blacklist_ok_asin  # ASINの判定結果 False:NG判定 True:OK
            obj.is_blacklist_ok_img = self._is_blacklist_ok_img  # 画像による判定結果 False:NG判定 True:OK
            obj.is_blacklist_ok_keyword = self._is_blacklist_ok_keyword  # キーワードによる判定結果 False:NG判定 True:OK
            obj.blacklist_keyword_flg = self._blacklist_keyword_flg  # どこでブラックリストに引っかかったかフラグ立てる

            obj.shipping_size = self._shipping_size  # 発送時の送料区分
            obj.product_title = self._product_title
            obj.description = self._description
            obj.p_o_f_0 = self._p_o_f[0]
            obj.p_o_f_1 = self._p_o_f[1]
            obj.p_o_f_2 = self._p_o_f[2]
            obj.p_o_f_3 = self._p_o_f[3]
            obj.p_o_f_4 = self._p_o_f[4]
            obj.p_o_f_5 = self._p_o_f[5]
            obj.p_o_f_6 = self._p_o_f[6]
            obj.p_o_f_7 = self._p_o_f[7]
            obj.p_o_f_8 = self._p_o_f[8]
            obj.p_o_f_9 = self._p_o_f[9]
            obj.f_b_0 = self._f_b[0]
            obj.f_b_1 = self._f_b[1]
            obj.f_b_2 = self._f_b[2]
            obj.f_b_3 = self._f_b[3]
            obj.f_b_4 = self._f_b[4]
            obj.f_b_5 = self._f_b[5]
            obj.f_b_6 = self._f_b[6]
            obj.f_b_7 = self._f_b[7]
            obj.f_b_8 = self._f_b[8]
            obj.f_b_9 = self._f_b[9]
            obj.p_d_t_s_th_0 = self._p_d_t_s_th[0]
            obj.p_d_t_s_th_1 = self._p_d_t_s_th[1]
            obj.p_d_t_s_th_2 = self._p_d_t_s_th[2]
            obj.p_d_t_s_th_3 = self._p_d_t_s_th[3]
            obj.p_d_t_s_th_4 = self._p_d_t_s_th[4]
            obj.p_d_t_s_th_5 = self._p_d_t_s_th[5]
            obj.p_d_t_s_th_6 = self._p_d_t_s_th[6]
            obj.p_d_t_s_th_7 = self._p_d_t_s_th[7]
            obj.p_d_t_s_th_8 = self._p_d_t_s_th[8]
            obj.p_d_t_s_th_9 = self._p_d_t_s_th[9]
            obj.p_d_t_s_td_0 = self._p_d_t_s_td[0]
            obj.p_d_t_s_td_1 = self._p_d_t_s_td[1]
            obj.p_d_t_s_td_2 = self._p_d_t_s_td[2]
            obj.p_d_t_s_td_3 = self._p_d_t_s_td[3]
            obj.p_d_t_s_td_4 = self._p_d_t_s_td[4]
            obj.p_d_t_s_td_5 = self._p_d_t_s_td[5]
            obj.p_d_t_s_td_6 = self._p_d_t_s_td[6]
            obj.p_d_t_s_td_7 = self._p_d_t_s_td[7]
            obj.p_d_t_s_td_8 = self._p_d_t_s_td[8]
            obj.p_d_t_s_td_9 = self._p_d_t_s_td[9]
            obj.p_d_0 = self._p_d[0]
            obj.p_d_1 = self._p_d[1]
            obj.p_d_2 = self._p_d[2]
            obj.p_d_3 = self._p_d[3]
            obj.p_d_4 = self._p_d[4]
            obj.p_d_5 = self._p_d[5]
            obj.p_d_6 = self._p_d[6]
            obj.p_d_7 = self._p_d[7]
            obj.p_d_8 = self._p_d[8]
            obj.p_d_9 = self._p_d[9]
            obj.img_tag_0 = self._img_tag[0]
            obj.img_tag_1 = self._img_tag[1]
            obj.img_tag_2 = self._img_tag[2]
            obj.img_tag_3 = self._img_tag[3]
            obj.img_tag_4 = self._img_tag[4]
            obj.img_tag_5 = self._img_tag[5]
            obj.img_tag_6 = self._img_tag[6]
            obj.img_tag_7 = self._img_tag[7]
            obj.img_tag_8 = self._img_tag[8]
            obj.img_tag_9 = self._img_tag[9]
            obj.img_tag_10 = self._img_tag[10]
            obj.img_tag_11 = self._img_tag[11]
            obj.img_tag_12 = self._img_tag[12]
            obj.img_tag_13 = self._img_tag[13]
            obj.img_tag_14 = self._img_tag[14]
            obj.img_tag_15 = self._img_tag[15]
            obj.img_tag_16 = self._img_tag[16]
            obj.img_tag_17 = self._img_tag[17]
            obj.img_tag_18 = self._img_tag[18]
            obj.img_tag_19 = self._img_tag[19]

        else:
            obj = QooAsinDetail.objects.create(
                asin=self._asin,
                title=self._title,
                url='', # 現状、セットするURLがない。何にするか・・
                amount=self._buybox_quantitytier, # 在庫数 カートの数量を入れてみる。ちゃんと設定されてるか要チェック
                binding=self._binding,
                brand=self._brand,
                color=self._color,
                department=self._department,
                is_adlt=self._is_adlt,
                i_height=self._i_height,
                i_height_unit=self._i_height_unit,
                i_length=self._i_length,
                i_length_unit=self._i_length_unit,
                i_width=self._i_width,
                i_width_unit=self._i_width_unit,
                i_weight=self._i_weight,
                i_weight_unit=self._i_weight_unit,
                p_height=self._p_height,
                p_height_unit=self._p_height_unit,
                p_length=self._p_length,
                p_length_unit=self._p_length_unit,
                p_width=self._p_width,
                p_width_unit=self._p_width_unit,
                p_weight=self._p_weight,
                p_weight_unit=self._p_weight_unit,
                rank_cat_1=self._rank_cat[0],
                rank_1=int(self._rank[0]),
                rank_cat_2=int(self._rank_cat[1]),
                rank_2=int(self._rank[1]),
                rank_cat_3=int(self._rank_cat[2]),
                rank_3=int(self._rank[2]),
                actor=self._actor,
                aspectRatio=self._aspectRatio,
                audienceRating=self._audienceRating,
                author=self._author,
                backFinding=self._backFinding,
                bandMaterialType=self._bandMaterialType,
                blurayRegion=self._blurayRegion,
                ceroAgeRating=self._ceroAgeRating,
                chainType=self._chainType,
                claspType=self._claspType,
                cpuManufacturer=self._cpuManufacturer,
                cpuSpeed_value=self._cpuSpeed_value,
                cpuSpeed_unit=self._cpuSpeed_unit,
                cpuType=self._cpuType,
                creator_value=self._creator_value,
                creator_unit=self._creator_unit,
                director=self._director,
                displaySize_value=self._displaySize_value,
                displaySize_unit=self._displaySize_unit,
                edition=self._edition,
                episodeSequence=self._episodeSequence,
                esrbAgeRating=self._esrbAgeRating,
                feature=self._feature,
                flavor=self._flavor,
                format_val=self._format_val,
                gemType=self._gemType,
                genre=self._genre,
                golfClubFlex=self._golfClubFlex,
                golfClubLoft_value=self._golfClubLoft_value,
                golfClubLoft_unit=self._golfClubLoft_unit,
                handOrientation=self._handOrientation,
                hardDiskInterface=self._hardDiskInterface,
                hardDiskSize_value=self._hardDiskSize_value,
                hardDiskSize_unit=self._hardDiskSize_unit,
                hardwarePlatform=self._hardwarePlatform,
                hazardousMaterialType=self._hazardousMaterialType,
                isAutographed=self._isAutographed,
                isEligibleForTradeIn=self._isEligibleForTradeIn,
                isMemorabilia=self._isMemorabilia,
                issuesPerYear=self._issuesPerYear,
                itemPartNumber=self._itemPartNumber,
                languages=self._languages,
                legalDisclaimer=self._legalDisclaimer,
                manufacturerMaximumAge_value=self._manufacturerMaximumAge_value,
                manufacturerMaximumAge_unit=self._manufacturerMaximumAge_unit,
                manufacturerMinimumAge_value=self._manufacturerMinimumAge_value,
                manufacturerMinimumAge_unit=self._manufacturerMinimumAge_unit,
                manufacturerPartsWarrantyDescription=self._manufacturerPartsWarrantyDescription,
                materialType=self._materialType,
                maximumResolution_value=self._maximumResolution_value,
                maximumResolution_unit=self._maximumResolution_unit,
                mediaType=self._mediaType,
                metalStamp=self._metalStamp,
                metalType=self._metalType,
                model=self._model,
                numberOfDiscs=self._numberOfDiscs,
                numberOfIssues=self._numberOfIssues,
                numberOfItems=self._numberOfItems,
                numberOfPages=self._numberOfPages,
                numberOfTracks=self._numberOfTracks,
                operatingSystem=self._operatingSystem,
                opticalZoom_value=self._opticalZoom_value,
                opticalZoom_unit=self._opticalZoom_unit,
                pegiRating=self._pegiRating,
                processorCount=self._processorCount,
                productTypeSubcategory=self._productTypeSubcategory,
                publicationDate=self._publicationDate,
                regionCode=self._regionCode,
                ringSize=self._ringSize,
                runningTime_value=self._runningTime_value,
                runningTime_unit=self._runningTime_unit,
                shaftMaterial=self._shaftMaterial,
                scent=self._scent,
                seasonSequence=self._seasonSequence,
                seikodoProductCode=self._seikodoProductCode,
                sizePerPearl=self._sizePerPearl,
                label=self._label,
                list_price_amount=self._list_price_amount,
                list_price_code=self._list_price_code,
                manufacturer=self._manufacturer,
                package_quantity=self._package_quantity,
                part_number=self._part_number,
                platform=self._platform,
                product_group=self._product_group,
                product_type_name=self._product_type_name,
                release_date=self._release_date,
                publisher=self._publisher,
                size=self._size,
                small_image_url=self._small_image_url,
                small_image_height_value=self._small_image_height_value,
                small_image_height_units=self._small_image_height_units,
                small_image_width_value=self._small_image_width_value,
                small_image_width_units=self._small_image_width_units,
                subscriptionLength_value=self._subscriptionLength_value,
                subscriptionLength_unit=self._subscriptionLength_unit,
                systemMemorySize_value=self._systemMemorySize_value,
                systemMemorySize_unit=self._systemMemorySize_unit,
                systemMemoryType=self._systemMemoryType,
                theatricalReleaseDate=self._theatricalReleaseDate,
                totalDiamondWeight_value=self._totalDiamondWeight_value,
                totalDiamondWeight_unit=self._totalDiamondWeight_unit,
                totalGemWeight_value=self._totalGemWeight_value,
                totalGemWeight_unit=self._totalGemWeight_unit,
                warranty=self._warranty,
                weeeTaxValue_amount=self._weeeTaxValue_amount,
                weeeTaxValue_currency_code=self._weeeTaxValue_currency_code,
                studio=self._studio,

                # ここから以下は格納できているか確認必要
                # relationships_asin_1=self._relationships_asin_1,
                # sales_rankings_cat_id=self._sales_rankings_cat_id
                # product_category_id=self._product_category_id
                # product_category_rank=self._product_category_rank

                buybox_listing_price=int(self._buybox_listing_price), # カート価格
                buybox_currency_cd=self._buybox_currency_cd,  # カード通貨コード
                buybox_condition=self._buybox_condition, # カート出品状態
                buybox_shipping_price=self._buybox_shipping_price, # カート送料
                shipfrom_country=self._shipfrom_country, # 出品者の所在国
                num_offers_amazon=self._num_offers_amazon, # NumberOfOffersのamazon出品者数
                num_offers_merchant=self._num_offers_merchant, # NumberOfOffersのMerchant出品者数
                ok_seller_feedback_rate=self._ok_seller_feedback_rate, # OKと判断されたセラーのfeedback rate
                ok_seller_id=self._ok_seller_id, # OKと判断されたセラーのid
                is_seller_ok=self._is_seller_ok, # 出品OKかどうかの出品者状態による判定
                product_title=self._product_title,
                description=self._description,
                p_o_f_0=self._p_o_f[0],
                p_o_f_1=self._p_o_f[1],
                p_o_f_2=self._p_o_f[2],
                p_o_f_3=self._p_o_f[3],
                p_o_f_4=self._p_o_f[4],
                p_o_f_5=self._p_o_f[5],
                p_o_f_6=self._p_o_f[6],
                p_o_f_7=self._p_o_f[7],
                p_o_f_8=self._p_o_f[8],
                p_o_f_9=self._p_o_f[9],
                f_b_0=self._f_b[0],
                f_b_1=self._f_b[1],
                f_b_2=self._f_b[2],
                f_b_3=self._f_b[3],
                f_b_4=self._f_b[4],
                f_b_5=self._f_b[5],
                f_b_6=self._f_b[6],
                f_b_7=self._f_b[7],
                f_b_8=self._f_b[8],
                f_b_9=self._f_b[9],
                p_d_t_s_th_0=self._p_d_t_s_th[0],
                p_d_t_s_th_1=self._p_d_t_s_th[1],
                p_d_t_s_th_2=self._p_d_t_s_th[2],
                p_d_t_s_th_3=self._p_d_t_s_th[3],
                p_d_t_s_th_4=self._p_d_t_s_th[4],
                p_d_t_s_th_5=self._p_d_t_s_th[5],
                p_d_t_s_th_6=self._p_d_t_s_th[6],
                p_d_t_s_th_7=self._p_d_t_s_th[7],
                p_d_t_s_th_8=self._p_d_t_s_th[8],
                p_d_t_s_th_9=self._p_d_t_s_th[9],
                p_d_t_s_td_0=self._p_d_t_s_td[0],
                p_d_t_s_td_1=self._p_d_t_s_td[1],
                p_d_t_s_td_2=self._p_d_t_s_td[2],
                p_d_t_s_td_3=self._p_d_t_s_td[3],
                p_d_t_s_td_4=self._p_d_t_s_td[4],
                p_d_t_s_td_5=self._p_d_t_s_td[5],
                p_d_t_s_td_6=self._p_d_t_s_td[6],
                p_d_t_s_td_7=self._p_d_t_s_td[7],
                p_d_t_s_td_8=self._p_d_t_s_td[8],
                p_d_t_s_td_9=self._p_d_t_s_td[9],
                p_d_0=self._p_d[0],
                p_d_1=self._p_d[1],
                p_d_2=self._p_d[2],
                p_d_3=self._p_d[3],
                p_d_4=self._p_d[4],
                p_d_5=self._p_d[5],
                p_d_6=self._p_d[6],
                p_d_7=self._p_d[7],
                p_d_8=self._p_d[8],
                p_d_9=self._p_d[9],
                img_tag_0=self._img_tag[0],
                img_tag_1=self._img_tag[1],
                img_tag_2=self._img_tag[2],
                img_tag_3=self._img_tag[3],
                img_tag_4=self._img_tag[4],
                img_tag_5=self._img_tag[5],
                img_tag_6=self._img_tag[6],
                img_tag_7=self._img_tag[7],
                img_tag_8=self._img_tag[8],
                img_tag_9=self._img_tag[9],
                img_tag_10=self._img_tag[10],
                img_tag_11=self._img_tag[11],
                img_tag_12=self._img_tag[12],
                img_tag_13=self._img_tag[13],
                img_tag_14=self._img_tag[14],
                img_tag_15=self._img_tag[15],
                img_tag_16=self._img_tag[16],
                img_tag_17=self._img_tag[17],
                img_tag_18=self._img_tag[18],
                img_tag_19=self._img_tag[19],
            )
        obj.save()

        # relationがあれば
        for kk, rel in enumerate(self._relation_asin):
            obj_relation, created = QooAsinRelationDetail.objects.update_or_create(
                asin=self._relation_asin[kk],
                defaults={
                    'parent_asin': obj,
                    'marketplace_id': self._marketplace_id[kk],
                    'seller_id': self._seller_id[kk],
                    'seller_sku': self._seller_sku[kk],
                    'color': self._rel_color[kk],
                    'edition': self._rel_edition[kk],
                    'flavor': self._rel_flavor[kk],
                    'gem_type': self._rel_gem_type[kk],
                    'golf_club_flex': self._rel_golf_club_flex[kk],
                    'hand_orientation': self._rel_hand_orientation[kk],
                    'hardware_platform': self._rel_hardware_platform[kk],
                    'material_type_1': self._rel_material_type[kk][0],
                    'material_type_2': self._rel_material_type[kk][1],
                    'material_type_3': self._rel_material_type[kk][2],
                    'metal_type': self._rel_metal_type[kk],
                    'model': self._rel_model[kk],
                    'operating_system_1': self._rel_operating_system[kk][0],
                    'operating_system_2': self._rel_operating_system[kk][1],
                    'operating_system_3': self._rel_operating_system[kk][2],
                    'product_type_subcategory': self._rel_product_type_subcategory[kk],
                    'ring_size': self._rel_ring_size[kk],
                    'shaft_material': self._rel_shaft_material[kk],
                    'scent': self._rel_scent[kk],
                    'size': self._rel_size[kk],
                    'size_per_pearl': self._rel_size_per_pearl[kk],
                    'golf_club_loft_value': self._rel_golf_club_loft_value[kk],
                    'golf_club_loft_units': self._rel_golf_club_loft_units[kk],
                    'total_diamond_weight_value': self._rel_total_diamond_weight_value[kk],
                    'total_diamond_weight_units': self._rel_total_diamond_weight_units[kk],
                    'total_gem_weight_value': self._rel_total_gem_weight_value[kk],
                    'total_gem_weight_units': self._rel_total_gem_weight_units[kk],
                    'package_quantity': self._rel_package_quantity[kk],
                    'item_dimensions_height_value': self._rel_item_dimensions_height_value[kk],
                    'item_dimensions_height_units': self._rel_item_dimensions_height_units[kk],
                    'item_dimensions_length_value': self._rel_item_dimensions_length_value[kk],
                    'item_dimensions_length_units': self._rel_item_dimensions_length_units[kk],
                    'item_dimensions_width_value': self._rel_item_dimensions_width_value[kk],
                    'item_dimensions_width_units': self._rel_item_dimensions_width_units[kk],
                    'item_dimensions_weight_value': self._rel_item_dimensions_weight_value[kk],
                    'item_dimensions_weight_units': self._rel_item_dimensions_weight_units[kk],
                }
            )
            obj_relation.save()

        # wowma 商品情報も更新
        self.logger.info("-> AmaSPApiAsinDetail start set wowma goodsinfo")
        new_wow_obj = WowmaGoodsDetail.objects.filter(
            asin__asin=self._asin,
        ).first()
        if not new_wow_obj:
            obj_wow, created = WowmaGoodsDetail.objects.update_or_create(
                asin=obj,
            )
        else:
            # ここでなにか更新するものはあるか・・・
            # new_wow_obj.
            self.logger.info("-> AmaSPApiAsinDetail found wowma goodsinfo obj")
            new_wow_obj.save()
        self.logger.info("-> AmaSPApiAsinDetail end of set wowma goodsinfo")

        self.logger.info("-> AmaSPApiAsinDetail set_db_product end ")
        return

    def get_ama_src_with_tor(self):
        # torでAmazonページをスクレイピングして詳細情報を取ってみよう
        self.logger.info("--->> get_ama_src_with_tor in ")
        self._common_chrome_driver = CommonChromeDriver(self.logger)

        # self.common_chrome_driver.driverにセット
        #self._common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)
        self._common_chrome_driver.init_chrome_with_tor()

        # asin指定してページ情報取得
        url = 'https://www.amazon.co.jp/dp/' + self._asin + '/ref=nav_logo'

        # これだとうまくいく・・・
        #url = 'https://www.amazon.co.jp/CA4LA-%E3%82%AB%E3%82%B7%E3%83%A9-KTZ02277-HK-BKH/dp/B0B9GRH3PZ/ref=sr_1_1?pf_rd_i=2229202051&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_p=cc33837b-6b21-4d03-8ce5-957c33106d62&pf_rd_r=8TBRNX9MTJ4W04XYC1G6&pf_rd_s=merchandised-search-5&pf_rd_t=101&qid=1662184803&s=fashion&sr=1-1'

        # これでも取れてるかな。 ref=nav_logoをつけただけ
        #url = 'https://www.amazon.co.jp/dp/B084TNP2B4/ref=nav_logo'

        #url = 'https://www.google.com/'
        self.get_ama_src_exec(url)

        self.logger.info("--->> get_ama_src_with_tor page_result [{}]".format(
            self._common_chrome_driver.driver.page_source
        ))

        self.logger.info("--->> get_ama_src_with_tor out ")
        return

    def get_ama_src_exec(self, url):
        try:
            self.logger.info("--->> get_ama_src_exec in ")

            retry_cnt = 3
            for i in range(1, retry_cnt + 1):
                try:
                    self._common_chrome_driver.driver.get(url)
                    # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
                except Exception as e:
                    self.logger.info(traceback.format_exc())
                    self.logger.info('webdriver error occurred start retry..')
                    self._common_chrome_driver.restart_chrome()
                    sleep(3)
                else:
                    break

        except Exception as e:
            #print(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            self._common_chrome_driver.quit_chrome_with_tor()

        self.logger.info("--->> get_ama_src_exec out ")
        return


# sp_apiのProductsとかぶったので改名する
class Products_BK20220821(BaseObject):

    # Idlistは最大5　回復レートは5商品/秒　最大20リクエスト　1時間あたり18000
    def GetMatchingProductForId(self, IdList):
        q = {
            'Action': 'GetMatchingProductForId',
            'MarketplaceId': 'A1VC38T7YXB528',
            'Version': '2011-10-01',
            'IdType': 'ASIN',
        }
        [q.update({'IdList.Id.' + str(i + 1): Id}) for i, Id in enumerate(IdList)]

        return q

    # Idlistは最大20　回復レートは10商品/秒　最大20リクエスト　時間最大36000リクエスト
    # 新品のカートボックス価格と中古のカートボックス価格を返す
    def GetCompetitivePricingForASIN(self, IdList):
        q = {
            'Action': 'GetCompetitivePricingForASIN',
            'MarketplaceId': 'A1VC38T7YXB528',
            'Version': '2011-10-01',
        }
        [q.update({'ASINList.ASIN.' + str(i + 1): Id}) for i, Id in enumerate(IdList)]

        return q

    # Idlistは最大20　回復レートは10商品/秒　最大20リクエスト　時間最大36000リクエスト
    # 最低価格
    # ItemCondition値：#New #Used #Collectible #Refurbished #Club #デフォルト：All
    def GetLowestOfferListingsForASIN(self, IdList, ItemCondition='New', ExcludeMe=True):
        q = {
            'Action': 'GetLowestOfferListingsForASIN',
            'MarketplaceId': 'A1VC38T7YXB528',
            'Version': '2011-10-01',
            'ItemCondition': ItemCondition,
            'ExcludeMe': ExcludeMe
        }
        [q.update({'ASINList.ASIN.' + str(i + 1): Id}) for i, Id in enumerate(IdList)]

        return q

    # Idlistは最大20　回復レートは1リクエスト/5秒　最大20リクエスト 時間最大720リクエスト
    def ListMatchingProducts(self, Query, QueryContextId='All'):
        q = {
            'Action': 'ListMatchingProducts',
            'MarketplaceId': 'A1VC38T7YXB528',
            'Version': '2011-10-01',
            'Query': Query,
            'QueryContextId': QueryContextId
        }

        return q

    # 最大20　回復レートは1リクエスト/5秒　最大20リクエスト 時間最大720リクエスト
    def GetProductCategoriesForASIN(self, ASIN):
        q = {
            'Action': 'GetProductCategoriesForASIN',
            'MarketplaceId': 'A1VC38T7YXB528',
            'Version': '2011-10-01',
            'ASIN': ASIN
        }

        return q

    def PostMWS(self, q):
        timestamp = datetime_encode(datetime.datetime.utcnow())
        last_update_after = datetime_encode(
            datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )

        data = {
            'AWSAccessKeyId': AMAZON_CREDENTIAL['ACCESS_KEY_ID'],
            'MarketplaceId': 'A1VC38T7YXB528',
            'SellerId': AMAZON_CREDENTIAL['SELLER_ID'],
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': '2',
            'Timestamp': timestamp,
        }

        #self.logger.info('PostMWS q:' + str(q))
        data.update(q)
        query_string = urllib.parse.urlencode(sorted(data.items()))
        #self.logger.info('PostMWS query_string:' + str(query_string))

        # これは例外かも知れないが
        query_string = re.sub('%25', '%', query_string)
        #self.logger.info('PostMWS after qy_str:' + str(query_string))

        canonical = "{}\n{}\n{}\n{}".format(
            'POST', DOMAIN, ENDPOINT, query_string
        )
        h = hmac.new(
            six.b(self.AWSSecretAccessKey),
            six.b(canonical), hashlib.sha256)
        signature = urllib.parse.quote(base64.b64encode(h.digest()), safe='')
        url = 'https://{}{}?{}&Signature={}'.format(
            DOMAIN, ENDPOINT, query_string, signature)

        res = requests.post(url)
        # 文字化け対策
        res.encoding = res.apparent_encoding

        return res.text

    def find_list_matched_product_ns2(self, element):
          #print("find_list_matched_product : resobj:[%s]", str(self._response))
          return self.parse.find(".//ns2:%s" % element, self._products_namespace)


    def find_list_matched_product(self, element):
          #print("find_list_matched_product : resobj:[%s]", str(self._response))
          return self.parse.find(".//2011-10-01:%s" % element, self._products_namespace)

      # https://lets-hack.tech/programming/languages/python/mws/　参考に
      # https://searchcode.com/codesearch/view/81319497/
      # Idlistは最大20　回復レートは1リクエスト/5秒　最大20リクエスト 時間最大720リクエスト
    def request_list_matching_products(self, Query, QueryContextId='All'):
        return self.request(PRODUCTSENDPOINT, **{"Action": "ListMatchingProducts",
                                                'Query': urllib.parse.quote(Query),
                                                'QueryContextId':QueryContextId,
                                                "MarketplaceId.Id.1": MARKETPLACES[self.Region][1]})

    def request_get_matching_product(self, asins):
        data = {
            "Action": "GetMatchingProduct",
            "MarketplaceId.Id.1" : MARKETPLACES[self.Region][1]
        }
        data.update(self.enumerate_param('ASINList.ASIN.', asins))
        return self.request(PRODUCTSENDPOINT, data)
"""
return self.request(PRODUCTSENDPOINT, **{"Action": "GetMatchingProduct",
                                    "MarketplaceId.Id.1": MARKETPLACES[self.Region][1],
                                    self.enumerate_param('ASINList.ASIN.', asins)})
"""

#
class Order(BaseObject):

    # ListOrders
    def request_list_orders(self, days=None):
       if days == None:
           days = 14  # 1
       last_update_after = datetime_encode(
          datetime.datetime.utcnow() - datetime.timedelta(days=days))
    # datetime.datetime.utcnow() - datetime.timedelta(days=14))

       return self.request(ORDERENDPOINT, **{"Action": "ListOrders",
                                             'LastUpdatedAfter': last_update_after,"MarketplaceId.Id.1": MARKETPLACES[self.Region][1]})

#
class Report(BaseObject):

    #
    def request_report(self, ReportType=None):
       return self.request(**{"Action": "RequestReport", "ReportType": ReportType,
                             "MarketplaceIdList.Id.1": MARKETPLACES[self.Region][1]})

    #
    def get_report_request_list(self, RequestId=None):
       return self.request(**{"Action": "GetReportRequestList", "ReportRequestIdList.Id.1": RequestId})

    #
    def get_report_list(self, RequestId=None):
       return self.request(**{"Action": "GetReportList", "ReportRequestIdList.Id.1": RequestId})

    #
    def get_report(self, ReportId=None):
       return self.request(**{"Action": "GetReport", "ReportId": ReportId})


    # Create your views here.
    def index(request):
       return HttpResponse("Hello testscr_1 ! ")


    def getorder(request):
        order = Order()

        #
        #  1
        response = order.request_list_orders(14)
        # print(response.raw)
        # parsed = response.parse
        print('ok parse')
        if (response.find_orders('LatestShipDate')):
            print(response.find_orders('LatestShipDate').text)
        else:
            print('no latest ship date')

        mylastorder = ''
        #  Order/AmazonOrderId
        myorders = response.find_orders_all('Order')

    # f = open('/app/amget/tmp/samplesrc.txt', mode='w')
    # f.write(str(response.raw, 'utf-8'))
    # f.close()

        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()

            for myorder in myorders:
              set_order(c, myorder)
            conn.commit()

# print(find_orders_by_obj(myorder,'AmazonOrderId').text)
# print(myorder.find(".//2013-09-01:%s" % 'AmazonOrderId', _orders_namespace).text)
# mystatus = find_orders_by_obj(myorder,'OrderStatus').text
# if(mystatus is None):
#    print('no orderstatus')
# else:
#    print(mystatus)
# if mystatus == 'Unshipped':
#    myorderobj = find_orders_by_obj(myorder,'BuyerName')
#    if(myorderobj is None):
#        mylastorder += '[none] '
#    else:
#        mylastorder = myorderobj.text
# else:
#    print('no buyer name')

# return HttpResponse(mylastorder)
        return HttpResponse('ok')
# print(myorder.find(".//2013-09-01:%s" % 'BuyerName', _orders_namespace).text)
# parse.find(".//2013-09-01:%s" % element, self._orders_namespace)


#        print('AmazonOrderId:' + myorder.find('./Order', _orders_namespace).text.strip())
# print(response.parse)
# print(response.find_orders("OrderType"))

"""
  #
  response = report.request_report(ReportType="_GET_MERCHANT_LISTINGS_DATA_")
  # ID
  request_id = response.find("ReportRequestId").text

  try:
      # ID
      while True:
          # ID
          response = report.get_report_request_list(RequestId=request_id)
          # status_DONE__DONE_ID
          if "_DONE_" == response.find("ReportProcessingStatus").text:
              report_id = response.find("GeneratedReportId").text
              break
          # 5032
          time.sleep(120)

      # ID
      response = report.get_report(ReportId=report_id)
      print(response.raw)
  except Exception as e:
      print(e)
"""

