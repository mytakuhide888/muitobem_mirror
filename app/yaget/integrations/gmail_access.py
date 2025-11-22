# coding: UTF-8

# 参考： https://valmore.work/automate-gmail-sending/#Google_Cloud_PlatformGmail_API
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
from email.mime.text import MIMEText
from apiclient import errors
import traceback

import csv
import codecs
import time
import re
import sqlite3
import datetime
import sys, io
import time
import hmac
import logging
import imaplib, email
import glob
import shutil
import io as cStringIO
#from dateutil import parser
from email.header import decode_header
import http.client, configparser, codecs
from xml.dom.minidom import parse, parseString
from datetime import date
from email.utils import parsedate
from email.mime.text import MIMEText
from email.utils import formatdate
import smtplib

from contextlib import closing
from hashlib import sha256
from base64 import b64encode

from oauth2client.service_account import ServiceAccountCredentials



"""
以下は、バイヤーズ用。wowmaの受注をこなすため。
2022/2/5 に実装
"""

class GmailAccess(object):
    # 1. Gmail APIのスコープを設定
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    client_secret_path = '/app/yaget/gmail/client_secret_634387224658-54erkbd892akj1tu5b40v3sml364145d.apps.googleusercontent.com.json'

    def __init__(self, logger):
        self.logger = logger
        help = 'gmail access'
        self.logger.info('gmail_access in. init')

    # 2. メール本文の作成
    def create_message(self, sender, to, subject, message_text):
        message = MIMEText(message_text)
        message['To'] = to
        message['From'] = sender
        message['Subject'] = subject
        message['Date'] = formatdate()
        """
        encode_message = base64.urlsafe_b64encode(message.as_bytes())
        return {'raw': encode_message.decode()}
        """
        return message

    # 3. メール送信の実行
    def send_message(self, sendAddress, password, msg):
        try:
            # SMTPサーバに接続
            smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
            smtpobj.starttls()
            smtpobj.login(sendAddress, password)

            # 作成したメールを送信
            smtpobj.send_message(msg)
            smtpobj.close()

            self.logger.info('gmail_access send.')
            return
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
        except:
            self.logger.info(traceback.format_exc())
        return

    # 4. メインとなる送信処理
    def exec_send_mail(self, sender, to, subject, message):
        try:
            self.logger.info('gmail_access exec_send_mail in.')

            sendAddress = 'admin@take-value.biz'
            password = '@.Takumi358'

            message = self.create_message(sender, to, subject, message)
            # 7. Gmail APIを呼び出してメール送信
            self.send_message(sendAddress, password, message)
            self.logger.info('gmail_access exec_send_mail send end.')

        except:
            self.logger.info(traceback.format_exc())
            return False

        return True

class GmailAccess_bk20220213(object):
    # 1. Gmail APIのスコープを設定
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    client_secret_path = '/app/yaget/gmail/client_secret_634387224658-54erkbd892akj1tu5b40v3sml364145d.apps.googleusercontent.com.json'

    def __init__(self, logger):
        self.logger = logger
        help = 'gmail access'
        self.logger.info('gmail_access in. init')

    # 2. メール本文の作成
    def create_message(self, sender, to, subject, message_text):
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        encode_message = base64.urlsafe_b64encode(message.as_bytes())
        return {'raw': encode_message.decode()}

    # 3. メール送信の実行
    def send_message(self, service, user_id, message):
        try:
            message = (service.users().messages().send(userId=user_id, body=message)
                       .execute())
            #print('Message Id: %s' % message['id'])
            self.logger.info('gmail_access send. message id[{}]'.format(message['id']))
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
        except:
            self.logger.info(traceback.format_exc())
        return

    # 受注確認用 > いや、これはwowma側が処理すべきだな。gmailは違う
    """
    def make_messsage():
        try:
            moto_message = '■送付先 \n [送付先zipcode] \n [送付先住所] \n [送付先氏名]'
            zip_code = '329-1103'
            address = '栃木県 宇都宮市東岡本町１２２８'
            name = '小川 剛久'
            moto_message = moto_message.replace('[送付先zipcode]', zip_code)
            moto_message = moto_message.replace('[送付先住所]', address)
            moto_message = moto_message.replace('[送付先氏名]', name)
        except:
            print('error occurred meke_message')
        return moto_message
    """

    # 4. メインとなる送信処理
    def exec_send_mail(self, sender, to, subject, message):
        # 5. アクセストークンの取得
        try:
            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    """
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'creds/client_secret_634387224658-54erkbd892akj1tu5b40v3sml364145d.apps.googleusercontent.com.json', SCOPES)
                    """
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GmailAccess.client_secret_path, GmailAccess.SCOPES)
                    creds = flow.run_local_server()
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            service = build('gmail', 'v1', credentials=creds)
            # 6. メール本文の作成
            """
            sender = 'info@take-value.biz'
            to = 'kuurie7@gmail.com'
            subject = 'メール送信自動化テスト'
            message_text = 'メール送信の自動化テストをしています。'
            message_text = make_messsage()
            """
            message = self.create_message(sender, to, subject, message)
            # 7. Gmail APIを呼び出してメール送信
            self.send_message(service, 'me', message)
        except:
            self.logger.info(traceback.format_exc())
            return False

        return True
    """
    # 8. プログラム実行！
    if __name__ == '__main__':
        main()
    """



