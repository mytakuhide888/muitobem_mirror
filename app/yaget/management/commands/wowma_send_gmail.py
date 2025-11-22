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
from datetime import date, timedelta


sys.path.append('/app/yaget/management/commands')
from yaget.integrations.buyers_info import BuyersInfo, BuyersBrandInfo
from yaget.integrations.wowma_access import WowmaAccess
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.integrations.batch_status import BatchStatusUpd
from gmail_access import GmailAccess


# mojule よみこみ
sys.path.append('/app')
sys.path.append('/app/yaget')
sys.path.append('/app/sample')

from yaget.models import YaBuyersItemDetail, WowmaOrderInfo, WowmaOrderDetail, WowmaBuyersOrderDetail
from yaget.models import WowmaShopInfo

# logging
logging.config.fileConfig(fname="/app/yaget/management/commands/wowma_send_gmail_logging.config", disable_existing_loggers=False)

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
        help = 'send gmail.'
        self.logger.debug('wowma_send_gmail Command in. init')
        self.logger.info('wowma_send_gmail Command in. init(info)')
        self.common_chrome_driver = None
        self.driver = None
        self.upd_csv = []
        self.my_wowma_target_ct_list = []
        self.batch_status = None

    # コマンドライン引数を指定します。(argparseモジュール https://docs.python.org/2.7/library/argparse.html)
    # 今回はblog_idという名前で取得する。（引数は最低でも1個, int型）
    def add_arguments(self, parser):
        parser.add_argument('--pk', nargs='?', default='', type=str)
        parser.add_argument('--mail_type', nargs='?', default='', type=str)
        parser.add_argument('--other_message', nargs='?', default='', type=str)
        #parser.add_argument('pk', nargs='+')

    def force_timeout(self):
        os.system('systemctl restart nginx')
        return

        # =====================================================================
        # ★★wowma用の在庫チェックバッチのなかでやる。
        # バイヤーズの在庫を巡回して、在庫数や価格を更新。
        # チェック対象は、yaget_yabuyersitemdetail　に登録済みのもの。
        # wowmaへの本登録は、在庫バッチを回して在庫があったとき。
        # 在庫があり、出品済みフラグを見て、まだ未出品のものは出品のフローを。出品済みであれば在庫数や価格のチェックと更新を行う
        # =====================================================================
        # コマンドが実行された際に呼ばれるメソッド
    def handle(self, *args, **options):

        try:
            self.logger.info('wowma_send_gmail handle is called')
            self.batch_status = BatchStatusUpd('wowma_send_gmail')
            self.batch_status.start()

            # バイヤーズのカテゴリはBuyersInfoから取ってくる
            self.buinfo_obj = BuyersInfo(self.logger)
            #self.wowma_access = WowmaAccess(self.logger)
            self.gmail = GmailAccess(self.logger)


            # メール送信する母体
            self.logger.info('wowma_send_gmail start _exec_send_gmail')
            self._exec_send_gmail(options['pk'], options['mail_type'], options['other_message'])

            self.logger.info('wowma_send_gmail handle end.')

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        #self.common_chrome_driver.quit_chrome_with_tor()
        self.batch_status.end()
        self.logger.info('wowma_send_gmail handle end')
        # self.stdout.write(self.style.SUCCESS('end of wowma_get_src Command!'))
        return

    # 指定されたメール内容でGmail送信する
    def _exec_send_gmail(self, pk, mail_type, other_message):

        # 受注番号をコマンド引数 pk から取得。とれただけループして確認する
        self.logger.info('wowma_send_gmail _exec_send_gmail handle pk:[{}] type:[{}]'.format(pk, mail_type))

        # 指定された注文情報取得
        wow_order = WowmaOrderInfo.objects.filter(
            orderid=pk,
        ).first()

        # 注文がヒットしたら処理
        if wow_order:

            # 注文に基づく発送先
            order_receiver_list = {
                "order_name": wow_order.order_name,
                "sender_name": wow_order.sender_name,
                "sender_kana": wow_order.sender_kana,
                "sender_zipcode": wow_order.sender_zipcode,
                "sender_address": wow_order.sender_address,
                "sender_phone_number_1": wow_order.sender_phone_number_1,
                "sender_phone_number_2": wow_order.sender_phone_number_2,
                "sender_email": wow_order.mail_address,
                "total_sale_price": wow_order.total_sale_price,
                "settlement_name": wow_order.settlement_name,
                "delivery_name": wow_order.delivery_name,
                "postage_price": wow_order.postage_price,
                "total_item_option_price": wow_order.total_item_option_price,
                "charge_price": wow_order.charge_price,
                "premium_issue_price": wow_order.premium_issue_price,
                "use_point": wow_order.use_point,
                "use_au_point_price": wow_order.use_au_point_price,
                "shipping_date": wow_order.shipping_date,
                "shipping_carrier": wow_order.shipping_carrier,
                "shipping_number": wow_order.shipping_number,
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

            # 受注詳細を取得
            wowma_order_detail_list = WowmaOrderDetail.objects.filter(
                orderinfo=wow_order
            ).all()

            if not wowma_order_detail_list:
                self.logger.info('wowma_do_buyers_order _exec_buyers_order 該当の注文明細が見つからないので処理終了[{}]'.format(pk))
                raise Exception('_exec_buyers_order 該当の注文明細が見つからないので処理終了[{}]'.format(pk))

            # メール本文を作る
            subject, message = self._make_mail_message(
                mail_type,
                order_receiver_list,
                shop_info_list,
                wowma_order_detail_list,
                other_message,
            )

            # メール送信
            self.gmail.exec_send_mail(
                shop_info_list.get('shop_name'),
                wow_order.mail_address,
                #'kuurie7@gmail.com',
                subject,
                message,
            )

            # 注文確認メールか、発送通知メールのあとはステータスを更新する
            if int(mail_type) == 1:
                # 受注確認メールの文面にする
                self._upd_wowma_status(pk, '発送待ち')
            elif int(mail_type) == 2:
                # 発送通知メール
                self._upd_wowma_status(pk, '完了')

        else:
            # 注文がヒットなし
            self.logger.info('wowma_do_buyers_order _exec_buyers_order 該当の注文が見つからないので処理終了[{}]'.format(pk))
            raise Exception('_exec_buyers_order 該当の注文が見つからないので処理終了[{}]'.format(pk))

        self.logger.info('wowma_send_gmail _exec_send_gmail end')
        return

    # メール本文を作成
    # mail_type : 1:受注確認メール 2:発送通知 3:通常の連絡メール
    def _make_mail_message(self,
                mail_type,
                order_receiver_list,
                shop_info_list,
                wowma_order_detail_list,
                other_message):

        message = ""
        subject = ""
        try:
            sender_phone = order_receiver_list.get('sender_phone_number_1')
            if not sender_phone:
                sender_phone = order_receiver_list.get('sender_phone_number_2')
            if not sender_phone:
                sender_phone = '00000000000'
                # 共通文
            head_message = order_receiver_list.get('order_name') + '様\nご注文ありがとうございます。'
            head_message += shop_info_list.get('shop_name') + '通販担当の新谷です。\n'

            footer_message = '**********************\n\n'
            footer_message += shop_info_list.get('shop_name') + ' au PAY マーケット 店\n(担当：　新谷)\n'
            footer_message += 'mail ： ' + shop_info_list.get('mail')

            if int(mail_type) == 1:
                # 受注確認メールの文面にする
                subject = "ご注文ありがとうございます！（" + shop_info_list.get('shop_name') + "）"
                message = head_message + '以下のとおりご注文を承りました。\n\n'
                message += 'これより商品在庫の確保に入らせて頂きますので\n'
                message += '発送完了後、改めてメールさせて頂きます。\nどうぞよろしくお願いいたします。\n--------------------\n■送付先\n\n'
                message += '〒' + order_receiver_list.get('sender_zipcode') + '\n' + order_receiver_list.get('sender_address') + '\n'
                message += order_receiver_list.get('sender_name') + '様\nTEL : ' + sender_phone + '\n\n'
                message += '\n====================\n■ご購入商品\n\n'

                if wowma_order_detail_list:
                    for wowma_order_detail in wowma_order_detail_list:
                        self.logger.info('item_code:[{}]'.format(wowma_order_detail.item_code))
                        message += '取引ナンバー　　：' + str(wowma_order_detail.order_detail_id) + '\n'
                        message += '商品名　　　　　：' + wowma_order_detail.item_name + '\n'
                        message += 'オプション　　　：' + wowma_order_detail.item_option + '\n'
                        message += 'オプション(手数料型)：' + str(wowma_order_detail.item_option_price) + '\n'
                        message += '単価　　　　　　：' + str(wowma_order_detail.item_price) + '円\n'
                        message += '個数　　　　　　：' + str(wowma_order_detail.unit) + '\n'
                        message += '商品代金小計　　：' + str(wowma_order_detail.total_item_price) + '円\n'
                        message += '発送日・お届け予定日情報 ：' + wowma_order_detail.shipping_day_disp_text + '\n'
                        message += '--------------------\n\n'

                message += '■ご請求金額\n--------------------\n'
                message += '　◆商品代金計　：' + str(order_receiver_list.get('total_sale_price')) + '円\n'
                message += '　◆支払い方法　：' + order_receiver_list.get('settlement_name') + '\n'
                message += '　◆配送方法　　：' + order_receiver_list.get('delivery_name') + '\n'
                message += '　◆送料　　　　：' + str(order_receiver_list.get('postage_price')) + '円\n'
                message += '　◆オプション手数料(合計)：' + str(order_receiver_list.get('total_item_option_price')) + '円\n'
                message += '--------------------\n\n'
                message += '　◆請求額小計　：' + str(order_receiver_list.get('charge_price')) + '円\n'
                message += '　◆auスマートパスプレミアム特典プログラム適用額：' + str(order_receiver_list.get('premium_issue_price')) + '円\n'
                message += '　◆ポイント利用額：' + str(order_receiver_list.get('use_point')) + '円\n'
                message += '　◆Pontaポイント（au PAY マーケット限定含む）利用額  ：' + str(order_receiver_list.get('use_au_point_price')) + '円\n'
                message += '--------------------\n\n'
                message += '　◆お支払額　　：' + str(order_receiver_list.get('charge_price')) + '円\n\n'
                message += '====================\n\n'
                message += footer_message

            elif int(mail_type) == 2:
                # 発送通知メール

                """
                配送会社：
                "1:クロネコヤマト、2:佐川急便、3:JPエクスプレス（旧 日本通運）、4:福山通運、
                5:西濃運輸、6:日本郵便、9:その他配送会社"
                """
                shipping_carrier = ''
                shipping_query_url = ''
                if int(order_receiver_list.get('shipping_carrier')) == 1:
                    shipping_carrier = 'クロネコヤマト'
                    shipping_query_url = 'https://toi.kuronekoyamato.co.jp/cgi-bin/tneko'
                elif int(order_receiver_list.get('shipping_carrier')) == 2:
                    shipping_carrier = '佐川急便'
                    shipping_query_url = 'https://www.sagawa-exp.co.jp/send/howto-search.html'
                elif int(order_receiver_list.get('shipping_carrier')) == 3:
                    shipping_carrier = 'JPエクスプレス（旧 日本通運）'
                    shipping_query_url = 'https://www.tracking-status.com/ja/jp-express-tracking-online/'
                elif int(order_receiver_list.get('shipping_carrier')) == 4:
                    shipping_carrier = '福山通運'
                    shipping_query_url = 'https://corp.fukutsu.co.jp/situation/tracking_no'
                elif int(order_receiver_list.get('shipping_carrier')) == 5:
                    shipping_carrier = '西濃運輸'
                    shipping_query_url = 'https://track.seino.co.jp/cgi-bin/gnpquery.pgm'
                elif int(order_receiver_list.get('shipping_carrier')) == 6:
                    shipping_carrier = '日本郵便'
                    shipping_query_url = 'http://tracking.post.japanpost.jp/service/numberSearch.do?locale=ja&searchKind=S002'
                else:
                    shipping_carrier = 'その他配送会社'

                subject = "商品の発送が完了いたしました（" + shop_info_list.get('shop_name') + "）"
                message = head_message + 'ご注文いただきました商品の発送が完了いたしましたので\n以下の通りお知らせいたします。'
                message += '商品の到着まで今しばらくお待ちくださいませ。\n\nどうぞよろしくお願いいたします。\n\n'
                message += '--------------------\n■送付先\n\n〒' + order_receiver_list.get('sender_zipcode') + '\n'
                message += order_receiver_list.get('sender_address') + '\n'
                message += order_receiver_list.get('sender_name') + '様\n'
                message += 'TEL:' + sender_phone + '\n\n'
                message += '発送日： ' + order_receiver_list.get('shipping_date') + '\n'
                message += '配送業者：： ' + shipping_carrier + '\n'
                if order_receiver_list.get('shipping_number') in ('', '-', ' ', '　'):
                    """
                        if order_receiver_list.shipping_number == '' \
                        or order_receiver_list.shipping_number == '-' \
                        or order_receiver_list.shipping_number == ' ' \
                        or order_receiver_list.shipping_number == '　':
                    """
                    message += '※今回のお届けは追跡番号無しの配送サービスを利用しております。\n'
                    message += 'お手頃な価格でお届けするため、何卒ご理解のほどよろしくお願いいたします。\n'
                else:
                    message += 'お問い合わせ番号： ' + order_receiver_list.get('shipping_number') + '\n'
                    message += '荷物のお問い合わせは、下記からお願いいたします。\n'
                    message += shipping_query_url + '\n'

                message += '\n====================\n■ご購入商品\n\n'

                if wowma_order_detail_list:
                    for wowma_order_detail in wowma_order_detail_list:
                        self.logger.info('item_code:[{}]'.format(wowma_order_detail.item_code))
                        message += '取引ナンバー　　：' + str(wowma_order_detail.order_detail_id) + '\n'
                        message += '商品名　　　　　：' + wowma_order_detail.item_name + '\n'
                        message += 'オプション　　　：' + wowma_order_detail.item_option + '\n'
                        message += 'オプション(手数料型)：' + str(wowma_order_detail.item_option_price) + '\n'
                        message += '単価　　　　　　：' + str(wowma_order_detail.item_price) + '円\n'
                        message += '個数　　　　　　：' + str(wowma_order_detail.unit) + '\n'
                        message += '商品代金小計　　：' + str(wowma_order_detail.total_item_price) + '円\n'
                        message += '発送日・お届け予定日情報 ：' + wowma_order_detail.shipping_day_disp_text + '\n'
                        message += '--------------------\n\n'

                message += '■ご請求金額\n--------------------\n'
                message += '　◆商品代金計　：' + str(order_receiver_list.get('total_sale_price')) + '円\n'
                message += '　◆支払い方法　：' + order_receiver_list.get('settlement_name') + '\n'
                message += '　◆配送方法　　：' + order_receiver_list.get('delivery_name') + '\n'
                message += '　◆送料　　　　：' + str(order_receiver_list.get('postage_price')) + '円\n'
                message += '　◆オプション手数料(合計)：' + str(order_receiver_list.get('total_item_option_price')) + '円\n'
                message += '--------------------\n\n'
                message += '　◆請求額小計　：' + str(order_receiver_list.get('charge_price')) + '円\n'
                message += '　◆auスマートパスプレミアム特典プログラム適用額：' + str(order_receiver_list.get('premium_issue_price')) + '円\n'
                message += '　◆ポイント利用額：' + str(order_receiver_list.get('use_point')) + '円\n'
                message += '　◆Pontaポイント（au PAY マーケット限定含む）利用額  ：' + str(order_receiver_list.get('use_au_point_price')) + '円\n'
                message += '--------------------\n\n'
                message += '　◆お支払額　　：' + str(order_receiver_list.get('charge_price')) + '円\n\n'
                message += '====================\n\n'
                message += footer_message



            else:
                # 通常の連絡メール
                message = ''
                subject = "ご注文についてのご連絡でございます（" + shop_info_list.get('shop_name') + "）"
                message = head_message + 'ご注文につきまして、ご連絡がございます。\n\n'
                message += other_message.replace('＃＃＃', '\n')
                message += '\n'
                message += footer_message

        except Exception as e:
            self.batch_status.error_occurred(traceback.format_exc())
            self.logger.info(traceback.format_exc())
            traceback.print_exc()
            return

        return subject, message

    # wowmaのステータスを更新　ここで更新するのは発送待ちか、完了
    # order_status : 「発送待ち」「完了」
    def _upd_wowma_status(self, orderid, order_status):

        self.logger.info('wowma_send_gmail _upd_wowma_status orderid:[{}] status:[{}]'.format(orderid, order_status))

        msg = ''
        # wowmaにアクセス
        wowma_access = WowmaAccess(logger)

        res_list = wowma_access.wowma_update_trade_sts_proc(
            orderid,
            order_status,
            )

        for res_item in res_list:
            my_ret_code = res_item['res_code']
            my_ret_msg = res_item['res_msg']
            msg += my_ret_msg
            if my_ret_code == 0:
                # 更新に成功している。次の処理は行わない
                break

        d = {
            'msg': msg,
            'ret_code': my_ret_code,
        }
        self.logger.info('wowma_send_gmail _upd_wowma_status end')
        return d

"""
上戸 正輝様
ご注文ありがとうございます。
三五八制作通販担当の新谷です。

ご注文いただきました商品の発送が完了いたしましたので
以下の通りお知らせいたします。
商品の到着まで今しばらくお待ちくださいませ。

どうぞよろしくお願いします。

--------------------
■送付先

〒859-0312
長崎県 諫早市西里町810-8
上戸 正輝様
TEL：090-4481-1023
発送日： 2022/02/07
配送業者：日本郵便
お問い合わせ番号：-
荷物のお問い合わせは、下記からお願いします。
http://tracking.post.japanpost.jp/service/numberSearch.do?locale=ja&searchKind=S002

====================
■ご購入商品

取引ナンバー　　：459979965
--------------------
ロットナンバー　：542177343
商品名　　　　　：(ブラック、 S:7~13号) いびき防止 リング いびき防止グッズ 「快眠リング」 つぼ 無呼吸 安眠 いびき軽減 指輪 エーユードリーム
オプション　　　：
オプション(手数料型)：
単価　　　　　　：1,480円
個数　　　　　　：1
商品代金小計　　：1,480円 【軽減税率対象外(10%)】
発送日・お届け予定日情報 ：2月12日までにお届け
--------------------

■ご請求金額
--------------------
　◆商品代金計　：1,480円
　　　(10%対象：1,480円)
　　　( 8%対象：0円)
　　　( 0%対象：0円)
　◆支払い方法　：ポイントで全額支払う
　◆配送方法　　：ネコポス定形外郵便等
　◆送料　　　　：0円
　◆手数料　　　：0円
　◆オプション手数料(合計)：0円
--------------------
　◆請求額小計　：1,480円
　　　(10%対象：1,480円)
　　　( 8%対象：0円)
　　　( 0%対象：0円)
　◆auスマートパスプレミアム特典プログラム適用額：0円
　◆クーポン利用額：74円
　　　(10%対象：74円)
　　　( 8%対象：0円)
　　　( 0%対象：0円)
　◆ポイント利用額：0円
　◆Pontaポイント（au PAY マーケット限定含む）利用額  ：1,406円（1,406ポイント）
　　　(10%対象：1,406円)

　　　( 8%対象：0円)
　　　( 0%対象：0円)
--------------------
　◆お支払額　　：0円

====================

**********************

三五八制作 au PAY マーケット 店
担当：　新谷

mail ： info@take-value.biz


"""
