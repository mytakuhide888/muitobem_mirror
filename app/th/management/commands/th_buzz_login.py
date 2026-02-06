# -*- coding: utf-8 -*-
"""
Threads ログインセッション保存コマンド

ヘッドフルブラウザを開き、手動でログイン後にセッション（Cookie等）を
JSON ファイルに保存する。保存したファイルをスクレイパーが読み込んで
認証済みリクエストを送信する。

使用例（ローカルPCで実行）:
  python manage.py th_buzz_login
  python manage.py th_buzz_login --output /path/to/threads_session.json

VPSへの反映:
  scp threads_session.json user@vps:/srv/muitobem/app/deploy/threads_session.json
"""
import logging
import os

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

DEFAULT_SESSION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'deploy', 'threads_session.json',
)


class Command(BaseCommand):
    help = "Threads にブラウザでログインしてセッションを保存"

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            default=DEFAULT_SESSION_PATH,
            help=f'セッションファイルの保存先 (デフォルト: {DEFAULT_SESSION_PATH})',
        )
        parser.add_argument(
            '--timeout', type=int, default=300,
            help='ログイン待機タイムアウト秒数 (デフォルト: 300)',
        )

    def handle(self, *args, **opts):
        output_path = opts['output']
        timeout_sec = opts['timeout']

        self.stdout.write("=" * 60)
        self.stdout.write("Threads ログインセッション保存ツール")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("ブラウザが開きます。Threads にログインしてください。")
        self.stdout.write("ログインが完了し、フィードが表示されたら")
        self.stdout.write("このターミナルに戻って Enter を押してください。")
        self.stdout.write("")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.stderr.write(
                "playwright がインストールされていません。\n"
                "pip install playwright && playwright install chromium"
            )
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 900},
                locale='ja-JP',
                timezone_id='Asia/Tokyo',
            )
            page = context.new_page()

            # webdriver 隠蔽
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            page.goto("https://www.threads.com/login", wait_until='domcontentloaded')

            self.stdout.write("ブラウザを開きました。ログインしてください...")
            self.stdout.write(f"(最大 {timeout_sec} 秒待機)")
            self.stdout.write("")

            # ユーザーがログインするまで待機
            try:
                input("ログイン完了後、Enter を押してください > ")
            except (EOFError, KeyboardInterrupt):
                self.stdout.write("\n中断されました。")
                browser.close()
                return

            # セッション保存
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            context.storage_state(path=output_path)

            # 確認
            current_url = page.url
            cookies = context.cookies()
            cookie_domains = set(c['domain'] for c in cookies)

            browser.close()

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(f"セッション保存完了: {output_path}")
        self.stdout.write(f"Cookie数: {len(cookies)}")
        self.stdout.write(f"Cookie ドメイン: {', '.join(sorted(cookie_domains))}")
        self.stdout.write(f"最終URL: {current_url}")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("VPS にコピーする場合:")
        self.stdout.write(f"  scp {output_path} user@vps:/srv/muitobem/app/deploy/threads_session.json")
