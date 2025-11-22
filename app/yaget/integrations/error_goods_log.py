# -*- coding:utf-8 -*-
from django.utils import timezone
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
import requests
import logging.config
import traceback
from time import sleep
from yaget.models import ErrorGoodsLog

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logger.setLevel(20)

# ログローテ設定
rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/management/commands/log/error_goods_log.log',
    encoding='utf-8',
    maxBytes=1000000,
    backupCount=3
)
fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
rh.setFormatter(fh_formatter)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(ch_formatter)

logger.addHandler(rh)
logger.addHandler(ch)

# e にはリストを渡す。
"""
batch_name = models.TextField('バッチ名', max_length=1000, default='', null=True, blank=True)  # バッチや処理元のプログラム名
asin = models.CharField('asin', max_length=30, default='', null=True,
                       blank=True)  # asin
status = models.IntegerField('バッチ実行状況', default=0, null=True, blank=True)  # ステータス
code = models.TextField('リターンコード', default='', null=True, blank=True)  # リターンコード
message = models.TextField('メッセージ', max_length=10000, default='', null=True, blank=True)  # エラーメッセージなど
"""
def exe_error_log(e):
    # DBに保存
    logger.info('exe_error_log in. ')
    obj = ErrorGoodsLog.objects.create(
        batch_name=e['batch_name'],
        asin=e['asin'],
        status=int(e['status']),
        code=e['code'],
        message=e['message'],
    )
    obj.save()
    return

