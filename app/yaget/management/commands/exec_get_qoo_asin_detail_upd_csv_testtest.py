# -*- coding:utf-8 -*-
import time
import sys, codecs

from django.core.management.base import BaseCommand
import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import re
import lxml.html
import logging
#import logging.handlers
import logging.config
from logging import getLogger, config
import traceback
import subprocess
from time import sleep
import urllib.request
import os, socket
import io,sys
from threading import Timer
import requests

from yaget.integrations.chrome_driver import CommonChromeDriver
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import (
    YaShopListUrl,
    YaShopItemList,
    QooAsinDetail,
)
from yaget.AmaSPApi import AmaSPApi, AmaSPApiAsinDetail, AmaSPApiQooAsinDetail
from yaget.integrations.batch_status import BatchStatusUpd

# 2022/7/13 指定したASINのリスト（CSV）を読み込んで、対象のASIN詳細を全部取ってきて保存する。
# リクエスト制限を気にしないと。
# ListMatchingProducts
# 時間あたりのリクエストクォータ:20リクエスト
# 回復レート:5秒あたり1回のリクエスト
# 最大リクエストクォータ:1時間あたり720リクエスト

#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# log設定はconfigに
#logging.config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail.config", disable_existing_loggers=False)

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

USER_DATA_DIR = '/app/yaget/userdata/'

#config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail_upd_csv.config", disable_existing_loggers=False)
# logger.setLevel(20)
logger = getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ログローテ設定

rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/management/commands/log/exec_qoo_asin_detail_upd_csv.log',
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

logger.addHandler(rh)
logger.addHandler(ch)


# logger.setLevel(logging.DEBUG)


# 共通変数
mydwsrc_dir = "/app/yaget/ama_dwsrc"


def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        #self.logger = logger
        self.logger = logging.getLogger(__name__)
        #logging.config.fileConfig(fname="/app/yaget/management/commands/exec_get_qoo_asin_detail_upd_csv.config", disable_existing_loggers=False)
        self.logger.setLevel(logging.DEBUG)
        # self.logger = logging.getLogger(__name__)

        self._ama_spapi_qoo_ojb = None
        self.common_chrome_driver = None

        self.logger.debug('exec_get_qoo_asin_detail_upd_csv Command in(debug). init')
        logger.debug('exec_get_qoo_asin_detail_upd_csv Command in(debug)_ only logger. init')

    # 本内容は、test_amsrc_1.py のselenium の使い方にある。

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('--csv_no', nargs='?', default='', type=str)
        parser.add_argument('--pk', type=int)
        parser.add_argument('--asin')

    # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):
        try:

            self.logger.debug('exec_get_asin_detail_upd_csv handle is called (self) debug')

            self.logger.debug('csv_no:' + options['csv_no'])
            self.logger.debug('asin:' + str(options['asin']))
            self.logger.debug('get_asin_detail_by_spapi_upd_csv handle end')

        except Exception as e:
            #self.logger.info(traceback.format_exc())
            self.logger.debug(traceback.format_exc())

            """
            t, v, tb = sys.exc_info()
            self.logger.info('###### ya_imp_spqpi_upd_csv except occurred. :{0}'.format(str(traceback.format_exception(t, v, tb))))
            self.logger.info('ya_imp_spqpi_upd_csv except_add:{0}'.format(str(traceback.format_tb(e.__traceback__))))
            print("ya_imp_spqpi_upd_csv message:{0}".format(str(e)))
            """
        return