"""
=========================================================================
以下は、buyma用に作ってたモジュール。バイヤーズ用には今の所使ってない。
"""

# === 全体処理概要 =========================================================
# gmailに届いたatom売り切れ連絡を引っ張って、ebayにそのままアップロードする
# 参考：　https://symfoware.blog.fc2.com/blog-entry-891.html
#         https://qiita.com/hujuu/items/b75f8492000483bc66aa
#         https://docs.python.jp/3/library/imaplib.html
# gmail で二段階認証かけてるときはアプリパスワードをgoogleで生成し指定する
# https://plaza.rakuten.co.jp/kugutsushi/diary/201508060000/
# === 全体処理概要 =========================================================

# ファイル格納、共通処理 #######################################################
lgr = logging.getLogger('/app/eb_sample/mylog/mylog')
# 共通変数
mydwsrc_dir = "/app/eb_sample/enditem_file"
from_dwsrc_dir = "/app/eb_sample/enditem_file/to_upload"
done_dwsrc_dir = "/app/eb_sample/enditem_file/done_upload"

# gmail 関連設定
host = 'imap.gmail.com'
smtp_host = "smtp.gmail.com"

# password = '@Takuhide358'
mailbox = 'INBOX'
#LabelName = 'atom_soldout'

# 取得したアプリパスワード：
# rtjibfmolyqbzuuz


# gmail処理関連 #################################################################
class imap4mail(object):

    def __init__(self, data):
        """
        コンストラクタで与えられたメールデータの解析を実行する
        """
        self.files = {}

        # メッセージをパース
        #msg = email.message_from_string(data)
        msg = email.message_from_string(data.decode('utf-8'))

        msg_encoding = email.header.decode_header(msg.get('Subject'))[0][1] or 'iso-2022-jp'
        # パースして解析準備
        msg = email.message_from_string(data.decode(msg_encoding))

        print('imap4mail_init:msg:[{}]'.format(msg))
        # タイトル取得
        #self.title = self.decode(msg.get('Subject'))
        subject = email.header.decode_header(msg.get('Subject'))
        self.title = ""
        for sub in subject:
            if isinstance(sub[0], bytes):
                self.title += sub[0].decode(msg_encoding)
            else:
                self.title += sub[0]

        print('imap4mail_init:title:[{}]'.format(self.title))
        # 送信者取得
        self.sender = self.decode(msg.get('From'))
        # 送信日付取得
        self.date = self.get_format_date(msg.get('Date'))

        # 本文取得
        self.body = ""
        charset = msg.get_content_charset()
        if msg.is_multipart():
            print('本文はmulti')
            for payload in msg.get_payload():
                if payload.get_content_type() == "text/plain":
                    if charset:
                        self.body = payload.get_payload(decode=True).decode(charset)
                    else:
                        self.body = payload.get_payload(decode=True).decode()
        else:
            print('本文はテキスト')
            if msg.get_content_type() == "text/plain":
                if charset:
                    self.body = msg.get_payload(decode=True).decode(charset)
                else:
                    self.body = msg.get_payload(decode=True).decode()


        print ("タイトル:[{}]".format(self.title))
        print ("本文:[{}]".format(self.body))
        # 添付ファイルを抽出
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue

            # ファイル名を取得
            filename = part.get_filename()

            # ファイル名が取得できなければ本文
            if not filename:
                self.body = self.decode_body(part)

            # ファイル名が存在すれば添付ファイル
            else:
                print("filename:" + filename)
                tmpfile = cStringIO.StringIO()
                tmpfile.write(str(part.get_payload(decode=1).decode()))

                self.files[filename] = tmpfile

                """
                # ファイル書き込みしてみる
                myfilename = from_dwsrc_dir + '/' + filename
                f = codecs.open(myfilename, 'w', 'utf-8')
                #writer = csv.writer(f, lineterminator='\n')
                #writer.writerows(tmpfile.getvalue())
                f.write(tmpfile.getvalue())
                f.close()
                """

    def decode(self, dec_target):
        """
        メールタイトル、送信者のデコード
        """
        #decodefrag = email.header.decode_header(dec_target)
        #decodefrag = email.header.decode_header(msg.get('Subject'))[0][1] or 'iso-2022-jp'
        decodefrag = email.header.decode_header(dec_target)[0][1] or 'iso-2022-jp'

        title = ''

        for sub in decodefrag:
            if isinstance(sub[0],bytes):
                title += sub[0].decode(decodefrag)
            else:
                title += sub[0]
        return title
    """
        for frag, enc in decodefrag:
            if enc:
                title += unicode(frag, enc)
            else:
                title += unicode(frag)
    """

    def decode_body(self, part):
        """
        メール本文のデコード
        """
        body = ''
        charset = str(part.get_content_charset())

        # charset が設定されるらしいが固定でいってみる
        #if charset:
        #    body = unicode(part.get_payload(), charset)

        #else:
        #    body = part.get_payload()
        body = part.get_payload()

        return body

    def get_format_date(self, date_string):
        """
        メールの日付をtimeに変換
        http://www.faqs.org/rfcs/rfc2822.html
        "Jan" / "Feb" / "Mar" / "Apr" /"May" / "Jun" / "Jul" / "Aug" /"Sep" / "Oct" / "Nov" / "Dec"
        Wed, 12 Dec 2007 19:18:10 +0900
        """

        #format_pattern = '%a, %d %b %Y %H:%M:%S'

        # 3 Jan 2012 17:58:09という形式でくるパターンもあるので、
        # 先頭が数値だったらパターンを変更
        #if date_string[0].isdigit():
        #    format_pattern = '%d %b %Y %H:%M:%S'

        #return time.strptime(date_string[0:-6], format_pattern)
        #return parser.parse(date_string).strftime("%Y/%m/%d %H:%M:%S")
        #return date.strftime("%Y/%m/%d %H:%M:%S")
        #return date_string.strftime("%Y/%m/%d %H:%M:%S")
        print(date_string)
        print('parse:[{}]'.format(parsedate(date_string)))
        date_obj = parsedate(date_string)
        ret_date_string = "{}/{}/{} {}:{}:{}".format(
            str(date_obj[0]),
            str(date_obj[1]).zfill(2),
            str(date_obj[2]).zfill(2),
            str(date_obj[3]).zfill(2),
            str(date_obj[4]).zfill(2),
            str(date_obj[5]).zfill(2))
        print(ret_date_string)
        return ret_date_string

