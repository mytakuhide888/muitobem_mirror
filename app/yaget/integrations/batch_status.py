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
from yaget.models import BatchStatus

# logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logger.setLevel(20)

# ログローテ設定
rh = logging.handlers.RotatingFileHandler(
    r'/app/yaget/management/commands/log/batch_status.log',
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


def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))

class BatchStatusUpd(object):
    def __init__(self, batch_name):
        self.logger = logger
        self.logger.info('batch_status_upd in. init')
        self.batch_id = None
        self.batch_name = batch_name

    # バッチ実行開始
    def start(self):
        self.logger.debug('batch_status_upd start in.')

        # DBに保存
        obj = BatchStatus.objects.create(
                batch_name=self.batch_name,
                batch_status=0,  # 実行中
                start_date=timezone.datetime.now(),
            )
        obj.save()
        self.batch_id = obj.batch_id
        self.logger.debug('batch_status_upd start batch_id:[{}]'.format(self.batch_id))

        self.logger.debug('batch_status_upd start out.')
        return

    # バッチ実行完了
    def end(self):
        self.logger.debug('batch_status_upd end in.')

        try:
            # DBに保存
            new_obj = BatchStatus.objects.filter(batch_id=self.batch_id).first()
            if not new_obj:
                self.logger.debug('batch_status_upd end batch_idが存在しない? id:[{}]'.format(self.batch_id))
            else:
                new_obj.batch_status = 1  # 正常終了
                new_obj.end_date = timezone.datetime.now()
                new_obj.save()
        except Exception as e:
            self.logger.debug('batch_status_upd end error? [{}]'.format(traceback.format_exc()))

        self.logger.debug('batch_status_upd end out.')
        return

    # バッチ異常終了
    def error_occurred(self, message):
        self.logger.debug('batch_status_upd error_occurred in.')

        # DBに保存
        new_obj = BatchStatus.objects.filter(batch_id=self.batch_id).first()
        if not new_obj:
            self.logger.debug('batch_status_upd error_occurred batch_idが存在しない? id:[{}]'.format(self.batch_id))
        else:
            new_obj.batch_status = 2  # 異常終了
            new_obj.message = str(message)[:9999]
            new_obj.stop_date = timezone.datetime.now()
            new_obj.save()

        self.logger.debug('batch_status_upd error_occurred out.')
        return

