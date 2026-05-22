#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Threads ログイン用スタンドアロンスクリプト（Django 不要）

Playwright のみで Threads にログインし、Cookie 等を JSON で保存する。
保存先: app/deploy/threads_session_<account>.json

使用例:
  cd /home/niiya/muitobem_mirror
  source .venv/bin/activate     # or .venv-login
  export RESEARCH_PROXY_URL='http://user:pass@geo.iproyal.com:12321'
  python scripts/local_threads_login.py arayasaki7

  # プロキシを引数で渡したい場合
  python scripts/local_threads_login.py arayasaki7 'http://user:pass@geo.iproyal.com:12321'

  # プロキシを使わず素の接続でログインしたい場合（非推奨：VPS 反映時に IP 不整合で凍結リスク）
  python scripts/local_threads_login.py arayasaki7 ''
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote


def parse_args():
    if len(sys.argv) < 2:
        sys.stderr.write(
            "使用法: python scripts/local_threads_login.py <account_name> [proxy_url]\n"
        )
        sys.exit(2)
    account = sys.argv[1]
    if len(sys.argv) >= 3:
        proxy_url = sys.argv[2]
    else:
        proxy_url = os.environ.get('RESEARCH_PROXY_URL', '')
    return account, proxy_url


def build_proxy_param(proxy_url: str):
    if not proxy_url:
        return None
    try:
        u = urlparse(proxy_url)
        if not u.hostname or not u.port:
            sys.stderr.write(f"プロキシ URL の形式が不正: {proxy_url}\n")
            return None
        param = {'server': f'{u.scheme}://{u.hostname}:{u.port}'}
        if u.username:
            param['username'] = u.username
        if u.password:
            param['password'] = unquote(u.password)
        return param
    except Exception as e:
        sys.stderr.write(f"プロキシ URL のパース失敗: {e}\n")
        return None


def main():
    account, proxy_url = parse_args()

    project_root = Path(__file__).resolve().parent.parent
    deploy_dir = project_root / 'app' / 'deploy'
    deploy_dir.mkdir(parents=True, exist_ok=True)
    output_path = deploy_dir / f'threads_session_{account}.json'

    proxy_param = build_proxy_param(proxy_url)

    print('=' * 60)
    print('Threads ログイン（スタンドアロン版）')
    print('=' * 60)
    print(f'対象アカウント: {account}')
    print(f'保存先:         {output_path}')
    if proxy_param:
        print(f'プロキシ:       {proxy_param["server"]} '
              f'(user={proxy_param.get("username", "?")} pass=*****)')
    else:
        print('プロキシ:       なし')
        print('  ⚠ VPS の本番では RESEARCH_PROXY_URL を使うため、'
              'ここで素の IP でログインすると Cookie の IP 紐付きが不整合になります。')
        print('  ⚠ 本番運用なら必ずプロキシ経由でログインしてください。')
    print()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.stderr.write(
            'playwright がインストールされていません。\n'
            '  pip install playwright\n'
            '  playwright install chromium\n'
            '  playwright install-deps    # WSL の場合\n'
        )
        sys.exit(1)

    with sync_playwright() as p:
        launch_kwargs = dict(
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
        )
        if proxy_param:
            launch_kwargs['proxy'] = proxy_param

        try:
            browser = p.chromium.launch(**launch_kwargs)
        except Exception as e:
            sys.stderr.write(f'Chromium 起動失敗: {e}\n')
            sys.stderr.write(
                '\nGUI が出ない場合の確認:\n'
                '  echo "$WAYLAND_DISPLAY $DISPLAY"\n'
                '  → Win11+WSL2 なら WSLg で自動。Win10 は VcXsrv 等が必要。\n'
            )
            sys.exit(1)

        context = browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
        )
        page = context.new_page()

        # webdriver 隠蔽
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        try:
            page.goto('https://www.threads.com/login', wait_until='domcontentloaded')
        except Exception as e:
            sys.stderr.write(f'ページ読み込み失敗: {e}\n')
            browser.close()
            sys.exit(1)

        print('ブラウザを開きました。Threads にログインしてください...')
        print('ログインが完了し、フィードが表示されたらこのターミナルに戻って Enter を押してください。')
        print()
        try:
            input('ログイン完了後、Enter > ')
        except (EOFError, KeyboardInterrupt):
            print('\n中断されました。')
            browser.close()
            sys.exit(130)

        # セッション保存
        context.storage_state(path=str(output_path))

        # 確認情報
        try:
            current_url = page.url
        except Exception:
            current_url = '(取得失敗)'
        try:
            cookies = context.cookies()
        except Exception:
            cookies = []
        cookie_domains = sorted({c.get('domain', '') for c in cookies if c.get('domain')})

        browser.close()

    print()
    print('=' * 60)
    print(f'セッション保存完了: {output_path}')
    print(f'Cookie 数:          {len(cookies)}')
    print(f'Cookie ドメイン:    {", ".join(cookie_domains) if cookie_domains else "(なし)"}')
    print(f'最終 URL:           {current_url}')
    print('=' * 60)
    print()
    print('VPS への転送:')
    print(f'  scp {output_path} muitobem-new:/srv/muitobem/app/deploy/')
    print()
    # 簡易整合性チェック
    target_cookies = {'sessionid', 'ds_user_id'}
    found = {c.get('name') for c in cookies} & target_cookies
    if not found:
        print('⚠ 警告: sessionid / ds_user_id が見当たりません。ログイン未完了の可能性があります。')
        print('  ブラウザでフィードが見える状態だったか確認してから再実行してください。')
    else:
        print(f'✓ ログイン確認: {found} を取得済み')


if __name__ == '__main__':
    main()
