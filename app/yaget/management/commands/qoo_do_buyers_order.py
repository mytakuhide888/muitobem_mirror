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

from yaget.models import YaBuyersItemDetail, QooOrderInfo, QooBuyersOrderDetail
from yaget.models import QooShopInfo, YaBuyersItemDetail

# logging
logging.config.fileConfig(fname="/app/yaget/management/commands/qoo_do_buyers_order_logging.config", disable_existing_loggers=False)

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
        self.logger.debug('qoo_do_buyers_order Command in. init')
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
        #parser.add_argument('pk', nargs='+')

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

        # =====================================================================
        # ★★qoo10用の在庫チェックバッチのなかでやる。
        # バイヤーズの在庫を巡回して、在庫数や価格を更新。
        # チェック対象は、yaget_yabuyersitemdetail　に登録済みのもの。
        # qooへの本登録は、在庫バッチを回して在庫があったとき。
        # 在庫があり、出品済みフラグを見て、まだ未出品のものは出品のフローを。出品済みであれば在庫数や価格のチェックと更新を行う
        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('qoo_do_buyers_order handle is called')
            self.batch_status = BatchStatusUpd('qoo_do_buyers_order')
            self.batch_status.start()

            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            self.buinfo_obj = BuyersInfo(self.logger)

            # バイヤーズに発注する母体
            self._exec_buyers_order(options['pk'], options['payment_method'])

            self.logger.info('qoo_do_buyers_order handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        self.batch_status.end()
        self.logger.info('qoo_do_buyers_order handle end')
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))
        return

    # qooから注文情報を取り込みバイヤーズに発注する
    def _exec_buyers_order(self, pk, payment_method):

        # 受注番号をコマンド引数 pk から取得。とれただけループして確認する
        self.logger.info('qoo_do_buyers_order _exec_buyers_order handle pk:' + pk)

        # パラメータ設定
        #end_date = datetime.date.today()
        #start_date = end_date + timedelta(weeks=-2)
        date_type = 0  # 0:注文日　1:発送日　2:入金日　3:発売(入荷)予定日　4:発送期限日　（デフォルト0）

        # 指定された注文情報取得
        qoo_order = QooOrderInfo.objects.filter(
            order_no=pk,
        ).first()

        # 注文がヒットしたら処理
        if qoo_order:

            # 電話番号はどちらか、有効な方を１に指定する
            if len(str(qoo_order.receiver_tel)) > 6:
                my_tel = qoo_order.receiver_tel
            else:
                my_tel = qoo_order.receiver_mobile

            # 注文に基づく発送先
            order_receiver_list = {
                "sender_name": qoo_order.receiver,
                "sender_kana": qoo_order.receiver_gata,
                "sender_zipcode": qoo_order.zipcode,
                "sender_address": self._insert_space_post_address(qoo_order.shipping_addr),
                "sender_phone_number_1": my_tel.replace('+81-', ''),
                "sender_phone_number_2": str(qoo_order.receiver_mobile).replace('+81-', ''),
            }

            # 注文に紐づくショップ情報も必要
            shop_info = QooShopInfo.objects.filter(shop_name=qoo_order.seller_id).first()
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

            # バイヤーズにログインしておく
            self.buinfo_obj.login_buyers()
            self.logger.info('qoo_do_buyers_order _exec_buyers_order ログイン成功まで')

            # バイヤーズで発注する前に、qoo10商品コードから商品IDを引っ張ってこないと
            item_detail = YaBuyersItemDetail.objects.filter(
                qoo_gdno=qoo_order.item_code
            ).first()

            if item_detail:

                for i in range(qoo_order.order_qty):

                    self.logger.info('item_code:[{}] 個数 {}/{}'.format(
                        item_detail.gid,
                        i+1,
                        qoo_order.order_qty))

                    # 購入をすすめる
                    buyers_order_id, payment_total = self.buinfo_obj.get_buyers_detail_page(
                        'https://buyerz.shop/shopdetail/' + str(item_detail.gid)[4:],
                        shop_info_list,
                        order_receiver_list,
                        payment_method,
                    )

                    if buyers_order_id:  # バイヤーズの発注番号が返却されたら保存しておく
                        obj, created = QooBuyersOrderDetail.objects.update_or_create(
                            buyers_order_id=buyers_order_id,
                            order_detail=qoo_order,
                            status='発注済み',
                            payment_method=payment_method,
                            payment_total=payment_total,
                            delivery_method=qoo_order.shipping_way,
                            order_date=dt.now().strftime('%Y%m%d %H%M%S.%f'),
                            unit=1,
                        )
                        obj.save
                    else:
                        # Falseで返されたらスルー
                        pass
            else:
                # 該当の商品が見つからない？
                self.logger.info('qoo_do_buyers_order _exec_buyers_order 該当の商品CDが見つからない？ qoo_order.item_code[{}]'.format(qoo_order.item_code))
                raise Exception('_exec_buyers_order 該当の商品CDが紐づけ出来ていません。商品詳細ページの「編集」からqoo商品コードに[{}]を設定してください'.format(qoo_order.item_code))


        else:
            # 注文がヒットなし
            self.logger.info('qoo_do_buyers_order _exec_buyers_order 該当の注文が見つからないので処理終了[{}]'.format(pk))
            raise Exception('_exec_buyers_order 該当の注文が見つからないので処理終了[{}]'.format(pk))

        return

    # 住所から都道府県の文字列の後に半角スペースを挿入する
    def _insert_space_post_address(self, address):

        todoufuken_list = [
            '北海道',
            '青森県',
            '岩手県',
            '宮城県',
            '秋田県',
            '山形県',
            '福島県',
            '茨城県',
            '栃木県',
            '群馬県',
            '埼玉県',
            '千葉県',
            '東京都',
            '神奈川県',
            '新潟県',
            '富山県',
            '石川県',
            '福井県',
            '山梨県',
            '長野県',
            '岐阜県',
            '静岡県',
            '愛知県',
            '三重県',
            '滋賀県',
            '京都府',
            '大阪府',
            '兵庫県',
            '奈良県',
            '和歌山県',
            '鳥取県',
            '島根県',
            '岡山県',
            '広島県',
            '山口県',
            '徳島県',
            '香川県',
            '愛媛県',
            '高知県',
            '福岡県',
            '佐賀県',
            '長崎県',
            '熊本県',
            '大分県',
            '宮崎県',
            '鹿児島県',
            '沖縄県',
        ]

        for todoufuken in todoufuken_list:
            address = str(address).replace(todoufuken, todoufuken + ' ')

        return address