# gmail処理関連 #################################################################
class GmailAccess_bk1(object):

    #def __init__(self, logger):
    def __init__(self, logger):
        self.logger = logger
        help = 'gmail access init'
        self.logger.info('GmailAccess in. init')

        #    self.logger = logger
        help = 'get GmailAccess.'
        #self.logger.info('GmailAccess in. init')
        self.send_message = ""
        self.smtpclient = None

    def analize_mail(self, mail):
        # 取得したメールの内容を表示
        #print(mail.sender)
        #self.logger.info('analize_mail mail.date[{}]'.format(mail.date))
        #print(mail.title)
        #print(mail.body)

        for key, value in mail.files.items():
            #print ('keys:')
            #print (key)
            with open(key, 'w') as f:
                f.write(value.getvalue())

    def get_gmail(self, user, password):
        print('get_gmail start')
        #self.logger.info('get_gmail start')
        #lgr.info('start get_gmail')

        # メールサーバ指定
        M = imaplib.IMAP4_SSL(host=host)
        # ログイン
        M.login(user, password)

        print('gmail login ok')
        # メールボックス選択
        M.select(mailbox)

        #print('gmail select mail box')
        # 指定したラベルで絞り込み
        M.select(LabelName)

        print('gmail select label ')
        #typ, data = M.search(None, 'ALL')
        typ, data = M.search(None, "(UNSEEN)")
        print('gmail search result:[' + typ + ']')
        for num in data[0].split():
            typ, data = M.fetch(num, '(RFC822)')
            #mail = imap4mail(data[0][1].decode('iso-2022-jp'))
            mail = imap4mail(data[0][1])
            self.analize_mail(mail)

            # メールを未読に戻す (ひとまず既読にしたままとしたければここをコメントアウト
            M.store(num, '-FLAGS','\\SEEN')

        M.close()
        M.logout()

        print('end get_gmail.')
        #lgr.info('end get_gmail')

    def create_mail_mime_message(self, main_text):
        """
        (1) MIMEメッセージを作成する
        """
        #main_text = "これが本文です"
        charset = "utf-8"
        if charset == "utf-8":
            self.send_message = MIMEText(main_text, "plain", charset)
        elif charset == "iso-2022-jp":
            self.send_message = MIMEText(base64.b64encode(main_text.encode(charset, "ignore")), "plain", charset)

        return

    def create_mime_header(self, subject, from_address, to_address):
        """
        (2) MIMEメッセージに必要なヘッダを付ける
        * Gmailで送信する場合
          - Gmailの設定で「セキュリティの低いアプリの許可」を有効にする必要あり
          - https://myaccount.google.com/u/1/lesssecureapps?pageId=none
        """
        self.send_message.replace_header("Content-Transfer-Encoding", "base64")
        self.send_message["Subject"] = subject
        self.send_message["From"] = from_address
        self.send_message["To"] = to_address
        self.send_message["Cc"] = ""
        self.send_message["Bcc"] = ""
        self.send_message["Date"] = formatdate(None, True)

        return

    def create_smtp_client(self):
        """
        (3) SMTPクライアントインスタンスを作成する
        * yahoo!メールで送信する場合
          host: "smtp.mail.yahoo.co.jp"
          nego_combo: ("no-encrypt", 25) or ("no-encrypt", 587) or
                      ("ssl", 465)
        * Gmailで送信する場合
          host: "smtp.gmail.com"
          nego_combo: ("starttls", 587) or ("starttls", 25) or
                      ("ssl", 465)
        """
        #host = "smtp.gmail.com"
        nego_combo = ("starttls", 587)  # ("通信方式", port番号)

        if nego_combo[0] == "no-encrypt":
            self.smtpclient = smtplib.SMTP(smtp_host, nego_combo[1], timeout=10)
        elif nego_combo[0] == "starttls":
            self.smtpclient = smtplib.SMTP(smtp_host, nego_combo[1], timeout=10)
            self.smtpclient.ehlo()
            self.smtpclient.starttls()
            self.smtpclient.ehlo()
        elif nego_combo[0] == "ssl":
            context = ssl.create_default_context()
            self.smtpclient = smtplib.SMTP_SSL(smtp_host, nego_combo[1], timeout=10, context=context)
        self.smtpclient.set_debuglevel(2)  # サーバとの通信のやり取りを出力してくれる

        return

    def send_gmail(self, user, password,
                   from_address, to_address,
                   head_text, main_text):
        print('send_gmail start')
        #self.logger.info('get_gmail start')
        #lgr.info('start get_gmail')

        # MIMEメッセージ作成
        self.create_mail_mime_message(main_text)

        # MIMEメッセージに必要なヘッダを付ける
        self.create_mime_header(head_text, from_address, to_address)

        # (3) SMTPクライアントインスタンスを作成する
        self.create_smtp_client()

        # ログイン
        self.smtpclient.login(user, password)

        print('gmail login ok')
        # メール送信
        self.smtpclient.send_message(self.send_message)
        print('ok, send_gmail.')
        self.smtpclient.quit()

        print('end send_gmail.')
        #lgr.info('end get_gmail')


