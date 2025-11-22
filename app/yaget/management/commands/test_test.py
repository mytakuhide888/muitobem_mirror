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
from yaget.models import YaBuyersItemList, YaBuyersItemDetail, YaBuyersItemBlackList
from yaget.models import Friend, Message
from yaget.integrations.batch_status import BatchStatusUpd


#from yaget.AmaMws import AmaMwsProducts

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/delete_goods_info.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

#logger.setLevel(20)

# 共通変数
mydwsrc_dir = "/app/yaget/wowma_buyers/dwsrc"
mydwimg_dir = "/app/yaget/wowma_buyers/dwimg/"
myupdcsv_dir = "/app/yaget/wowma_buyers/updcsv/"
mydeletecsv_dir = "/app/yaget/wowma_buyers/deletecsv/"

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


    def _chk_buyers_stock_from_list(self):

        self.logger.info('_chk_buyers_stock_from_list in.')

        self.logger.info('test_test out.')
        return


    def handle(self, *args, **options):

        try:
            self.logger.info('test_test handle is called start[{}]'.format(datetime.datetime.now()))
            print('test_test start')
            obj, created = Friend.objects.update_or_create(
                name='test_1',
                mail='test_mail_1',
                gender=True,
                age=20,
                birthday=datetime.datetime.now(),
            )
            obj.save()

            # 注文詳細をそれぞれ取り込む
            new_obj_list = Message.objects.filter(
                friend=obj,
            ).all()

            if not new_obj_list:
                message_obj, created_message = Message.objects.update_or_create(
                    title='title_1',
                    content='test_content_1',
                    pub_date=datetime.datetime.now(),
                    friend = obj,
                )
                #message_obj.friend = obj
                message_obj.save()

                message_obj_1, created_message = Message.objects.update_or_create(
                    title='title_2',
                    content='test_content_2',
                    pub_date=datetime.datetime.now(),
                    friend=obj,
                )
                # message_obj.friend = obj
                message_obj_1.save()
            else:
                print('Message: すでに登録済みです')
                print('len:{}'.format(len(new_obj_list)))
                for new_obj in new_obj_list:
                    if new_obj.title == 'title_2':
                        new_obj.title ='title_2_1'
                        new_obj.save()

            myobj = Friend.objects.all()
            for mymy_obj in myobj:
                print('Friend:name:[{}]'.format(mymy_obj.name))

                child_obj = Message.objects.filter(friend=mymy_obj)
                for child_obj_member in child_obj:
                    print('Message:title:[{}]'.format(child_obj_member.title))

            """
            detail_list = YaBuyersItemDetail.objects.all()
            self.logger.info('detail_list len [{}]'.format(len(detail_list)))
            #filtered = YaBuyersItemDetail.objects.filter(black_list__isnull=True).all()
            #self.logger.info('filtered len [{}]'.format(len(filtered)))
            self.logger.info('test_test handle is called next[{}]'.format(datetime.datetime.now()))
            filtered = YaBuyersItemDetail.objects.select_related('black_list').filter(black_list__isnull=True).all()
            self.logger.info('filtered len [{}]'.format(len(filtered)))
            """
            print('test_test end')
            self.logger.info('test_test handle is called end[{}]'.format(datetime.datetime.now()))

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            traceback.print_exc()
            #self.common_chrome_driver.quit_chrome_with_tor()
            return

        #self.common_chrome_driver.quit_chrome_with_tor()
        self.logger.info('test_test handle end')
        return



