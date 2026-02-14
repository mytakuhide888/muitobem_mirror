# -*- coding: utf-8 -*-
"""
プロフィール画像URLが未取得のアカウントを一括更新するコマンド
ブラウザで各アカウントのプロフィールページを開き、画像URLだけを取得・保存する。

使用例:
  python manage.py th_buzz_update_avatars
  python manage.py th_buzz_update_avatars --max-authors 50
  python manage.py th_buzz_update_avatars --all   # 既取得分も含めて全件再取得
"""
import logging

from django.core.management.base import BaseCommand

from th.models import THBuzzAuthor
from th.services.buzz_scraper import ThreadsBuzzScraper

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "プロフィール画像URLが未取得のアカウントを一括更新"

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-authors', type=int, default=30,
            help='1回の実行で処理するアカウント数の上限（デフォルト: 30）',
        )
        parser.add_argument(
            '--all', action='store_true',
            help='既取得のアカウントも含めて全件再取得する',
        )

    def handle(self, *args, **opts):
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        max_authors = opts['max_authors']
        update_all = opts.get('all', False)

        if update_all:
            targets = THBuzzAuthor.objects.all().order_by('-growth_score', '-followers_count')[:max_authors]
        else:
            targets = THBuzzAuthor.objects.filter(
                profile_pic_url='',
            ).order_by('-growth_score', '-followers_count')[:max_authors]

        targets = list(targets)
        if not targets:
            self.stdout.write("プロフィール画像の更新対象がありません。")
            return

        self.stdout.write(f"プロフィール画像更新開始: {len(targets)} アカウント")
        logger.info("[CMD] th_buzz_update_avatars 開始: targets=%d", len(targets))

        updated = 0
        failed = 0

        try:
            with ThreadsBuzzScraper() as scraper:
                for author in targets:
                    try:
                        profile = scraper.fetch_author_profile(author.username)
                        pic_url = profile.get('profile_pic_url', '')
                        if pic_url:
                            author.profile_pic_url = pic_url
                            # ついでに他のプロフィール情報も更新
                            author.display_name = profile.get('display_name') or author.display_name
                            author.bio = profile.get('bio', '') or author.bio
                            if profile.get('followers_count') is not None:
                                author.followers_count = profile['followers_count']
                            if profile.get('following_count') is not None:
                                author.following_count = profile['following_count']
                            author.is_verified = profile.get('is_verified', False)
                            author.raw_json = profile
                            author.save()
                            updated += 1
                            self.stdout.write(f"  OK: @{author.username} → {pic_url[:60]}...")
                        else:
                            failed += 1
                            self.stdout.write(f"  NG: @{author.username} 画像URL取得失敗")
                    except Exception as e:
                        failed += 1
                        logger.warning("プロフィール画像更新失敗 @%s: %s", author.username, e)
                        self.stderr.write(f"  ERR: @{author.username} - {e}")

        except Exception as e:
            logger.exception("th_buzz_update_avatars 全体エラー")
            self.stderr.write(f"エラー: {e}")

        self.stdout.write(f"\n完了: 更新 {updated} 件, 失敗 {failed} 件")
        logger.info("[CMD] th_buzz_update_avatars 完了: updated=%d, failed=%d", updated, failed)