# main ############
def main():

    print('start call_upd_end_item.')
    #lgr.info('start call_upd_end_item')

    recv_user = 'doublenuts8@gmail.com'
    recv_password = 'rtjibfmolyqbzuuz'

    send_user = 'admin@take-value.biz'
    send_password = '@.Takumi358'

    #rtn = 0;
    # gmail 取り込み
    # LabelName =
    #label = 'wow_order' # wowmaの注文ラベル
    label = 'buyers_order'  # buyersの発注ラベル

    #GmailAccess().get_gmail(recv_user, recv_password, label)

    # gmail 取り込み
    GmailAccess().send_gmail(
        send_user,
        send_password,
        "info@take-value.biz",
        "doublenuts8@gmail.com",
        "これがtake-valueからの件名です",
        "これが本文です",
        )

    """

    # csv 読み込み
    file_list = glob.glob(from_dwsrc_dir + "/*")
    my_end_file = ''
    #print('chk file_list.')

    for my_file in file_list:
        print("file:" + my_file)
        #myfilename = mydwsrc_dir + '/' + 'test_1.txt'
        rtn = call_enditem(my_file)

        # csvの内容でenditem する
        #build_endItem_req(csv_res)

        # 処理が正常に終わってたら、ファイルを処理済みに移動する
        #my_end_file = os.path.basename(myfile)
        if rtn == 1:
            lgr.info('move to done_dir')
            #print('move to done_dir')
            new_file_path = shutil.move(my_file, done_dwsrc_dir)
            #lgr.info("new_file_path:" + new_file_path)
            #print("new_file_path:" + new_file_path)
        else:
            lgr.info('some error occurred. csv still in to_dir')
            print('some error occurred. csv still in to_dir')
    """

    #lgr.info('end of call_upd_end_item')
    print('end of call_upd_end_item.')
    return

if __name__ == '__main__': main()

