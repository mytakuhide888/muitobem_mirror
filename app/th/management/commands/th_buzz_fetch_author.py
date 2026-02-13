# -*- coding: utf-8 -*-
"""
Threads 投稿者の過去投稿を取得するコマンド

使用例:
  python manage.py th_buzz_fetch_author --username "example_user"
  python manage.py th_buzz_fetch_author --author-id 3
  python manage.py th_buzz_fetch_author --job-id 5
"""
import json
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from th.models import THBuzzAuthor, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import ThreadsBuzzScraper, ViralityDetector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Threads 投稿者の過去投稿を取得して DB に保存"

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', type=str, default=None,
            help='Threads アカウント名（@なし）',
        )
        parser.add_argument(
            '--author-id', type=int, default=None,
            help='THBuzzAuthor の DB ID を指定',
        )
        parser.add_argument(
            '--job-id', type=int, default=None,
            help='THBuzzSearchJob の ID を指定して実行',
        )
        parser.add_argument(
            '--max-scrolls', type=int, default=10,
            help='最大スクロール回数（デフォルト: 10）',
        )
        parser.add_argument(
            '--include-replies', action='store_true',
            help='低品質リプライも含めて取得する',
        )

    def _fetch_single_author(self, scraper, username, max_scrolls, exclude_replies):
        """単一アカウントのプロフィール＋過去投稿を取得して DB 保存。(new_count, updated_count) を返す。"""
        author, _ = THBuzzAuthor.objects.get_or_create(
            username=username,
            defaults={'profile_url': f"https://www.threads.com/@{username}"},
        )

        # プロフィール更新
        profile = scraper.fetch_author_profile(username)
        author.display_name = profile.get('display_name') or author.display_name
        author.bio = profile.get('bio', '')
        author.followers_count = profile.get('followers_count')
        author.following_count = profile.get('following_count')
        author.is_verified = profile.get('is_verified', False)
        author.raw_json = profile
        author.save()
        self.stdout.write(f"プロフィール更新完了: @{username}")

        # 過去投稿取得
        posts = scraper.fetch_author_posts(username, max_scrolls=max_scrolls, exclude_replies=exclude_replies)
        self.stdout.write(f"取得件数: {len(posts)}")

        new_count = 0
        updated_count = 0
        for post_data in posts:
            text = post_data.get('text_content', '')
            if not text:
                continue

            followers = author.followers_count or 0
            virality = ViralityDetector.is_viral(post_data, followers)
            imp = post_data.get('impressions')

            # 重複チェック → 既存なら数値を更新
            existing = THBuzzPost.objects.filter(author=author, text_content=text).first()
            if existing:
                existing.like_count = post_data.get('like_count', 0)
                existing.reply_count = post_data.get('reply_count', 0)
                existing.repost_count = post_data.get('repost_count', 0)
                existing.engagement_rate = virality['engagement_rate']
                existing.engagement_score = virality['engagement_score']
                existing.is_viral = virality['is_viral']
                if imp is not None:
                    existing.impressions = imp
                if post_data.get('posted_at') and not existing.posted_at:
                    existing.posted_at = post_data['posted_at']
                if post_data.get('post_url') and not existing.post_url:
                    existing.post_url = post_data['post_url']
                # is_pinned を raw_json に保存
                raw = existing.raw_json or {}
                raw['is_pinned'] = post_data.get('is_pinned', False)
                existing.raw_json = raw
                existing.media_type = post_data.get('media_type', '')
                existing.media_urls = post_data.get('media_urls', [])
                existing.save()
                updated_count += 1
                continue

            raw_json = {'is_pinned': post_data.get('is_pinned', False)}
            THBuzzPost.objects.create(
                author=author,
                post_url=post_data.get('post_url', ''),
                text_content=text,
                like_count=post_data.get('like_count', 0),
                reply_count=post_data.get('reply_count', 0),
                repost_count=post_data.get('repost_count', 0),
                impressions=imp,
                engagement_rate=virality['engagement_rate'],
                engagement_score=virality['engagement_score'],
                is_viral=virality['is_viral'],
                search_keyword='',
                posted_at=post_data.get('posted_at'),
                raw_json=raw_json,
                media_type=post_data.get('media_type', ''),
                media_urls=post_data.get('media_urls', []),
            )
            new_count += 1

        # 成長指標を再計算
        author.update_growth_stats()
        self.stdout.write(
            f"成長指標更新: score={author.growth_score}, "
            f"followers/day={author.followers_per_day}, "
            f"age={author.account_age_days}days"
        )

        return new_count, updated_count

    def handle(self, *args, **opts):
        # Playwright sync API が内部でイベントループを作成するため、
        # Django ORM の async safety チェックを無効化する
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        job = None
        username = opts.get('username')
        author_id = opts.get('author_id')
        max_scrolls = opts['max_scrolls']
        exclude_replies = not opts.get('include_replies', False)

        # ── ジョブ ID 指定の場合: 複数アカウントをループ処理 ──
        if opts.get('job_id'):
            try:
                job = THBuzzSearchJob.objects.get(pk=opts['job_id'])
                usernames = json.loads(job.keywords)
                job.status = 'RUNNING'
                job.started_at = timezone.now()
                job.save(update_fields=['status', 'started_at'])
            except THBuzzSearchJob.DoesNotExist:
                self.stderr.write(f"ジョブ ID {opts['job_id']} が見つかりません")
                return

            self.stdout.write(f"ジョブ #{job.id}: アカウント {len(usernames)} 件を処理")
            logger.info("[CMD] th_buzz_fetch_author ジョブ開始: job_id=%s, usernames=%s", job.id, usernames)
            total_new = 0
            error_occurred = None

            try:
                with ThreadsBuzzScraper() as scraper:
                    for uname in usernames:
                        uname = uname.strip().lstrip('@')
                        if not uname:
                            continue
                        self.stdout.write(f"\n--- @{uname} ---")
                        try:
                            new_count, updated_count = self._fetch_single_author(
                                scraper, uname, max_scrolls, exclude_replies,
                            )
                            total_new += new_count
                            logger.info("[CMD] @%s 完了: new=%d, updated=%d", uname, new_count, updated_count)
                            self.stdout.write(f"完了: @{uname} 新規 {new_count} 件, 更新 {updated_count} 件")
                        except Exception as e:
                            logger.exception("[CMD] @%s 取得エラー（スキップ）", uname)
                            self.stderr.write(f"@{uname} エラー（スキップ）: {e}")
            except Exception as e:
                logger.exception("[CMD] th_buzz_fetch_author ジョブ全体エラー")
                self.stderr.write(f"エラー: {e}")
                error_occurred = e
            finally:
                if job:
                    try:
                        job.refresh_from_db()
                        if error_occurred:
                            job.status = 'FAILED'
                            job.completed_at = timezone.now()
                            job.error_message = str(error_occurred)
                            job.save(update_fields=['status', 'completed_at', 'error_message'])
                        elif job.status == 'RUNNING':
                            job.status = 'COMPLETED'
                            job.completed_at = timezone.now()
                            job.result_count = total_new
                            job.save(update_fields=['status', 'completed_at', 'result_count'])
                    except Exception as e:
                        logger.error("ジョブステータス更新失敗 (job_id=%s): %s", job.id, e)

            self.stdout.write(f"\nジョブ完了: 合計新規 {total_new} 件")
            return

        # ── 単体実行（既存互換） ──
        if author_id:
            try:
                author = THBuzzAuthor.objects.get(pk=author_id)
                username = author.username
            except THBuzzAuthor.DoesNotExist:
                self.stderr.write(f"投稿者 ID {author_id} が見つかりません")
                return
        elif not username:
            self.stderr.write("--username, --author-id, または --job-id を指定してください")
            return

        self.stdout.write(f"投稿取得開始: @{username} (max_scrolls={max_scrolls})")
        logger.info("[CMD] th_buzz_fetch_author 開始: username=%s, author_id=%s", username, author_id)

        try:
            with ThreadsBuzzScraper() as scraper:
                new_count, updated_count = self._fetch_single_author(
                    scraper, username, max_scrolls, exclude_replies,
                )
        except Exception as e:
            logger.exception("[CMD] 投稿取得エラー @%s", username)
            self.stderr.write(f"エラー: {e}")
            return

        logger.info("[CMD] th_buzz_fetch_author 完了: username=%s, new=%d, updated=%d", username, new_count, updated_count)
        self.stdout.write(f"完了: @{username} 新規 {new_count} 件保存, {updated_count} 件更新")
