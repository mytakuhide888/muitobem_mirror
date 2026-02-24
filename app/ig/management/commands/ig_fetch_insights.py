# -*- coding: utf-8 -*-
"""Instagram投稿インサイト定期取得コマンド"""
from django.core.management.base import BaseCommand

from ig.models import InstagramBusinessAccount
from ig.services.insights_fetcher import refresh_all_post_insights


class Command(BaseCommand):
    help = "Instagram投稿のインサイト（インプレッション/リーチ/ER等）を一括取得してDBに保存"

    def add_arguments(self, parser):
        parser.add_argument("--account-id", type=int, help="特定のアカウントIDのみ対象")
        parser.add_argument("--limit", type=int, default=20, help="各アカウントの対象投稿件数（デフォルト: 20）")

    def handle(self, *args, **options):
        account_id = options.get("account_id")
        limit = options["limit"]

        if account_id:
            accounts = InstagramBusinessAccount.objects.filter(pk=account_id, is_active=True)
        else:
            accounts = InstagramBusinessAccount.objects.filter(is_active=True)

        if not accounts.exists():
            self.stdout.write("対象アカウントなし")
            return

        total = 0
        for account in accounts:
            count = refresh_all_post_insights(account, limit=limit)
            self.stdout.write(f"[{account.username}] {count}件更新")
            total += count

        self.stdout.write(self.style.SUCCESS(f"完了: 合計 {total} 件のインサイトを更新"))
