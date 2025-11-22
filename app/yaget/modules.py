from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import redirect
#from google import spreadsheet
import gspread
import subprocess
import traceback
from oauth2client.service_account import ServiceAccountCredentials
from time import sleep
import os, os.path
import re

# Create your views here.
from .models import (
    AmaCategory, WowmaCatTagOyaList, WowmaTagChildList,
    WowmaSpecDetail, WowmaShopInfo, WowCategory
)
from .forms import KickYagetForm
from .forms import FindForm

from django.db.models import Q
from django.db.models import Count, Sum, Avg, Min, Max
from .forms import CheckForm

from django.core.paginator import Paginator
from yaget.integrations.wowma_access import WowmaAccess
from yaget.integrations.qoo10_access import Qoo10Access
import yaget.integrations.error_goods_log


class CommonModules(object):

    def __init__(self, logger):
        self._logger = logger
        self.driver = None

        # google trans関連
        self._trans_cnt = 0  # get_translated_word の呼び出し先アカウントを覚えておく
        self._trans_target_url = [
            'https://script.google.com/macros/s/AKfycbx3uANmPUC0wDdEWMdZmf-aB1cf8Oga_sR_M0_fejD1fGQw04U/exec',
            'https://script.google.com/macros/s/AKfycbxyOWjdZrrlC8mQf_IH_ao44mamXiazuXv0aS6DuYFsSY4hitzK/exec',
            'https://script.google.com/macros/s/AKfycbydWkMZ5FUb7S9EkZK2_F0bSo6rQjoimB2f0vzyG5j_Iys6UQaX/exec',
            'https://script.google.com/macros/s/AKfycbzrhK-yu12yhYEz8fmgi540Lf1l9VRa3Zh7iIIOz7v7RTojce4H/exec',
            'https://script.google.com/macros/s/AKfycbwaC0JST3uGRQd2BjUgwilpUeVbPtZYIgnL4owal3y9C0MuQTY/exec',
            'https://script.google.com/macros/s/AKfycbwDw64__CqgdV4zmchfJmfQm3VO0aI_-AjDdE-pOG_5faNOHis/exec',
            'https://script.google.com/macros/s/AKfycbyHScoCJbSeEdKtGvX4iGri9uy5hj-xlsLMOzsd5MlwJtNGQw/exec',
            'https://script.google.com/macros/s/AKfycbzQcbGoKhb0m8lOtvuVZ1dPRniP-kZqjk1v0UWtTjRpmmg5ftQ/exec',
            'https://script.google.com/macros/s/AKfycbwqYTSsPVZJ5OrZY8vom1kavrWMFJngd6BC0T7pY4a8K79lp0yx/exec',
            'https://script.google.com/macros/s/AKfycbzvjRTzDH4x3F3ydMrTqPTz9xl6EYTJ7YzNbOR0qUNMahyk1mU/exec',
            'https://script.google.com/macros/s/AKfycby3O42O8cPZFedG3TZa0H6zpgeX7HG2RLlpt_YpRSZKhZqAced0/exec',
            'https://script.google.com/macros/s/AKfycbyg0xubxYhP-4bvKs1zL6wIYS3g9UD3K2MCnfV7dT04VWyGsi-V/exec',
            'https://script.google.com/macros/s/AKfycbwflOQjC-raqshfcDk-VFU921xVB34NzohS1gaWpiOSpBLWmQ0/exec',
        ]

    def cut_str(self, chk_str, max_len):
        try:
            tmp_str = chk_str[:max_len]
            if len(tmp_str) == max_len:
                # 最大文字数と同じならチェック（切り出したはず）
                i = 0
                while True:
                    i += 1
                    m = re.match(r'.+[ 　]$', tmp_str)
                    if m:
                        # もし空白マッチしたら、trimして終了
                        tmp_str = tmp_str.rstrip()
                        break
                    else:
                        max_len = len(tmp_str) - 1
                        # もし通常文字なら、一文字消して続行
                        tmp_str = tmp_str[:max_len]
                    if i == max_len:
                        break
            else:
                # この場合はそのままにする
                pass

            return tmp_str

        except Exception as e:
            print(traceback.format_exc())
            return False

    def force_timeout(self):
        os.system('systemctl restart httpd')
        return

    # torリスタート
    def restart_tor(self):
        try:
            # tor をリスタートしてIP切り替える
            args = ['sudo', 'service', 'tor', 'restart']
            subprocess.call(args)
            sleep(2)
            proxies = {
                'http': 'socks5://127.0.0.1:9050',
                'https': 'socks5://127.0.0.1:9050'
            }
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self._logger.info(traceback.format_exc())
            traceback.print_exc()
        return

    # headless chromeをtorセットして初期化する
    def init_chrome_with_tor(self):
        try:
            # tor をリスタートしてIP切り替える
            args = ['sudo', 'service', 'tor', 'restart']
            subprocess.call(args)
            sleep(2)
            proxies = {
                'http': 'socks5://127.0.0.1:9050',
                'https': 'socks5://127.0.0.1:9050'
            }

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')
            options.add_argument('--proxy-server=socks5://127.0.0.1:9050')

            self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self._logger.info(traceback.format_exc())
            traceback.print_exc()

        return

    # headless chromeをtorなしで初期化する
    def init_chrome_with_no_tor(self):
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')

            self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self._logger.info(traceback.format_exc())
            traceback.print_exc()

        return

    # headless chromeをcloseする
    def quit_chrome_with_tor(self):
        try:
            # self.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい
            self.driver.quit()  # quitは全ウィンドウを閉じてwebdriverセッションを終了する
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self._logger.info(traceback.format_exc())
            traceback.print_exc()

        return

    def restart_chrome(self):
        try:
            if self.driver:
                self.driver.quit()  # quitは全ウィンドウを閉じてwebdriverセッションを終了する

            # httpd restart
            self._logger.info('eb_restart_chrome restart httpd')
            self.force_timeout()
            sleep(3)

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')
            options.add_argument('--proxy-server=socks5://127.0.0.1:9050')

            self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self._logger.info(traceback.format_exc())
            traceback.print_exc()

        self._logger.info('eb_restart_chrome end')
        return

    def restart_chrome_no_tor(self):
        try:
            if self.driver:
                self.driver.quit()  # quitは全ウィンドウを閉じてwebdriverセッションを終了する

            # httpd restart
            self._logger.info('eb_restart_chrome restart httpd')
            self.force_timeout()
            sleep(3)

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,1024')

            self.driver = webdriver.Chrome(chrome_options=options)

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self._logger.info(traceback.format_exc())
            traceback.print_exc()

        self._logger.info('eb_restart_chrome end')
        return

    # 自作のgoogle transAPIを呼び出して翻訳した文字列を得る
    def get_translated_word(self, word, from_lang, to_lang):
        # 翻訳する文章
        """
        以下が呼び出し用API
        kuurie7のアカウントに紐づけて作った
        場所はここ。kuurie7@gmail.comのgoogle driveにて
        https://script.google.com/d/1G7-CJLUtHXDsawkjAiGXYY-Uh08rrq5b9yF9HQU9E8JSAUxpABUmpTwZ/edit?usp=drive_web

        function doGet(e) {
          var p = e.parameter;
          var translatedText = LanguageApp.translate(p.text, p.source, p.target);
          return ContentService.createTextOutput(translatedText);
        }

        """
        #myurl = 'https://script.google.com/macros/s/AKfycbx3uANmPUC0wDdEWMdZmf-aB1cf8Oga_sR_M0_fejD1fGQw04U/exec'
        #from_lang = 'ja'
        #to_lang = 'en'

        # カウント中の配列から、リクエストするgoogle transのスクリプトを呼び出す。
        # 翻訳がエラーになったら次のURLに切り替えないといけない
        payload = {'text': word, 'source': from_lang, 'target': to_lang}
        r = ''
        for i in range(len(self._trans_target_url)):
            myurl = self._trans_target_url[self._trans_cnt]
            r = requests.get(myurl, params=payload)
            # エラーになったら「errorMessage」が含まれてくる
            if 'errorMessage' in r.text:
                self._trans_cnt += 1
                if self._trans_cnt >= len(self._trans_target_url):
                    self._trans_cnt = 0  # 配列一周してたら0に
            else:
                break
        return r.text

    # 半角スペースで区切られた文字列から重複文字と不要文字を削除する
    @staticmethod
    def get_ddjasted_keyword(moto_key):
        tmp_list_moto = moto_key.split(" ")
        tmp_list_unique = list(set(tmp_list_moto))
        ret_str = ' '.join(tmp_list_unique)

        # 不要文字は削除
        ret_str = ret_str.replace('\'s ',' ')
        ret_str = ret_str.replace('\'s','')
        return ret_str

    # 扱いOKだが、商品名・商品説明から削除しておくブランドコード
    _MY_DEL_WORDS = [
        'Amazon.co.jp',
        'AMAZON.CO.JP',
        'Amazon.com',
        'AMAZON.COM',
        'Amazon',
        'AMAZON',
        'アマゾン',
        '【送料無料】',
        '（送料無料）',
        '☆彡　送料無料',
        '★送料無料',
    ]

    # Shift-jis変換が効かない文字などを変換する。
    _MY_EXCHANGE_WORDS = [
        ['㎝', 'cm'],
        ['㎏', 'kg'],
        ['㎎', 'mg'],
        ['゙', '”'],
        ['゚|\u02da', '°'],
        ['♫', '♪'],
        ['♬', '♪'],
        ['Ⅿ', 'M'],
        ['Ⅽ', 'C'],
        ['Ⅼ', 'L'],
        ['✕', 'Ｘ'],
        ['－', '-'],
        ['✅', '■'],
        ['‼', '！'],
        ['※|\u2733', '※'],
        [', ', '、'],
        ['\n', '<br/>'],
        ['～|\u223c', '~'],
        ['•|◎', '●'],
        ['\u2014|–', '-'],
        ['：', ':'],
        ['バストアップ', '育乳'],
        ['\u2460|\u2780|\u2160', '１'],
        ['\u2461|\u2781|\u2161', '２'],
        ['\u2462|\u2782|\u2162', '３'],
        ['\u2463|\u2783|\u2163', '４'],
        ['\u2464|\u2784|\u2164', '５'],
        ['\u2465|\u2785|\u2165', '６'],
        ['\u2466|\u2786|\u2166', '７'],
        ['\u2467|\u2787|\u2167', '８'],
        ['\u2468|\u2788|\u2168', '９'],
        ['\u2469|\u2789|\u2169', '１０'],
        ['\u24b6', 'A.'],
        ['\u24b7', 'B.'],
        ['\u24b8', 'C.'],
        ['\u24b9', 'D.'],
        ['\u24ba', 'E.'],
        ['\ufe0f', ':'],
        ['\u2762', '！'],
        ['\u2764', '・'],
        ['\u2b1b|\u26ab|\U0001f9f6|\u2600|\U0001f9e3|\U0001f381|\U0001f4a1|\u25fc|\u263a', '■'],
        ['\u2660|\u2661|\u2662', '■'],
        ['\uf06c|\'', ''],
        ['\u339c', 'mm'],
        ['\u2728|\u2729', '★'],
        ['|♡|♠|♢|✔|♥|♣|♧|♦|♨|♩|╰|︶|╯|\u202a|\u7e6b|\ufe0e|\u525d|\u5e26|\u02ca|\u1d55|\u02cb|\u6d01|\u26a0', ''],
        ['\uf0b7|\u26aa|\u52bf|\u2b50', ''],
    ]

    # 指定された文字列中から不要文字をチェックしてマッチしたら消し込む。
    # ブラックリストのチェックはAmaSPA chk_black_list でやってるはずだからここではやらない
    # return:
    #  不要文字を消し込んだ文字列
    def chk_goods_str(self, chk_str):
        try:
            # 変換する文字。shift-jis変換でコケた文字はここに登録
            for exchange_words in __class__._MY_EXCHANGE_WORDS:
                chk_str = re.sub(exchange_words[0], exchange_words[1], chk_str)

            # NGな文章も消しておく
            for ng_words in __class__._MY_DEL_WORDS:
                chk_str = re.sub(ng_words, "", chk_str)

            return chk_str

        except Exception as e:
            raise


