#!/usr/bin/env python3
"""
Threads ログインセッション保存スクリプト（スタンドアロン・Django不要）

使い方:
  python3 threads_login.py
  python3 threads_login.py --output /path/to/threads_session.json

保存後、VPSにコピー:
  scp <output_path> django@VPS:/srv/muitobem/app/deploy/threads_session.json
"""
import argparse
import os
import subprocess
import sys

DEFAULT_SCP_DEST = "muitobem-vps:/srv/muitobem/app/deploy/threads_session.json"


def main():
    parser = argparse.ArgumentParser(description="Threads ログインセッション保存")
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "deploy", "threads_session.json"),
        help="セッションファイルの保存先",
    )
    parser.add_argument(
        "--no-scp", action="store_true",
        help="SCP転送をスキップ（ローカル保存のみ）",
    )
    parser.add_argument(
        "--scp-dest",
        default=DEFAULT_SCP_DEST,
        help=f"SCP転送先（デフォルト: {DEFAULT_SCP_DEST}）",
    )
    args = parser.parse_args()
    output_path = os.path.abspath(args.output)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright がインストールされていません。")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    print("=" * 60)
    print("Threads ログインセッション保存ツール")
    print("=" * 60)
    print()
    print("ブラウザが開きます。Threads にログインしてください。")
    print("ログインが完了し、フィードが表示されたら")
    print("このターミナルに戻って Enter を押してください。")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page.goto("https://www.threads.com/login", wait_until="domcontentloaded")

        print("ブラウザを開きました。ログインしてください...")
        print()

        try:
            input("ログイン完了後、Enter を押してください > ")
        except (EOFError, KeyboardInterrupt):
            print("\n中断しました。")
            browser.close()
            return

        # セッション保存
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        context.storage_state(path=output_path)

        cookies = context.cookies()
        domains = sorted(set(c["domain"] for c in cookies))
        current_url = page.url

        browser.close()

    print()
    print("=" * 60)
    print(f"セッション保存完了: {output_path}")
    print(f"Cookie数: {len(cookies)}")
    print(f"Cookie ドメイン: {', '.join(domains)}")
    print(f"最終URL: {current_url}")
    print("=" * 60)

    # SCP 自動転送
    if not args.no_scp:
        print()
        print(f"VPS に転送中: {args.scp_dest}")
        result = subprocess.run(
            ["scp", output_path, args.scp_dest],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print("SCP 転送完了!")
        else:
            print(f"SCP 転送失敗 (code={result.returncode})")
            if result.stderr:
                print(f"  エラー: {result.stderr.strip()}")
            print(f"手動で実行してください:")
            print(f"  scp {output_path} {args.scp_dest}")
    else:
        print()
        print("VPS にコピーする場合:")
        print(f"  scp {output_path} {args.scp_dest}")


if __name__ == "__main__":
    main()
