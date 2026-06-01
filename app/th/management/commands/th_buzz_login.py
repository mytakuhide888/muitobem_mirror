# -*- coding: utf-8 -*-
"""
Threads ログインセッション保存コマンド

ヘッドフルブラウザを開き、手動でログイン後にセッション（Cookie等）を
JSON ファイルに保存する。保存したファイルをスクレイパーが読み込んで
認証済みリクエストを送信する。

使用例（ローカルPCで実行）:
  python manage.py th_buzz_login                                  # legacy: deploy/threads_session.json
  python manage.py th_buzz_login --account arayahide3             # deploy/threads_session_arayahide3.json
  python manage.py th_buzz_login --account arayahide3 --proxy http://user:pass@gateway:port

VPSへの反映:
  scp deploy/threads_session_arayahide3.json user@vps:/srv/muitobem/app/deploy/
"""
import logging
import os

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

DEPLOY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'deploy',
)
DEFAULT_SESSION_PATH = os.path.join(DEPLOY_DIR, 'threads_session.json')


def _session_path_for_account(account_name: str) -> str:
    """アカウント名から保存パスを組み立てる"""
    safe = account_name.replace('/', '_').replace('..', '_')
    return os.path.join(DEPLOY_DIR, f'threads_session_{safe}.json')


class Command(BaseCommand):
    help = "Threads にブラウザでログインしてセッションを保存"

    def add_arguments(self, parser):
        parser.add_argument(
            '--account', '-a', default=None,
            help='ResearchAccount.name。指定時は threads_session_<name>.json に保存',
        )
        parser.add_argument(
            '--output', '-o', default=None,
            help='セッションファイルの保存先（--account より優先）',
        )
        parser.add_argument(
            '--proxy', default=None,
            help='プロキシ URL（http://user:pass@host:port）。Phase G では原則必須',
        )
        parser.add_argument(
            '--timeout', type=int, default=300,
            help='ログイン待機タイムアウト秒数 (デフォルト: 300)',
        )

    def handle(self, *args, **opts):
        account_name = opts.get('account')
        output_path = opts.get('output')
        proxy_url = opts.get('proxy')
        timeout_sec = opts['timeout']

        # 保存パス決定: --output > --account 連動 > legacy
        if not output_path:
            if account_name:
                output_path = _session_path_for_account(account_name)
            else:
                output_path = DEFAULT_SESSION_PATH

        # プロキシ URL の解決（環境変数 RESEARCH_PROXY_URL も見る）
        if not proxy_url:
            proxy_url = os.environ.get('RESEARCH_PROXY_URL', '') or None

        self.stdout.write("=" * 60)
        self.stdout.write("Threads ログインセッション保存ツール")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        if account_name:
            self.stdout.write(f"対象アカウント: {account_name}")
        self.stdout.write(f"保存先: {output_path}")
        if proxy_url:
            # パスワード部分は表示しない
            from urllib.parse import urlparse
            try:
                u = urlparse(proxy_url)
                self.stdout.write(f"プロキシ: {u.scheme}://{u.hostname}:{u.port} (認証あり)")
            except Exception:
                self.stdout.write("プロキシ: 設定あり")
        else:
            self.stdout.write("プロキシ: なし（VPS で同セッションを使う場合は本番のプロキシと整合する必要あり）")
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

        # プロキシ設定の組み立て
        proxy_param = None
        if proxy_url:
            from urllib.parse import urlparse, unquote
            try:
                u = urlparse(proxy_url)
                proxy_param = {'server': f"{u.scheme}://{u.hostname}:{u.port}"}
                if u.username:
                    proxy_param['username'] = u.username
                if u.password:
                    proxy_param['password'] = unquote(u.password)
            except Exception as e:
                self.stderr.write(f"プロキシ URL のパースに失敗: {e}")
                proxy_param = None

        with sync_playwright() as p:
            launch_kwargs = dict(
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
            )
            if proxy_param:
                launch_kwargs['proxy'] = proxy_param
            browser = p.chromium.launch(**launch_kwargs)
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

        # ResearchAccount レコードを同期（指定時のみ）
        if account_name:
            try:
                from th.models import ResearchAccount
                from django.utils import timezone as _tz
                ra, created = ResearchAccount.objects.get_or_create(
                    name=account_name,
                    defaults={
                        'threads_username': account_name,
                        'storage_state_path': output_path,
                        'status': ResearchAccount.STATUS_VPS_WARMUP,
                        'warmup_started_at': _tz.now(),
                    },
                )
                # 既存なら storage_state_path を最新に
                if not created and ra.storage_state_path != output_path:
                    ra.storage_state_path = output_path
                    ra.save(update_fields=['storage_state_path', 'updated_at'])
                self.stdout.write(
                    f"ResearchAccount[{ra.name}] を {'作成' if created else '更新'}: "
                    f"status={ra.status}, storage_state_path={ra.storage_state_path}"
                )
            except Exception as e:
                self.stderr.write(f"ResearchAccount 同期失敗（ローカル実行なら無視可）: {e}")

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(f"セッション保存完了: {output_path}")
        self.stdout.write(f"Cookie数: {len(cookies)}")
        self.stdout.write(f"Cookie ドメイン: {', '.join(sorted(cookie_domains))}")
        self.stdout.write(f"最終URL: {current_url}")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("VPS にコピーする場合:")
        target = os.path.basename(output_path)
        self.stdout.write(f"  scp {output_path} user@vps:/srv/muitobem/app/deploy/{target}")