class TestMsgModule(object):
    def get_message(self):
        return ('test get_message ok')


class GSpreadModule(object):
    scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

    def __init__(self, mykeyfilename = None):
        if mykeyfilename is not None:
            self.keyfilename = mykeyfilename
        else:
            self.keyfilename = '/app/yaget/test-app-flex-1-542896fdd03c.json'

    def get_gsheet(self, gsheetname):
        # シートをopenして返却する。とりあえずシートは sheet1 で固定
        if gsheetname is None:
            return None
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.keyfilename, self.scope)
        gc = gspread.authorize(credentials)
        wks = gc.open(gsheetname).sheet1
        return wks


# バッチコマンドなどから共通で呼び出されるqoo10関連実行クラス
class ExecQoo10(object):

    def __init__(self, logger):
        self._logger = logger
        self._qoo10_access = Qoo10Access(self._logger)
        self._qoo10_access.qoo10_create_cert_key()

    def exec_qoo10_goods_update(self, myobj):
        """ qoo10の商品を更新する
        params: myobj YaBuyersItemDetail 商品情報
        return: true, msg 正常終了
                false, error_msg 異常終了
        """
        try:
            # qoo10 更新 ###################################################################################################
            #     qoo_upd_status = ((1, '取引待機'), (2, '取引可能'), (3, '取引廃止'))
            #     qoo_on_flg = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
            # qooについて画面から1(出品OK)もしくは3（在庫切れ）になっている対象は、以下で掲載状況を確認して更新してゆく
            if myobj.qoo_on_flg == 1 or myobj.qoo_on_flg == 3:

                # 出品OKなのに在庫０なら、そのまま未掲載にしておく
                if int(myobj.stock) == 0:
                    if myobj.qoo_upd_status == 1 or myobj.qoo_upd_status == 3:  # qoo未掲載
                        # 未掲載 qoo_upd_status = 1（取引待機）もしくは3（登録済みだが取引廃止）
                        # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                        self._logger.info('--> exec_qoo10_goods_update 出品OKなのに在庫０　未掲載のまま')
                        myobj.qoo_on_flg = 3
                    else:
                        # 掲載中 qoo_upd_status = 2 取引可能
                        # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない、かつ登録済みだが未掲載に切り替える
                        myobj.qoo_on_flg = 3  # 更新成功したら 在庫切れにする。出品OK状態はそのまま、qoo掲載状況は取引待機になってる
                        myobj.qoo_upd_status = 1  # 取引待機に
                        # 商品更新のセットを投げる
                        try:
                            self._qoo10_access.qoo10_my_set_update_goods(myobj)
                            self._logger.info('--> exec_qoo10_goods_update 在庫切れにした。')
                        except Exception as e:
                            self._logger.info(traceback.format_exc())
                            self._logger.info('--> exec_qoo10_goods_update 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                            my_err_list = {
                                'batch_name': 'ExecQoo10 exec_qoo10_goods_update',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': '',
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            return False, traceback.format_exc()  # DB更新せずに戻す

                # 　在庫がある
                elif int(myobj.stock) > 0:
                    # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                    if myobj.qoo_upd_status == 1:  # 取引待機（1）は未登録か、登録済みだが在庫0で更新された場合も。
                        if myobj.qoo_gdno:  # 商品登録済み
                            # 商品更新のセットを投げる
                            myobj.qoo_on_flg = 1  # OKに。
                            myobj.qoo_upd_status = 2  # 掲載中に更新
                            try:
                                self._qoo10_access.qoo10_my_set_update_goods(myobj)
                                self._logger.info('--> exec_qoo10_goods_update 出品OKで在庫あるので掲載中に更新！ 1')
                            except Exception as e:
                                self._logger.info(traceback.format_exc())
                                self._logger.info('--> exec_qoo10_goods_update 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                                my_err_list = {
                                    'batch_name': 'ExecQoo10 exec_qoo10_goods_update',
                                    'gid': myobj.gid,
                                    'status': 1,
                                    'code': '',
                                    'message': traceback.format_exc(),
                                }
                                error_goods_log.exe_error_log(my_err_list)
                                return False, traceback.format_exc()  # DB更新せずに戻す
                        else:
                            self._logger.info('--> exec_qoo10_goods_update 未登録だが出品OKで在庫あるので登録開始')
                            # 未掲載 qoo_upd_status = 0 なら新規登録する
                            myobj.qoo_on_flg = 1  # OKに。
                            myobj.qoo_upd_status = 2  # 掲載中に更新

                            # 商品登録のセットを投げる
                            try:
                                self._qoo10_access.qoo10_my_set_new_goods(myobj)
                                self._logger.info('--> exec_qoo10_goods_update 在庫あり、未登録だったので新規登録OK！')
                            except Exception as e:
                                self._logger.info(traceback.format_exc())
                                self._logger.info('--> exec_qoo10_goods_update 新規登録中にエラーになったがそのまま続行する。後で要確認')
                                my_err_list = {
                                    'batch_name': 'ExecQoo10 exec_qoo10_goods_update',
                                    'gid': myobj.gid,
                                    'status': 1,
                                    'code': '',
                                    'message': traceback.format_exc(),
                                }
                                error_goods_log.exe_error_log(my_err_list)
                                return False, traceback.format_exc()  # DB更新せずに戻す
                    else:
                        # 掲載中 qoo_upd_status = 2　か、登録済みだが未掲載 3 （これまで在庫０だった）
                        # 現在の在庫数で更新する、未掲載だったら復活させる
                        myobj.qoo_on_flg = 1  # 更新成功した。
                        myobj.qoo_upd_status = 2  # 掲載中に更新

                        # 商品更新のセットを投げる
                        try:
                            self._qoo10_access.qoo10_my_set_update_goods(myobj)
                            self._logger.info('--> exec_qoo10_goods_update 出品OKで在庫あるので掲載中に更新！')
                        except Exception as e:
                            self._logger.info(traceback.format_exc())
                            self._logger.info('--> exec_qoo10_goods_update 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                            my_err_list = {
                                'batch_name': 'ExecQoo10 exec_qoo10_goods_update',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': '',
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            return False, traceback.format_exc()  # DB更新せずに戻す

                    """
                    if myobj.qoo_upd_status != 0:
                        # 登録済みだったら、在庫状況によらず商品内容をupdateする
                        myobj.qoo_on_flg = 1  # OKのまま
                        myobj.qoo_upd_status = 1  # 掲載中に
                        # 商品更新のセットを投げる
                        self._qoo10_access.qoo10_my_set_update_goods(myobj)
                    """
                else:  # 在庫数の取得エラー？
                    # raise Exception("在庫数の取得に失敗？stock:[{}] gid:[{}]".format(myobj.stock, myobj.gid))
                    return False, "在庫数の取得に失敗？stock:[{}] gid:[{}]".format(myobj.stock, myobj.gid)  # DB更新せずに戻す

            else:
                # ここにきたら、qoo_on_flg は 0（確認中）か2（NG）のはず。
                if myobj.qoo_on_flg == 2:
                    self._logger.info('--> exec_qoo10_goods_update qoo 未出品に更新しないと flg=2 （NG）')
                    if myobj.qoo_upd_status != 1:  # 登録済みのものは未掲載に倒さないと
                        myobj.qoo_on_flg = 2  # NGのまま。
                        myobj.qoo_upd_status = 1  # 取引待機に

                        # 商品更新のセットを投げる
                        try:
                            self._qoo10_access.qoo10_my_set_update_goods(myobj)
                            self._logger.info('--> exec_qoo10_goods_update qoo 出品OKで在庫あるので掲載中に更新！')
                        except Exception as e:
                            self._logger.info(traceback.format_exc())
                            self._logger.info('--> exec_qoo10_goods_update 掲載中に更新中にエラーになったがそのまま続行する。後で要確認')
                            my_err_list = {
                                'batch_name': 'ExecQoo10 exec_qoo10_goods_update',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': '',
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            return False, traceback.format_exc()  # DB更新せずに戻す

                    else:
                        # 更新時にエラー？
                        self._logger.info(
                            '--> exec_qoo10_goods_update qoo 未出品に更新しないと flg=2 （NG）qoo_upd_status:[{}]'.format(
                                myobj.qoo_upd_status))
                        """
                        raise Exception("qoo 出品NGで在庫あったのでNGにする更新中に失敗？ gid:[{0}] stock:[{1}]".format(
                            myobj.gid, myobj.stock))
                        """
                        # 2021/11/16 ひとまず初期登録中なのでエラーになってもそのまま進んでしまう。後で直すこと！
                        return False, "qoo 未出品に更新しないと flg=2 （NG）qoo_upd_status:[{}]".format(
                                myobj.qoo_upd_status)  # DB更新せずに戻す
                else:
                    self._logger.info('--> exec_qoo10_goods_update qoo 在庫あるがNGフラグたってて未出品なので処理せず flg=0 ')

            # ここまで到達したら商品の状態は更新してしまう
            myobj.save()
        except:
            return False, traceback.format_exc()  # DB更新せずに戻す

        return True, "qoo10 更新 正常終了"


# バッチコマンドなどから共通で呼び出されるwowma関連実行クラス
class ExecWowma(object):

    def __init__(self, logger):
        self._logger = logger
        self._wowma_access = WowmaAccess(self._logger)
        self._common_module = CommonModules(self._logger)

    def set_wowma_gid(self, myobj):
        # 商品コードと管理用商品名（asin）のセット

        # 商品コードは自動採番のidを15桁で0埋めして、先頭にBA111をつける
        myobj.gid = 'BA111{:0>15}'.format(myobj.id)

        # 管理用商品名はasinをそのまま入れてみる
        myobj.gcode = myobj.asin.asin
        myobj.save()
        return

    def build_gname_for_wowma(self, myobj):
        # 商品名をwowma用に組み立てる
        # 抽出対象は QooAsinDetail
        # 候補は title か、スクレイピングした product_title
        # ひとまず titleにしよう
        # 保存先は WowmaGoodsDetailのwow_gname
        gname = myobj.asin.title.strip()
        # wowmaの商品名は100文字とする
        myobj.wow_gname = self._common_module.cut_str(
            self._common_module.chk_goods_str(gname), 100)
        myobj.save()
        return

    def build_gdetail_for_wowma(self, myobj):
        # param: myobj (WowmaGoodsDetail)
        # Todo: 作成中 2023/07/01
        # 商品詳細をwowma用に組み立てる、連結時は<br>でいこう
        # 抽出対象は QooAsinDetail

        # 候補は・・
        # --- wow_gdetail (長さ 半角1024) に格納
        # feature （微妙）
        # スクレイピング結果より、全部連結させる
        # description

        # --- wow_descriptionForSP と wow_descriptionForPC (長さ 半角10240) に格納
        # p_o_f_0 - 9
        # f_b_0 - 9
        # p_d_t_s_th_0 - 9  (th) と p_d_t_s_td_0 - 9 （td）の組み合わせ
        # p_d_0 - 9
        # p_a_m_w_0 - 4

        # --- wow_detailDescription (長さ 半角640) に格納
        # 商品詳細コンテンツ
        # p_a_s_m_0

        gdetail = ''
        if myobj.asin.feature:
            gdetail += myobj.asin.feature.strip() + '&lt;br&gt;'
        if myobj.asin.description:
            gdetail += myobj.asin.description.strip() + '&lt;br&gt;'

        descriptionForSPorPC = ''
        if myobj.asin.p_o_f_0:
            descriptionForSPorPC += myobj.asin.p_o_f_0.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_1:
            descriptionForSPorPC += myobj.asin.p_o_f_1.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_2:
            descriptionForSPorPC += myobj.asin.p_o_f_2.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_3:
            descriptionForSPorPC += myobj.asin.p_o_f_3.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_4:
            descriptionForSPorPC += myobj.asin.p_o_f_4.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_5:
            descriptionForSPorPC += myobj.asin.p_o_f_5.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_6:
            descriptionForSPorPC += myobj.asin.p_o_f_6.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_7:
            descriptionForSPorPC += myobj.asin.p_o_f_7.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_8:
            descriptionForSPorPC += myobj.asin.p_o_f_8.strip() + '&lt;br&gt;'
        if myobj.asin.p_o_f_9:
            descriptionForSPorPC += myobj.asin.p_o_f_9.strip() + '&lt;br&gt;'

        if myobj.asin.f_b_0:
            descriptionForSPorPC += myobj.asin.f_b_0.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_1:
            descriptionForSPorPC += myobj.asin.f_b_1.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_2:
            descriptionForSPorPC += myobj.asin.f_b_2.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_3:
            descriptionForSPorPC += myobj.asin.f_b_3.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_4:
            descriptionForSPorPC += myobj.asin.f_b_4.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_5:
            descriptionForSPorPC += myobj.asin.f_b_5.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_6:
            descriptionForSPorPC += myobj.asin.f_b_6.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_7:
            descriptionForSPorPC += myobj.asin.f_b_7.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_8:
            descriptionForSPorPC += myobj.asin.f_b_8.strip() + '&lt;br&gt;'
        if myobj.asin.f_b_9:
            descriptionForSPorPC += myobj.asin.f_b_9.strip() + '&lt;br&gt;'

        if myobj.asin.p_d_t_s_th_0 and myobj.asin.p_d_t_s_td_0:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_0.strip() + ':' + myobj.asin.p_d_t_s_td_0.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_1 and myobj.asin.p_d_t_s_td_1:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_1.strip() + ':' + myobj.asin.p_d_t_s_td_1.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_2 and myobj.asin.p_d_t_s_td_2:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_2.strip() + ':' + myobj.asin.p_d_t_s_td_2.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_3 and myobj.asin.p_d_t_s_td_3:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_3.strip() + ':' + myobj.asin.p_d_t_s_td_3.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_4 and myobj.asin.p_d_t_s_td_4:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_4.strip() + ':' + myobj.asin.p_d_t_s_td_4.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_5 and myobj.asin.p_d_t_s_td_5:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_5.strip() + ':' + myobj.asin.p_d_t_s_td_5.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_6 and myobj.asin.p_d_t_s_td_6:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_6.strip() + ':' + myobj.asin.p_d_t_s_td_6.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_7 and myobj.asin.p_d_t_s_td_7:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_7.strip() + ':' + myobj.asin.p_d_t_s_td_7.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_8 and myobj.asin.p_d_t_s_td_8:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_8.strip() + ':' + myobj.asin.p_d_t_s_td_8.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_t_s_th_9 and myobj.asin.p_d_t_s_td_9:
            descriptionForSPorPC += myobj.asin.p_d_t_s_th_9.strip() + ':' + myobj.asin.p_d_t_s_td_9.strip() + '&lt;br&gt;'

        if myobj.asin.p_d_0:
            descriptionForSPorPC += myobj.asin.p_d_0.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_1:
            descriptionForSPorPC += myobj.asin.p_d_1.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_2:
            descriptionForSPorPC += myobj.asin.p_d_2.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_3:
            descriptionForSPorPC += myobj.asin.p_d_3.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_4:
            descriptionForSPorPC += myobj.asin.p_d_4.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_5:
            descriptionForSPorPC += myobj.asin.p_d_5.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_6:
            descriptionForSPorPC += myobj.asin.p_d_6.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_7:
            descriptionForSPorPC += myobj.asin.p_d_7.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_8:
            descriptionForSPorPC += myobj.asin.p_d_8.strip() + '&lt;br&gt;'
        if myobj.asin.p_d_9:
            descriptionForSPorPC += myobj.asin.p_d_9.strip() + '&lt;br&gt;'
        if myobj.asin.p_a_m_w_0:
            descriptionForSPorPC += myobj.asin.p_a_m_w_0.strip() + '&lt;br&gt;'
        if myobj.asin.p_a_m_w_1:
            descriptionForSPorPC += myobj.asin.p_a_m_w_1.strip() + '&lt;br&gt;'
        if myobj.asin.p_a_m_w_2:
            descriptionForSPorPC += myobj.asin.p_a_m_w_2.strip() + '&lt;br&gt;'
        if myobj.asin.p_a_m_w_3:
            descriptionForSPorPC += myobj.asin.p_a_m_w_3.strip() + '&lt;br&gt;'
        if myobj.asin.p_a_m_w_4:
            descriptionForSPorPC += myobj.asin.p_a_m_w_4.strip() + '&lt;br&gt;'

        detailDescription = ''
        if myobj.asin.p_a_s_m_0:
            detailDescription += myobj.asin.p_a_s_m_0.strip() + '&lt;br&gt;'

        # wowma は < >をエスケープ タグ文字は入ってていいかな。<br>とか
        gdetail = re.sub('<', '&lt;', gdetail)
        gdetail = re.sub('>', '&gt;', gdetail)
        descriptionForSPorPC = re.sub('<', '&lt;', descriptionForSPorPC)
        descriptionForSPorPC = re.sub('>', '&gt;', descriptionForSPorPC)
        detailDescription = re.sub('<', '&lt;', detailDescription)
        detailDescription = re.sub('>', '&gt;', detailDescription)

        # 不要文字削除など
        # 全角で512文字
        gdetail = self._common_module.cut_str(
            self._common_module.chk_goods_str(gdetail), 512)
        # 全角で5120文字
        descriptionForSPorPC = self._common_module.cut_str(
            self._common_module.chk_goods_str(descriptionForSPorPC), 5120)
        # 全角で320文字
        detailDescription = self._common_module.cut_str(
            self._common_module.chk_goods_str(detailDescription), 320)

        # myobjに格納
        myobj.wow_gdetail = gdetail
        myobj.wow_descriptionForSP = descriptionForSPorPC
        myobj.wow_descriptionForPC = descriptionForSPorPC
        myobj.wow_detailDescription = detailDescription
        myobj.save()
        return

    def set_wow_hinmei(self, myobj):
        """
        ロジスピに必要な品名をセットしてみる。
        wow_ctidから末尾のカテゴリ名を抜き出して品名に転用。
        「その他」とある文言は削除しておく
        """
        if myobj.wow_ctid > 0:
            # wow_hinmei
            # 対応するカテゴリ
            wow_ct_obj = WowCategory.objects.get(product_cat_id=myobj.wow_ctid)
            if wow_ct_obj:
                tmp_ct_name = ''
                ct_set_flg = False
                if wow_ct_obj.level_4_cat_name:
                    if len(wow_ct_obj.level_4_cat_name) > 0:
                        tmp_ct_name = wow_ct_obj.level_4_cat_name
                        ct_set_flg = True
                if (ct_set_flg is False) and wow_ct_obj.level_3_cat_name:
                    if len(wow_ct_obj.level_3_cat_name) > 0:
                        tmp_ct_name = wow_ct_obj.level_3_cat_name
                        ct_set_flg = True
                if (ct_set_flg is False) and wow_ct_obj.level_2_cat_name:
                    if len(wow_ct_obj.level_2_cat_name) > 0:
                        tmp_ct_name = wow_ct_obj.level_2_cat_name
                        ct_set_flg = True
                if (ct_set_flg is False) and wow_ct_obj.level_1_cat_name:
                    if len(wow_ct_obj.level_1_cat_name) > 0:
                        tmp_ct_name = wow_ct_obj.level_1_cat_name
                        ct_set_flg = True

                # 不要文字削除
                tmp_ct_name = re.sub('その他', "", tmp_ct_name)

                myobj.wow_hinmei = tmp_ct_name

        return

    def set_wowma_ctid(self, myobj):
        """
        wowmaのカテゴリIDをセットする。
        ・Amaの商品情報からAmaのカテゴリIDを取得
            もとは QooAsinDetail p_cat_id_0

        ・p_cat_id_0 は、3369254051　のように「セール」用の一時的なIDが入ってきて、
          amaのカテゴリリストと一致しない場合もある・・その場合はp_cat_id_1, p_cat_id_2 も見る
        ・AmaのカテゴリIDからwowmaのカテゴリIDは引っ張れるはず・・・
        ・最終的にセットするのは WowmaGoodsDetail.wow_ctid
        """
        ama_ctid = myobj.asin.p_cat_id_0  # amaのカテゴリID
        self._logger.debug('set_wowma_ctid start :ama_ctid:[{}] wow_ctid:[{}]'.format(myobj.ama_ctid, myobj.wow_ctid))
        # 紐づけを取ってこないと
        # AmaCategory.product_cat_id にあてて wow_cat_id を得る
        ama_cat_obj = AmaCategory.objects.filter(
            product_cat_id=ama_ctid,
        ).first()
        if ama_cat_obj:
            myobj.ama_ctid = ama_ctid
            myobj.wow_ctid = ama_cat_obj.wow_cat_id
        else:
            ama_ctid = myobj.asin.p_cat_id_1  # amaのカテゴリID 1
            ama_cat_obj = AmaCategory.objects.filter(
                product_cat_id=ama_ctid,
            ).first()
            if ama_cat_obj:
                myobj.ama_ctid = ama_ctid
                myobj.wow_ctid = ama_cat_obj.wow_cat_id
            else:
                ama_ctid = myobj.asin.p_cat_id_2  # amaのカテゴリID 2
                ama_cat_obj = AmaCategory.objects.filter(
                    product_cat_id=ama_ctid,
                ).first()
                if ama_cat_obj:
                    myobj.ama_ctid = ama_ctid
                    myobj.wow_ctid = ama_cat_obj.wow_cat_id

        # ロジスピの商品登録に必要な品名をカテゴリからセットしてみる
        self.set_wow_hinmei(myobj)

        myobj.save()
        self._logger.debug('set_wowma_ctid end :ama_ctid:[{}] wow_ctid:[{}] hinmei:[{}]'.format(myobj.ama_ctid, myobj.wow_ctid, myobj.wow_hinmei))
        return

    def set_stock(self, myobj):
        """
        在庫数のセット
        Amaの在庫数QooAsinDetailからwowmaのWowmaGoodsDetail.stock在庫数へ転記
        Amaは、amountと カート在庫数であるbuybox_quantitytierがある。どっちを取るか・・
        buyboxの方を適用しよう。
        また、在庫数1のとき扱いどうするか。0にして販売させないか、そのまま売るか・・
        ひとまずそのまま売るか。
        Todo: 未完
        """
        myobj.stock = myobj.asin.buybox_quantitytier
        myobj.save()
        return

    def build_tag_for_wowma(self, myobj):
        """
        # wowma用のタグIDをセットして返す。商品名のキーワードにマッチする検索タグを
        # 64個までセットして半角スペース区切りに。
        # ★これを呼び出すまでにwowmaのカテゴリIDは取得済みであること。
        #   myobj.wow_ctid にセットしておかないと。
        # wowmaに登録するときは注意のこと
        # タグとカテゴリとのマッピングはこちら wow_cat
        # https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=2027093015

        古いモジュール だいぶ流用できそうではある。
        myobj.wow_tagid = self._buinfo_obj.get_wow_tagid_list(
            myobj.bu_ctid, myobj.wow_gname, myobj.wow_ctid)
        """
        ctcode = myobj.wow_ctid  # wowma のカテゴリIDでよいよね
        if not ctcode or ctcode == 0:
            self._logger.debug('build_tag_for_wowma:ctcode: none or 0. return')
            return
        self._logger.debug('build_tag_for_wowma:in ctcode:[{}]'.format(ctcode))

        ret_str = ''
        new_list = []

        try:
            # WowmaCatTagOyaList, WowmaTagChildList
            oya = WowmaCatTagOyaList.objects.filter(
                wow_cat_id=ctcode,
            ).first()
            if oya:
                self._logger.info('build_tag_for_wowma:2 登録済み親idと一致 gname:[{}]'.format(myobj.wow_gname))
            else:
                self._logger.info('build_tag_for_wowma:3 親idと一致せず。処理終了')
                return

            # 商品名から、紐付けるキーワード（ブラック　とか）を抽出
            tmp_list_keyword = myobj.wow_gname.split(" ")

            # 10040000 10270000 10280000 とか。
            tmp_list_moto = oya.tag_grp.split(" ")

            # 紐付いている親タグから、小タグを探す
            list_cnt = 0
            for tag_moto in tmp_list_moto:
                child_list = WowmaTagChildList.objects.filter(
                    oya_id=tag_moto,
                ).all()

                child_find_flg = 0
                for child in child_list:
                    # キーワードと、子タグ名称
                    # まず、キーワードとマッチする子タグは優先して登録
                    if child.child_name in tmp_list_keyword:
                        new_list.append(str(child.child_id))
                        child_find_flg = 1
                        list_cnt += 1
                        if child.rel_flg == 0:  # 一つの商品に複数の子タグを登録できない場合はここで終わり
                            break
                        if list_cnt > 63:
                            break
                if child_find_flg == 0:
                    # まだ見つかってなければ、まるごと登録してしまう
                    for child in child_list:
                        # キーワードと、子タグ名称
                        # まず、キーワードとマッチする子タグは優先して登録
                        if child.rel_flg == 0:  # 一つの商品に複数の子タグを登録できない
                            new_list.append(str(child.child_id))  # 一つだけ登録してbreak
                            list_cnt += 1
                            break
                        else:
                            new_list.append(str(child.child_id))  # 紐付いてるだけ登録してゆく
                            list_cnt += 1
                            if list_cnt > 63:
                                break

                # ここでも最大登録数のチェックはしておく
                if list_cnt > 63:
                    break

            # 全部がっちゃんこして半角スペース区切りにして返却
            ret_str = ' '.join(new_list)

            self._logger.info('build_tag_for_wowma:4 設定するタグ:[{}]'.format(ret_str))
            myobj.wow_tagid = ret_str.strip()
            myobj.save()
            return

        except Exception as e:
            self._logger.info(traceback.format_exc())
            self._logger.debug(traceback.format_exc())
            raise

        return

    def build_spec_for_wowma(self, myobj):
        """
        スペックをセットする
        WowmaSpecDetail（親はWowmaGoodsDetail）
        最大５つまで。
        """
        spec_title = [""] * 5
        spec_name = [""] * 5
        spec_value = [""] * 5
        spec_seq = [""] * 5
        ar_cnt = 0

        for i in range(3):
            if myobj.asin.color and myobj.asin.color != '':
                spec_title[ar_cnt] = 'カラー'
                spec_name[ar_cnt] = 'カラー'
                spec_value[ar_cnt] = myobj.asin.color
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
            if myobj.asin.size and myobj.asin.size != '':
                spec_title[ar_cnt] = 'サイズ'
                spec_name[ar_cnt] = 'サイズ'
                spec_value[ar_cnt] = myobj.asin.size
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
            if myobj.asin.flavor and myobj.asin.flavor != '':
                spec_title[ar_cnt] = 'フレーバー'
                spec_name[ar_cnt] = 'フレーバー'
                spec_value[ar_cnt] = myobj.asin.flavor
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
            if myobj.asin.model and myobj.asin.model != '':
                spec_title[ar_cnt] = 'モデル'
                spec_name[ar_cnt] = 'モデル'
                spec_value[ar_cnt] = myobj.asin.model
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
            if myobj.asin.feature and myobj.asin.feature != '':
                spec_title[ar_cnt] = '特徴'
                spec_name[ar_cnt] = '特徴'
                spec_value[ar_cnt] = myobj.asin.feature
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.materialType and myobj.asin.materialType != '':
                spec_title[ar_cnt] = '素材タイプ'
                spec_name[ar_cnt] = '素材タイプ'
                spec_value[ar_cnt] = myobj.asin.materialType
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.mediaType and myobj.asin.mediaType != '':
                spec_title[ar_cnt] = 'メディアタイプ'
                spec_name[ar_cnt] = 'メディアタイプ'
                spec_value[ar_cnt] = myobj.asin.mediaType
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.ringSize and myobj.asin.ringSize != '':
                spec_title[ar_cnt] = 'リングサイズ'
                spec_name[ar_cnt] = 'リングサイズ'
                spec_value[ar_cnt] = myobj.asin.ringSize
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.manufacturer and myobj.asin.manufacturer != '':
                spec_title[ar_cnt] = 'メーカー'
                spec_name[ar_cnt] = 'メーカー'
                spec_value[ar_cnt] = myobj.asin.manufacturer
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.part_number and myobj.asin.part_number != '':
                spec_title[ar_cnt] = '製造番号'
                spec_name[ar_cnt] = '製造番号'
                spec_value[ar_cnt] = myobj.asin.part_number
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.package_quantity\
                    and myobj.asin.package_quantity != '':
                spec_title[ar_cnt] = 'パッケージ数量'
                spec_name[ar_cnt] = 'パッケージ数量'
                spec_value[ar_cnt] = myobj.asin.package_quantity
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.publisher and myobj.asin.publisher != '':
                spec_title[ar_cnt] = '発行者'
                spec_name[ar_cnt] = '発行者'
                spec_value[ar_cnt] = myobj.asin.publisher
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break
            if myobj.asin.brand and myobj.asin.brand != '':
                spec_title[ar_cnt] = 'ブランド'
                spec_name[ar_cnt] = 'ブランド'
                spec_value[ar_cnt] = myobj.asin.brand
                spec_seq[ar_cnt] = str(ar_cnt+1)
                ar_cnt += 1
                if ar_cnt >= 4:
                    break

        obj_detail, detail_created = WowmaSpecDetail.objects.update_or_create(
            wow_goods_detail=myobj,
            spec_title_0=spec_title[0],
            spec_title_1=spec_title[1],
            spec_title_2=spec_title[2],
            spec_title_3=spec_title[3],
            spec_title_4=spec_title[4],
            d_spec_name_0=spec_name[0],
            d_spec_name_1=spec_name[1],
            d_spec_name_2=spec_name[2],
            d_spec_name_3=spec_name[3],
            d_spec_name_4=spec_name[4],
            d_spec_0=spec_value[0],
            d_spec_1=spec_value[1],
            d_spec_2=spec_value[2],
            d_spec_3=spec_value[3],
            d_spec_4=spec_value[4],
            d_spec_seq_0=spec_seq[0],
            d_spec_seq_1=spec_seq[1],
            d_spec_seq_2=spec_seq[2],
            d_spec_seq_3=spec_seq[3],
            d_spec_seq_4=spec_seq[4],
        )
        if obj_detail:
            obj_detail.save()

        return

    def build_wowma_goods_detail(self, myobj):
        """
        Todo: まだ未完 2023/07/01
        Amazon対応版
        wowma用の商品詳細情報を組み立てる
        商品詳細から不要文字の除去など
        配送料の設定もここでやるか

        _get_wowma_buyers_detail
        を参考に
        """
        try:
            # 商品コードのセット
            self.set_wowma_gid(myobj)

            # 商品名の組み立てと不要文字削除・変換
            self.build_gname_for_wowma(myobj)

            # 商品詳細の組み立てと不要文字削除・変換
            self.build_gdetail_for_wowma(myobj)

            # カテゴリのセット
            self.set_wowma_ctid(myobj)

            # タグのセット
            self.build_tag_for_wowma(myobj)

            # スペックのセット
            self.build_spec_for_wowma(myobj)

            # ショップ情報のセット
            # なんかmanytomanyがうまくいかない・・ので削除
            # self.set_shop_info(myobj)

            # 配送情報のセット
            self.set_delivery_info(myobj)

            # 在庫数のセット
            self.set_stock(myobj)

            # wowmaでの販売価格決定
            self.set_selling_price(myobj)

        except:
            raise

        return myobj

    def set_shop_info(self, myobj):
        # Todo: ショップ情報の紐づけ、かならず1つはショップが存在すること まだ登録が正確にできてない
        # buyersの配送を消して業者のにしないと
        """
            追加の順
            (ここはショップ管理画面から）
            new_wowma_shop = WowmaShopInfo(name = django)
            new_wowma_shop.save()

            商品にショップを追加するには
            wowma_shop = WowmaShopInfo.objects.get(id = 1)
            wowma_goods_obj = WowmaGoodsDetail.objects.get(id = 1)
            WowmaGoodsDetail.wowma_shops.add(wowma_shop)

        """
        # なぜかmanytomanyでテーブルができない・・・
        # for wowma_shop in WowmaShopInfo.objects.all():
        #     myobj.wowma_shops.add(wowma_shop)
        return

    def set_delivery_info(self, myobj):
        """
            商品ごとに配送区分（サイズ）を取得

            QooAsinDetail に以下はセットされてる
            obj.shipping_size = self._shipping_size  # 発送時の送料区分

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

            こいつをもとに、wowmaでセットされてる配送区分と一致させよう
            以下に登録。
            wowma管理画面でいうところの配送方法ID
            配送会社は「ヤマト運輸」「佐川急便」
            WowmaGoodsDetail.wow_delivery_method_id

            # 1: ネコポス   100003
            # 2: 60サイズ   100060
            # 3: 80サイズ   100080
            # 4: 100サイズ  100100
            # 5: 120サイズ  100120
            # 6: 140サイズ  100140
            # 7: 160サイズ  100160
            # 8: 180サイズ（ロジスピは取り扱いない）これ以上はサイズNG

            wowmaなら、wowmaの送料テーブルと突き合わせて送料を算出
            配送業者もその段階で得る
            沖縄とかも考慮する
            wowmaなら、deliveryMethod　に配送方法を五種セットできるが・・
            まあ選択肢は一択となるだろう。
            配送方法ID　を紐づけましょう
            ※wowmaでも、出店する店舗情報WowmaShopInfoを複数もたせますか。
            配送情報は
                wowma_shops = models.ManyToManyField(WowmaShopInfo, related_name='wowma_shops', blank=True)
        """

        try:
            if myobj.asin.shipping_size == 1:
                # ネコポス
                myobj.wow_delivery_method_id = '100003'
            elif myobj.asin.shipping_size == 2:
                # 60サイズ   100060
                myobj.wow_delivery_method_id = '100060'
            elif myobj.asin.shipping_size == 3:
                # 80サイズ   100080
                myobj.wow_delivery_method_id = '100080'
            elif myobj.asin.shipping_size == 4:
                # 100サイズ   100100
                myobj.wow_delivery_method_id = '100100'
            elif myobj.asin.shipping_size == 5:
                # 120サイズ   100120
                myobj.wow_delivery_method_id = '100120'
            elif myobj.asin.shipping_size == 6:
                # 140サイズ   100140
                myobj.wow_delivery_method_id = '100140'
            elif myobj.asin.shipping_size == 7:
                # 160サイズ   100160
                myobj.wow_delivery_method_id = '100160'
            else:
                # サイズNG
                myobj.wow_delivery_method_id = 'size_ng'

            # 送料設定区分は 1 （送料別）にしておく
            myobj.wow_postage_segment = 1

        except Exception as e:
            self._logger.debug(traceback.format_exc())
            return False

        # myobj にセットするのみ。
        myobj.save()
        return

    def set_selling_price(self, myobj):
        """
            # 販売価格のセット

            考え方は
                ama
                1000円　だと

                wow
                1000円　からスタート
                *
                手数料 1.1 + 消費税上乗せ 1.05
                *
                利益 1.2
                （この時点で1380円）
                +
                送料(別)
                =
                2000円くらい。
        """
        try:
            selling_price = 0  # 販売価格計算結果
            # amaの基準価格はカート価格＋カート送料としておく
            ama_price = myobj.asin.buybox_listing_price\
                + myobj.asin.buybox_shipping_price

            # wowmaの販売手数料 10% と消費税上乗せ分 5%をまず上乗せ
            ama_price = ama_price * 1.15

            # ここから利益を考える。基本的に10～20% くらいを載せたいのだが
            # 価格帯によって変えてみよう。
            benefit_price = 500
            if ama_price < 500:
                benefit_price = 200
            elif 500 <= ama_price < 1000:
                benefit_price = 300
            elif 1000 <= ama_price < 2000:
                benefit_price = 400
            elif 2000 <= ama_price < 3000:
                benefit_price = 500
            elif 3000 <= ama_price < 4000:
                benefit_price = 600
            elif 4000 <= ama_price < 5000:
                benefit_price = 700
            elif 5000 <= ama_price < 7000:
                benefit_price = 800
            elif 7000 <= ama_price < 9000:
                benefit_price = 900
            elif 9000 <= ama_price < 12000:
                benefit_price = 1000
            elif 12000 <= ama_price < 15000:
                benefit_price = 1200
            elif 15000 <= ama_price < 18000:
                benefit_price = 1500
            elif 18000 <= ama_price < 21000:
                benefit_price = 1800
            elif 21000 <= ama_price < 24000:
                benefit_price = 2100
            elif 24000 <= ama_price < 27000:
                benefit_price = 2400
            elif 27000 <= ama_price < 30000:
                benefit_price = 2700
            elif 30000 <= ama_price < 33000:
                benefit_price = 3000
            elif 33000 <= ama_price < 36000:
                benefit_price = 3300
            elif 36000 <= ama_price < 40000:
                benefit_price = 3600
            elif 40000 <= ama_price < 45000:
                benefit_price = 3800
            elif 45000 <= ama_price < 50000:
                benefit_price = 4000
            else:
                benefit_price = 2000

            # 端数調整
            selling_price = int(round((ama_price + benefit_price), -2)) + 80
            myobj.wow_price = selling_price

        except Exception as e:
            self._logger.debug(traceback.format_exc())
            return False

        # myobj にセットするのみ。
        myobj.save()
        return

    def set_wow_goods_img(self, myobj):

        # 既存DBのフラグによってどうステータスを更新するか
        # wowma新規登録用の画像情報を作らないといけない。

        # asin.small_image_url  # サムネイルにするか
        # asin.img_tag_0-19  # スクレイピングした結果を
        images = [{'imageUrl': myobj.asin.img_tag_0, 'imageName': 'image_1', 'imageSeq': 1},
                  {'imageUrl': myobj.asin.img_tag_1, 'imageName': 'image_2', 'imageSeq': 2},
                  {'imageUrl': myobj.asin.img_tag_2, 'imageName': 'image_3', 'imageSeq': 3},
                  {'imageUrl': myobj.asin.img_tag_3, 'imageName': 'image_4', 'imageSeq': 4},
                  {'imageUrl': myobj.asin.img_tag_4, 'imageName': 'image_5', 'imageSeq': 5},
                  {'imageUrl': myobj.asin.img_tag_5, 'imageName': 'image_6', 'imageSeq': 6},
                  {'imageUrl': myobj.asin.img_tag_6, 'imageName': 'image_7', 'imageSeq': 7},
                  {'imageUrl': myobj.asin.img_tag_7, 'imageName': 'image_8', 'imageSeq': 8},
                  {'imageUrl': myobj.asin.img_tag_8, 'imageName': 'image_9', 'imageSeq': 9},
                  {'imageUrl': myobj.asin.img_tag_9, 'imageName': 'image_10', 'imageSeq': 10},
                  {'imageUrl': myobj.asin.img_tag_10, 'imageName': 'image_11', 'imageSeq': 11},
                  {'imageUrl': myobj.asin.img_tag_11, 'imageName': 'image_12', 'imageSeq': 12},
                  {'imageUrl': myobj.asin.img_tag_12, 'imageName': 'image_13', 'imageSeq': 13},
                  {'imageUrl': myobj.asin.img_tag_13, 'imageName': 'image_14', 'imageSeq': 14},
                  {'imageUrl': myobj.asin.img_tag_14, 'imageName': 'image_15', 'imageSeq': 15},
                  {'imageUrl': myobj.asin.img_tag_15, 'imageName': 'image_16', 'imageSeq': 16},
                  {'imageUrl': myobj.asin.img_tag_16, 'imageName': 'image_17', 'imageSeq': 17},
                  {'imageUrl': myobj.asin.img_tag_17, 'imageName': 'image_18', 'imageSeq': 18},
                  {'imageUrl': myobj.asin.img_tag_18, 'imageName': 'image_19', 'imageSeq': 19},
                  {'imageUrl': myobj.asin.img_tag_19, 'imageName': 'image_20', 'imageSeq': 20}]

        return images

    def chk_is_blacklist(self, myobj):
        """ ブラックリストの登録状況を確認
            return: True / ブラックリスト対象
                    False / ブラックリスト対象ではない
        """
        # 以下のどれか一つでも引っかかったらNG
        if myobj.asin.is_adlt is True\
                or myobj.asin.is_seller_ok is False\
                or myobj.asin.is_blacklist_ok is False\
                or myobj.asin.is_blacklist_ok_asin is False\
                or myobj.asin.is_blacklist_ok_img is False\
                or myobj.asin.is_blacklist_ok_keyword is False:
            return True
        return False

    def call_wow_register_item_info(self, myobj, flg, images):
        return self._wowma_access.wowma_register_item_info(
                            myobj.wow_gname,
                            myobj.gid,
                            myobj.gcode,
                            myobj.wow_price,
                            myobj.wow_fixed_price,
                            myobj.wow_postage_segment,
                            myobj.wow_postage,
                            myobj.wow_delivery_method_id,
                            myobj.wow_gdetail,
                            myobj.wow_ctid,
                            myobj.wow_keyword,
                            myobj.wow_tagid,
                            flg,  # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                            int(myobj.stock),  # 在庫数
                            images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                        )

    def call_wow_update_item_info(self, myobj, flg, images):
        # wowmaのupdate_item_infoを呼ぶ
        return self._wowma_access.wowma_update_item_info(
                            myobj.wow_gname,
                            myobj.gid,
                            myobj.gcode,
                            myobj.wow_price,
                            myobj.wow_fixed_price,
                            myobj.wow_postage_segment,
                            myobj.wow_postage,
                            myobj.wow_delivery_method_id,
                            myobj.wow_gdetail,
                            myobj.wow_ctid,
                            myobj.wow_keyword,
                            myobj.wow_tagid,
                            flg,  # 1は販売中。2は販売終了。出品OKだが在庫切れなので登録済みだが未掲載 ( 2 ) にしておく
                            int(myobj.stock),  # 在庫数
                            images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                        )

    def call_wow_goods_register(self, myobj, images):
        """
        wowma新規登録ロジック
        """
        self._logger.debug('--> call_wow_goods_register 処理開始')

        # まず出品可否を判断する。
        # ブラックリストに乗ってるものは登録自体しない。
        if self.chk_is_blacklist(myobj):
            self._logger.debug('--> call_wow_goods_register ブラックリスト対象なので登録しない asin:[{}]'.format(myobj.asin.asin))
            myobj.wow_on_flg = 2  # 出品NG
            myobj.wow_ng_flg = True  # こちらも出品NG
            return

        if myobj.wow_upd_status == 0:  # 未登録なら新規登録する
            self._logger.info('--> call_wow_goods_register 登録開始')
            # 未掲載 wow_upd_status = 0
            # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
            ret_obj_list = self.call_wow_register_item_info(
                myobj, 1, images)

            myrtn = 0
            mycode = ''
            chk_flg = 0

            if ret_obj_list is None or len(ret_obj_list) == 0:
                self._logger.debug(
                    " call_wow_goods_register wowma call_wow_register_item_info failed..")
                chk_flg = 1
            for ret_obj in ret_obj_list:
                self._logger.debug(
                    " call_wow_goods_register wowma ret_obj [{}]".format(ret_obj))

                """
                Todo:エラーコードは以下パターンも考慮すること
                    <error>
                    <code>PME0203</code>
                    <message>販売価格は1～4000000000を入力してください。</message>
                    </error>
                    <error>
                    <code>PME0208</code>
                    <message>店舗ID[17738]配送方法ID[0]をキーに利用配送方法情報は取得できません。</message>
                    </error>
                    <error>
                    <code>PME0095</code>
                    <message>不正なカテゴリIDが入力されています。</message>
                    </error>
                """

                # PME0106:入力された商品コードは、既に登録されています。
                if ret_obj['res_rtn'] == '1' and ret_obj['res_code'] == 'PME0106':
                    # 出品していいはずなので、更新をかけ直す
                    try:
                        # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                        ret_obj_list =\
                            self.call_wow_update_item_info(myobj, 1, images)
                        for ret_obj in ret_obj_list:
                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                # lotnumberを更新しておく
                                myobj.wow_lotnum = int(ret_obj['res_code'])
                                self._logger.info(
                                    '--> call_wow_goods_register 更新OK！ 1_1_0 在庫[{}] lotnum[{}]'.format(myobj.stock, myobj.wow_lotnum))

                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                        # 出品失敗なら 1 が返される。この場合は未出品のまま
                        self._logger.info(
                            '--> call_wow_goods_register 更新OK！ 1_1 在庫[{}]'.format(myobj.stock))
                        myobj.wow_on_flg = 1  # OKのまま
                        myobj.wow_upd_status = 1  # 掲載中に

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'call_wow_goods_register point 1_1',
                            'asin': myobj.asin.asin,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        continue  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

                elif ret_obj['res_rtn'] != "0":
                    self._logger.debug(
                        " call_wow_goods_register wowma 商品検索でエラー [{}][{}]".format(ret_obj['res_code'],
                                                                                    ret_obj['res_msg']))
                    chk_flg = 1  # なにかエラーになってた

                elif ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                    self._logger.debug(
                        "call_wow_goods_register 商品登録できた lotnum:[{}] msg:[{}]".format(ret_obj['res_code'],
                                                                                ret_obj['res_msg']))
                    # lotnumberを更新しておく
                    myobj.wow_lotnum = int(ret_obj['res_code'])

            if chk_flg == 0:
                # 0が返ってきて 出品OKだったら、フラグを出品済みに
                # 出品失敗なら 1 が返される。この場合は未出品のまま
                self._logger.debug('--> call_wow_goods_register 登録OK！ 1')
                myobj.wow_on_flg = 1  # OK
                myobj.wow_upd_status = 1  # 掲載中に更新
            else:
                # 更新時にエラー？
                my_err_list = {
                    'batch_name': 'call_wow_goods_register point 2_1',
                    'asin': myobj.asin.asin,
                    'status': myrtn,
                    'code': mycode,
                    'message': traceback.format_exc(),
                }
                # エラー記録だけ残して処理は続行しておく
                error_goods_log.exe_error_log(my_err_list)

            myobj.save()
            self._logger.info('--> call_wow_goods_register 登録終了')

        else:
            self._logger.info('--> call_wow_goods_register 登録せず終了 upd_status[{}] '.format(myobj.wow_upd_status))
        self._logger.debug('--> call_wow_goods_register 処理終了')
        return

    def call_wow_goods_upd(self, myobj, images):
        """
        wowma 商品情報更新
        Todo: まだ未完
        """
        self._logger.debug('--> call_wow_goods_upd 処理開始')

        # まず出品可否を判断する。
        # ブラックリストに乗ってるものは登録しないが、もし登録済みだったらNGとして降ろさないといけない。
        if self.chk_is_blacklist(myobj):
            self._logger.debug('--> call_wow_goods_upd ブラックリスト対象 もし登録済みなら降ろす asin:[{}]'.format(myobj.asin.asin))
            myobj.wow_on_flg = 2  # 出品NG
            myobj.wow_ng_flg = True  # こちらも出品NG

        # wowma 更新 ###################################################################################################
        # wowmaについて画面から出品OKになっている。以下で掲載状況を確認して更新してゆく もしくは　wow_on_flg == 3（在庫切れ）
        myrtn = 0
        mycode = ''
        asin = myobj.asin.asin

        # 以下は、myobj.wow_lotnum　がセットされている状態から流れてくる。
        # wow_on_flg = ((0, '確認待ち'), (1, 'OK'), (2, 'NG'), (3, '在庫切れ'))
        if myobj.wow_on_flg == 1 or myobj.wow_on_flg == 3:

            # 出品OKなのに在庫０なら、そのまま未掲載にしておく
            if int(myobj.stock) == 0:
                if myobj.wow_upd_status == 0 or myobj.wow_upd_status == 2:  # wowma未掲載
                    # 未掲載 wow_upd_status = 0（未登録）もしくは2（登録済みだが未掲載）
                    # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                    self._logger.info('--> call_wow_goods_upd 出品OKなのに在庫０　未掲載のまま asin:[{}]'.format(asin))
                    myobj.wow_on_flg = 3
                else:
                    # 掲載中 wow_upd_status = 1
                    # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない、かつ登録済みだが未掲載に切り替える
                    try:
                        self._wowma_access.wowma_update_stock(myobj.gid, 0, '2')
                        myobj.wow_on_flg = 3  # 更新成功したら 在庫切れにする。出品OK状態はそのまま、wow掲載状況は掲載中止になってる
                        myobj.wow_upd_status = 2  # 未掲載に
                        self._logger.info('--> call_wow_goods_upd 在庫切れにした。gid:[{}]'.format(gid))
                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'call_wow_goods_upd error 1_1',
                            'asin': asin,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        self._logger.debug(
                            '--> call_wow_goods_upd 在庫数更新時にエラー？ asin:[{}] 在庫は0'.format(asin))
                        return  # DB更新せずに戻す
                        # raise Exception("在庫を0更新時に失敗？ asin:[{0}] stock:[{1}]".format(my_value.asin, my_value.stock))

                if myobj.wow_upd_status != 0:
                    # 登録済みだったら、在庫状況によらず商品内容をupdateする
                    try:
                        # 1は販売中。2は販売終了。出品OKだが在庫切れなので登録済みだが未掲載 ( 2 ) にしておく
                        ret_obj_list =\
                            self.call_wow_update_item_info(myobj, 2, images)
                        for ret_obj in ret_obj_list:
                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                # lotnumberを更新しておく
                                myobj.wow_lotnum = int(ret_obj['res_code'])

                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                        # 在庫0更新
                        self._logger.info('--> call_wow_goods_upd 更新OK！ 在庫は0 未掲載に更新した')
                        myobj.wow_on_flg = 3  # OKのまま
                        myobj.wow_upd_status = 2  # 登録済みだが未掲載に

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'call_wow_goods_upd point 1_2',
                            'asin': asin,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

            # 在庫がある
            elif int(myobj.stock) > 0:
                # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                if myobj.wow_upd_status == 0:  # 未登録なら新規登録する
                    self._logger.info('--> call_wow_goods_upd 未登録だが出品OKで在庫あるので登録開始')
                    # 未掲載 wow_upd_status = 0
                    # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                    ret_obj_list = self.call_wow_register_item_info(
                        myobj, 1, images)

                    myrtn = 0
                    mycode = ''
                    chk_flg = 0
                    for ret_obj in ret_obj_list:
                        # PME0106:入力された商品コードは、既に登録されています。
                        if ret_obj['res_rtn'] == '1' and ret_obj['res_code'] == 'PME0106':
                            self._logger.info(
                                '--> call_wow_goods_upd 在庫[{}] しかし商品コード既に存在(PME0106) 更新し直す'.format(myobj.stock))
                            # 出品していいはずなので、更新をかけ直す
                            try:
                                # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                                ret_obj_list =\
                                    self.call_wow_update_item_info(
                                        myobj, 1, images)
                                for ret_obj in ret_obj_list:
                                    if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                        # lotnumberを更新しておく
                                        myobj.wow_lotnum = ret_obj['res_code']

                                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                                        # 出品失敗なら 1 が返される。この場合は未出品のまま
                                        self._logger.info(
                                            '--> call_wow_goods_upd 更新OK！ 2_1 在庫[{}]'.format(myobj.stock))
                                        myobj.wow_on_flg = 1  # OKのまま
                                        myobj.wow_upd_status = 1  # 掲載中に
                                    else:
                                        # なにかエラー
                                        # wow_on_flg はそのまま1か。何かおかしければ別の値に
                                        # wow_upd_statusは0のまま
                                        self._logger.info(
                                            '--> call_wow_goods_upd 更新NG? 2_2 res_rtn[{}]'.format(ret_obj['res_rtn']))
                                        myobj.wow_upd_status = 0
                                        chk_flg = 1  # エラー扱いに

                            except:
                                # 更新時にエラー？
                                my_err_list = {
                                    'batch_name': 'call_wow_goods_upd error point 1_3',
                                    'asin': asin,
                                    'status': myrtn,
                                    'code': mycode,
                                    'message': traceback.format_exc(),
                                }
                                error_goods_log.exe_error_log(my_err_list)
                                continue  # DB更新せずに戻す
                                # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

                        elif ret_obj['res_rtn'] != "0":
                            self._logger.debug(
                                "call_wow_goods_upd wowma 商品検索でエラー [{}][{}]".format(ret_obj['res_code'],
                                                                                         ret_obj['res_msg']))
                            myrtn = int(ret_obj['res_rtn'])
                            mycode = ret_obj['res_code']
                            chk_flg = 1  # なにかエラーになってた

                        elif ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                            self._logger.debug(
                                "call_wow_goods_upd 商品登録できた [{}][{}]".format(ret_obj['res_code'],
                                                                                        ret_obj['res_msg']))
                            # lotnumberを更新しておく
                            myobj.wow_lotnum = ret_obj['res_code']

                        else:
                            # ret_obj res_rtnが予期してない値？
                            self._logger.debug(
                                "call_wow_goods_upd 商品登録中にエラー？ [{}][{}][{}]".format(
                                    ret_obj['res_rtn'], ret_obj['res_code'], ret_obj['res_msg']))
                            myrtn = int(ret_obj['res_rtn'])
                            mycode = ret_obj['res_code']
                            chk_flg = 1  # なにかエラーになってた

                    if chk_flg == 0:
                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                        # 出品失敗なら 1 が返される。この場合は未出品のまま
                        self._logger.debug('--> call_wow_goods_upd 登録OK！ 3_1 在庫[{}]'.format(myobj.stock))
                        myobj.wow_on_flg = 1  # OK
                        myobj.wow_upd_status = 1  # 掲載中に更新
                    else:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'call_wow_goods_upd error point 1_4',
                            'asin': asin,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        # エラー記録だけ残して処理は続行しておく
                        error_goods_log.exe_error_log(my_err_list)

                else:
                    # 在庫あり、かつ
                    # 掲載中 wow_upd_status = 1　か、登録済みだが未掲載 2 （これまで在庫０だった）
                    # 現在の在庫数で更新する、未掲載だったら復活させる
                    self._logger.info('--> call_wow_goods_upd 掲載中。現時点の在庫数で更新 asin[{}] stock[{}]'.format(
                        asin,
                        myobj.stock)
                    )
                    try:
                        # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                        ret_obj_list =\
                            self.call_wow_update_item_info(
                                myobj, 1, images)
                        upd_flg = False
                        for ret_obj in ret_obj_list:
                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                # lotnumberを更新しておく
                                upd_flg = True
                                myobj.wow_lotnum = ret_obj['res_code']
                                myobj.wow_on_flg = 1  # OKのまま
                                myobj.wow_upd_status = 1  # 掲載中に

                        # 0が返ってきて 出品OKだったら、フラグを出品済みに
                        # 出品失敗なら 1 が返される。この場合は未出品のまま
                        if upd_flg is True:
                            self._logger.info(
                                '--> call_wow_goods_upd 更新OK！ lotnum[{}] 在庫[{}]'.format(myobj.wow_lotnum, myobj.stock))
                        else:
                            self._logger.info(
                                '--> call_wow_goods_upd 更新NG.. 在庫[{}]'.format(myobj.stock))
                            myobj.wow_upd_status = 0  # 未掲載に

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'call_wow_goods_upd point 2_1',
                            'asin': asin,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

            else:  # 在庫数の取得エラー？
                raise Exception("在庫数の取得に失敗？stock:[{}] gid:[{}]".format(myobj.stock, myobj.gid))

        else:
            # ここにきたら、wow_on_flg は 0（確認中）か2（NG）のはず。そのままにしておく
            if myobj.wow_on_flg == 2:
                self._logger.info('--> call_wow_goods_upd 未出品に更新しないと flg=2 （NG）')
                if myobj.wow_upd_status != 0:  # 登録済みのものは未掲載に倒さないと
                    try:
                        # 1は販売中。2は販売終了。出品NGなので販売終了 ( 2 ) にしておく
                        ret_obj_list =\
                            self.call_wow_update_item_info(
                                myobj, 2, images)
                        upd_flg = False
                        for ret_obj in ret_obj_list:
                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                # lotnumberを更新しておく
                                upd_flg = True
                                myobj.wow_lotnum = ret_obj['res_code']
                                # 0が返ってきて 出品OKだったら、フラグを出品済みに
                                # 出品失敗なら 1 が返される。この場合は未出品のまま
                                myobj.wow_on_flg = 1  # OKのまま
                                myobj.wow_upd_status = 1  # 掲載中に
                        if upd_flg is True:
                            self._logger.info(
                                '--> call_wow_goods_upd 更新OK！ 3 lotnum[{}] 在庫[{}]'.format(myobj.wow_lotnum, myobj.stock))
                        else:
                            self._logger.info(
                                '--> call_wow_goods_upd 更新ng.. 3 在庫[{}]'.format(myobj.stock))

                    except:
                        # 更新時にエラー？
                        my_err_list = {
                            'batch_name': 'call_wow_goods_upd error point 3_1',
                            'asin': myobj.asin.asin,
                            'status': myrtn,
                            'code': mycode,
                            'message': traceback.format_exc(),
                        }
                        error_goods_log.exe_error_log(my_err_list)
                        return  # DB更新せずに戻す
                        # raise Exception("出品OKで在庫あるので登録中に失敗？ gid:[{0}] stock:[{1}]".format(myobj.gid, myobj.stock))

            else:
                self._logger.info('--> call_wow_goods_upd 在庫あるがNGフラグたってて未出品なので処理せず flg=0 ')

        self._logger.debug('--> call_wow_goods_upd 処理終了')
        return

    def exec_wow_goods_detail_upd(self, myobj):
        """
            wowmaのAPI経由で商品情報をwowmaにアップデートかける
            Todo: まだ未完 wowmaの更新

            まずはこのあたりを参考
            def _upd_wowma_qoo_item_info_normal(self, gid):

            1.wow登録済みかどうかの判断
                wow_lotnum があればwowmaに問い合わせる。存在するか？
            2.未登録なら新規登録
            3.登録済みなら最新にアップデート

            ※ここでは在庫更新だけの処理とは分ける。あくまで商品情報全部更新するかどうか。
              2023/5/6 やっぱり在庫更新（ama_stock_chk.py）からもこっちを呼ぼうか

        """

        # 商品画像を取り込む
        images = self.set_wow_goods_img(myobj)

        """
        ・ブラックリストのチェックは新規登録or更新側　それぞれで判断すること
        """
        if myobj.wow_lotnum == 0:
            # wowma登録無しなので新規登録
            # 商品登録しない場合はFalseリタンしてログに書くだけ
            self.call_wow_goods_register(myobj, images)

        else:
            # wowma登録済みなのでwowmaに存在するか問い合わせ（wowmaで消えてるかもしれないので）
            self.call_wow_goods_upd(myobj, images)

        return

    def exec_wowma_goods_update(self, myobj, taglist_upd_flg, wow_upd_flg):
        """ wowmaの商品を更新する
            こっちはAma商品対応版
        params: myobj WowmaGoodsDetail 商品情報
                taglist_upd_flg: 0 タグは最新化せず、dbに登録されてるままを
                                 1 タグは指定のカテゴリにマッチしたリストで最新化する
                wow_upd_flg: 0 wowmaは更新かけない
                             1 wowmaも更新する
        return: true, msg 正常終了
                false, error_msg 異常終了
        """
        try:
            self._logger.debug('--> exec_wowma_goods_update 処理開始 tag_flg:[{}] wow_upd_flg[{}]'.format(taglist_upd_flg, wow_upd_flg))

            # 商品情報の組み立て
            myobj = self.build_wowma_goods_detail(myobj)

            # wowのカテゴリがちゃんとセットされている場合のみwowma側は更新する
            wow_cat_ok_flg = False
            if myobj.wow_ctid > 0:
                wow_cat_ok_flg = True

            # wowmaも更新
            if wow_upd_flg == '1':
                if wow_cat_ok_flg is True:
                    self._logger.debug('--> exec_wowma_goods_update wow_ctidが設定済み wowmaを更新開始 ama_ctid:[{}]'.format(myobj.ama_ctid))
                    self.exec_wow_goods_detail_upd(myobj)
                else:
                    # カテゴリIDが未割り当てのものはwowmaに更新をかけない。
                    self._logger.debug('--> exec_wowma_goods_update wow_ctidが未設定のためwowmaは更新せず 問題のama_ctid:[{}]'.format(myobj.ama_ctid))
            else:
                self._logger.debug('--> exec_wowma_goods_update wow_upd_flgが1以外のためwowmaは更新せず 問題のama_ctid:[{}]'.format(wow_upd_flg))

            # DBを更新
            myobj.save()
            self._logger.debug('--> exec_wowma_goods_update 処理終了')

        except:
            return False, traceback.format_exc()  # DB更新せずに戻す

        return True, "wowma 商品情報更新 正常終了"

    def exec_wowma_goods_update_bk(self, myobj, taglist_upd_flg):
        """ wowmaの商品を更新する
            これは古いやつ・・・ buyers対応版
        params: myobj YaBuyersItemDetail 商品情報
                taglist_upd_flg: 0 タグは最新化せず、dbに登録されてるままを
                                 1 タグは指定のカテゴリにマッチしたリストで最新化する
        return: true, msg 正常終了
                false, error_msg 異常終了
        """
        try:
            self._logger.debug('--> exec_wowma_goods_update_bk 処理開始 tag_flg:[{}]'.format(taglist_upd_flg))
            # 既存DBのフラグによってどうステータスを更新するか
            # 出品はまだNG。（画面から編集してない）が、DBの在庫などは更新していい
            if myobj.wow_on_flg == 0:
                self._logger.debug('--> exec_wowma_goods_update_bk 出品まだNG そのまま')
                return True, "wow_on_flg[0] のためwowmaの更新はしません"

            # 画面から出品OKになっている。以下で掲載状況を確認して更新してゆく
            elif myobj.wow_on_flg == 1:

                if taglist_upd_flg == '1':
                    # wowmaのtagidは、このタイミングで最新化しておく
                    # wowma は検索タグIDを設定。
                    myobj.wow_tagid = self._buinfo_obj.get_wow_tagid_list(
                        myobj.bu_ctid, myobj.wow_gname, myobj.wow_ctid)
                    myobj.save()

                # 画像情報を作らないといけない。
                images = [{'imageUrl': myobj.g_img_src_1, 'imageName': 'image_1', 'imageSeq': 1},
                          {'imageUrl': myobj.g_img_src_2, 'imageName': 'image_2', 'imageSeq': 2},
                          {'imageUrl': myobj.g_img_src_3, 'imageName': 'image_3', 'imageSeq': 3},
                          {'imageUrl': myobj.g_img_src_4, 'imageName': 'image_4', 'imageSeq': 4},
                          {'imageUrl': myobj.g_img_src_5, 'imageName': 'image_5', 'imageSeq': 5},
                          {'imageUrl': myobj.g_img_src_6, 'imageName': 'image_6', 'imageSeq': 6},
                          {'imageUrl': myobj.g_img_src_7, 'imageName': 'image_7', 'imageSeq': 7},
                          {'imageUrl': myobj.g_img_src_8, 'imageName': 'image_8', 'imageSeq': 8},
                          {'imageUrl': myobj.g_img_src_9, 'imageName': 'image_9', 'imageSeq': 9},
                          {'imageUrl': myobj.g_img_src_10, 'imageName': 'image_10', 'imageSeq': 10},
                          {'imageUrl': myobj.g_img_src_11, 'imageName': 'image_11', 'imageSeq': 11},
                          {'imageUrl': myobj.g_img_src_12, 'imageName': 'image_12', 'imageSeq': 12},
                          {'imageUrl': myobj.g_img_src_13, 'imageName': 'image_13', 'imageSeq': 13},
                          {'imageUrl': myobj.g_img_src_14, 'imageName': 'image_14', 'imageSeq': 14},
                          {'imageUrl': myobj.g_img_src_15, 'imageName': 'image_15', 'imageSeq': 15},
                          {'imageUrl': myobj.g_img_src_16, 'imageName': 'image_16', 'imageSeq': 16},
                          {'imageUrl': myobj.g_img_src_17, 'imageName': 'image_17', 'imageSeq': 17},
                          {'imageUrl': myobj.g_img_src_18, 'imageName': 'image_18', 'imageSeq': 18},
                          {'imageUrl': myobj.g_img_src_19, 'imageName': 'image_19', 'imageSeq': 19},
                          {'imageUrl': myobj.g_img_src_20, 'imageName': 'image_20', 'imageSeq': 20}]

                # 出品OKなのに在庫０なら、そのまま未掲載にしておく
                if int(myobj.stock) == 0:
                    if myobj.wow_upd_status == 0:
                        # 未掲載 wow_upd_status = 0
                        # 出品OKなのに在庫０、かつ未掲載なら、そのまま未掲載にしておく
                        self._logger.debug('--> exec_wowma_goods_update_bk 出品OKなのに在庫０　未掲載のまま')
                        myobj.wow_on_flg = 1
                    else:
                        # 掲載中 wow_upd_status = 1
                        # ★★出品OKなのに在庫０、掲載済みなら、在庫を0で更新しないといけない
                        try:
                            ret_obj_list = self._wowma_access.wowma_update_item_info(
                                    myobj.wow_gname,
                                    myobj.gid,
                                    myobj.gcode,
                                    myobj.wow_price,
                                    myobj.wow_fixed_price,
                                    myobj.wow_postage_segment,
                                    myobj.wow_postage,
                                    myobj.wow_delivery_method_id,
                                    myobj.wow_gdetail,
                                    myobj.wow_ctid,
                                    myobj.wow_keyword,
                                    myobj.wow_tagid,
                                    myobj.wow_upd_status,  # 1は販売中。2は販売終了。
                                    int(myobj.stock),  # ★要確認、DBの在庫数をそのまま更新すること。在庫数
                                    images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                            )
                            for ret_obj in ret_obj_list:
                                if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                    # lotnumberを更新しておく
                                    myobj.wow_lotnum = ret_obj['res_code']
                                    self._logger.debug(
                                        '--> exec_wowma_goods_update_bk wowma側更新OK。lotnum[{}]'.format(
                                            myobj.wow_lotnum))
                        except:
                            # 更新時にエラー？
                            my_err_list = {
                                'batch_name': 'exec_wowma_goods_update_bk wowma_update_stock point 0_1',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': myobj.gcode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            raise Exception("wowma更新時に失敗？{}".format(myobj.gcode))

                # 　在庫がある
                elif int(myobj.stock) > 0:
                    # ☆☆　出品もしくは在庫更新しないといけない ☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆☆
                    if myobj.wow_upd_status == 0:
                        self._logger.debug('--> exec_wowma_goods_update_bk 未登録だが出品OKで在庫あるので登録開始')
                        # 未掲載 wow_upd_status = 0
                        try:
                            ret_obj_list = self._wowma_access.wowma_register_item_info(
                                                               myobj.wow_gname,
                                                               myobj.gid,
                                                               myobj.gcode,
                                                               myobj.wow_price,
                                                               myobj.wow_fixed_price,
                                                               myobj.wow_postage_segment,
                                                               myobj.wow_postage,
                                                               myobj.wow_delivery_method_id,
                                                               myobj.wow_gdetail,
                                                               myobj.wow_ctid,
                                                               myobj.wow_keyword,
                                                               myobj.wow_tagid,
                                                               1,  # 出品OKなので1は販売中。
                                                               int(myobj.stock),  # 在庫数
                                                               images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                                               )

                            chk_flg = 0
                            for ret_obj in ret_obj_list:
                                # PME0106:入力された商品コードは、既に登録されています。
                                if ret_obj['res_rtn'] == '1' and ret_obj['res_code'] == 'PME0106':
                                    # 出品していいはずなので、更新をかけ直す
                                    try:
                                        ret_obj_list = self._wowma_access.wowma_update_item_info(
                                            myobj.wow_gname,
                                            myobj.gid,
                                            myobj.gcode,
                                            myobj.wow_price,
                                            myobj.wow_fixed_price,
                                            myobj.wow_postage_segment,
                                            myobj.wow_postage,
                                            myobj.wow_delivery_method_id,
                                            myobj.wow_gdetail,
                                            myobj.wow_ctid,
                                            myobj.wow_keyword,
                                            myobj.wow_tagid,
                                            1,  # 1は販売中。2は販売終了。出品OKなので販売中 ( 1 ) にしておく
                                            int(myobj.stock),  # 在庫数
                                            images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                                        )
                                        for ret_obj in ret_obj_list:
                                            if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                                # lotnumberを更新しておく
                                                myobj.wow_lotnum = ret_obj['res_code']
                                                self._logger.debug(
                                                    '--> exec_wowma_goods_update_bk wowma側更新OK_1。lotnum[{}]'.format(
                                                        myobj.wow_lotnum))
                                                myobj.wow_upd_status = 1  # 掲載中に更新

                                    except:
                                        # 更新時にエラー？
                                        my_err_list = {
                                            'batch_name': 'wowma_stock_chk exec_wowma_goods_update_bk point 1_1',
                                            'gid': myobj.gid,
                                            'status': 1,
                                            'code': myobj.gcode,
                                            'message': traceback.format_exc(),
                                        }
                                        error_goods_log.exe_error_log(my_err_list)
                                        #continue  # DB更新せずに戻す
                                        raise Exception(
                                            "出品OKで在庫あるので更新中に失敗？ gid:[{0}] stock:[{1}]".format(
                                                myobj.gid, myobj.stock))

                                elif ret_obj['res_rtn'] != "0":
                                    self._logger.debug(
                                        "exec_wowma_goods_update_bk wowma 商品登録でエラー [{}][{}]".format(
                                            ret_obj['res_code'], ret_obj['res_msg']))
                                    chk_flg = 1  # なにかエラーになってた

                                elif ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                    self._logger.debug(
                                        "exec_wowma_goods_update_bk wowma 商品登録できた [{}][{}]".format(
                                            ret_obj['res_code'], ret_obj['res_msg']))
                                    # lotnumberを更新しておく
                                    myobj.wow_lotnum = ret_obj['res_code']

                            if chk_flg == 0:
                                # 0が返ってきて 出品OKだったら、フラグを出品済みに
                                # 出品失敗なら 1 が返される。この場合は未出品のまま
                                self._logger.debug('--> exec_wowma_goods_update_bk 登録OK！ 1_2')
                                myobj.wow_on_flg = 1  # OK
                                myobj.wow_upd_status = 1  # 掲載中に更新
                            else:
                                # 更新時にエラー？
                                my_err_list = {
                                    'batch_name': 'wowma_stock_chk exec_wowma_goods_update_bk point 2_1',
                                    'gid': myobj.gid,
                                    'status': 1,
                                    'code': myobj.gcode,
                                    'message': traceback.format_exc(),
                                }
                                error_goods_log.exe_error_log(my_err_list)
                                raise Exception("wowma更新時に失敗？ _1 {}".format(myobj.gcode))

                        except:
                            # 更新時にエラー？
                            my_err_list = {
                                'batch_name': 'exec_wowma_goods_update_bk wowma_update_stock point 2_2',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': myobj.gcode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            raise Exception(
                                "出品OKで在庫あるので登録中に失敗？_2 gid:[{0}] stock:[{1}]".format(
                                    myobj.gid, myobj.stock))

                    else:
                        # 掲載中 wow_upd_status = 1
                        # 現在の在庫数で更新する
                        self._logger.debug('--> exec_wowma_goods_update_bk 掲載中。現時点の在庫数で更新')
                        try:
                            ret_obj_list = self._wowma_access.wowma_update_item_info(
                                    myobj.wow_gname,
                                    myobj.gid,
                                    myobj.gcode,
                                    myobj.wow_price,
                                    myobj.wow_fixed_price,
                                    myobj.wow_postage_segment,
                                    myobj.wow_postage,
                                    myobj.wow_delivery_method_id,
                                    myobj.wow_gdetail,
                                    myobj.wow_ctid,
                                    myobj.wow_keyword,
                                    myobj.wow_tagid,
                                    myobj.wow_upd_status,  # 1は販売中。2は販売終了。
                                    int(myobj.stock),  # 在庫数
                                    images,  # 画像情報。リストで images[imageUrl,imageName,imageSeq]
                            )
                            for ret_obj in ret_obj_list:
                                if ret_obj['res_rtn'] == "0":  # 正常に更新されていた場合
                                    # lotnumberを更新しておく
                                    myobj.wow_lotnum = ret_obj['res_code']
                                    myobj.wow_on_flg = 1  # 更新成功した。
                                    self._logger.debug(
                                        '--> exec_wowma_goods_update_bk 在庫数更新 gid:[{0}] stock:[{1}]'.format(
                                            myobj.gid, myobj.stock))
                        except:
                            # 更新時にエラー？
                            #raise Exception("在庫を0更新時に失敗？ gid:[{0}] stock:[{1}]".format(gid, tmpgretail))
                            my_err_list = {
                                'batch_name': 'exec_wowma_goods_update_bk wowma_update_stock point 1_1',
                                'gid': myobj.gid,
                                'status': 1,
                                'code': myobj.gcode,
                                'message': traceback.format_exc(),
                            }
                            error_goods_log.exe_error_log(my_err_list)
                            raise Exception(
                                "出品OKで在庫あるのに更新中に失敗？_3 gid:[{0}] stock:[{1}]".format(
                                    myobj.gid, myobj.stock))


                else:  # 在庫数の取得エラー？
                    raise Exception("在庫数の取得に失敗？{}".format(myobj.stock))

            else:
                # ここにきたら、wow_on_flg は 2（NG）のはず。そのままにしておく
                # ただし本メソッド呼び出し時の条件で 2は除外してあるのでここには来ないはず
                self._logger.debug('--> exec_wowma_goods_update_bk 処理せず flg=2 （NG）')
                return True, "wowma 商品情報更新 flg=2 （NG）なので更新せずに終了"

            # DBを更新
            myobj.save()

        except:
            return False, traceback.format_exc()  # DB更新せずに戻す

        return True, "wowma 商品情報更新 正常終了"

