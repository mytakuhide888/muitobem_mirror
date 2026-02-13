# -*- coding: utf-8 -*-
"""
投稿データ不足のアカウントに対して過去投稿を自動取得するコマンド
成長スコアの精度を高めるための「深掘りスキャン」。

使用例:
  python manage.py th_buzz_deep_scan
  python manage.py th_buzz_deep_scan --max-authors 20
  python manage.py th_buzz_deep_scan --job-id 5
"""
import json
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from th.models import THBuzzAuthor, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import ThreadsBuzzScraper, ViralityDetector

logger = logging.getLogger(__name__)

# 投稿数がこの値以下のアカウントを深掘り対象とする
POSTS_THRESHOLD = 3


class Command(BaseCommand):
    help = "投稿データ不足のアカウントの過去投稿を自動取得して成長スコアを再計算"

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-authors', type=int, default=10,
            help='1回の実行で処理するアカウント数の上限（デフォルト: 10）',
        )
        parser.add_argument(
            '--job-id', type=int, default=None,
            help='THBuzzSearchJob の ID を指定して実行',
        )
        parser.add_argument(
            '--max-scrolls', type=int, default=10,
            help='各アカウントの最大スクロール回数（デフォルト: 10）',
        )
        parser.add_argument(
            '--include-replies', action='store_true',
            help='低品質リプライも含めて取得する',
        )

    def _fetch_author_posts(self, scraper, author, max_scrolls, exclude_replies):
        """単一アカウントの過去投稿を取得して DB 保存。新規保存件数を返す。"""
        username = author.username

        # プロフィール更新
        profile = scraper.fetch_author_profile(username)
        author.display_name = profile.get('display_name') or author.display_name
        author.bio = profile.get('bio', '')
        author.followers_count = profile.get('followers_count')
        author.following_count = profile.get('following_count')
        author.is_verified = profile.get('is_verified', False)
        author.raw_json = profile
        author.save()

        # 過去投稿取得
        posts = scraper.fetch_author_posts(username, max_scrolls=max_scrolls, exclude_replies=exclude_replies)
        self.stdout.write(f"  取得: {len(posts)} 件")

        new_count = 0
        for post_data in posts:
            text = post_data.get('text_content', '')
            if not text:
                continue

            followers = author.followers_count or 0
            virality = ViralityDetector.is_viral(post_data, followers)
            imp = post_data.get('impressions')

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
                raw = existing.raw_json or {}
                raw['is_pinned'] = post_data.get('is_pinned', False)
                existing.raw_json = raw
                existing.media_type = post_data.get('media_type', '')
                existing.media_urls = post_data.get('media_urls', [])
                existing.save()
            else:
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
        return new_count

    def handle(self, *args, **opts):
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        job = None
        max_authors = opts['max_authors']
        max_scrolls = opts['max_scrolls']
        exclude_replies = not opts.get('include_replies', False)

        # ジョブ ID 指定の場合
        if opts.get('job_id'):
            try:
                job = THBuzzSearchJob.objects.get(pk=opts['job_id'])
                job.status = 'RUNNING'
                job.started_at = timezone.now()
                job.save(update_fields=['status', 'started_at'])
            except THBuzzSearchJob.DoesNotExist:
                self.stderr.write(f"ジョブ ID {opts['job_id']} が見つかりません")
                return

        # 深掘り対象: 投稿数がPOSTS_THRESHOLD以下かつフォロワー数が既知のアカウント
        targets = THBuzzAuthor.objects.filter(
            followers_count__isnull=False,
            followers_count__gt=0,
            total_post_count__lte=POSTS_THRESHOLD,
        ).order_by('-growth_score', '-followers_count')[:max_authors]

        # total_post_count が NULL のアカウントも対象
        targets_null = THBuzzAuthor.objects.filter(
            followers_count__isnull=False,
            followers_count__gt=0,
            total_post_count__isnull=True,
        ).order_by('-followers_count')[:max(max_authors - targets.count(), 0)]

        all_targets = list(targets) + list(targets_null)
        all_targets = all_targets[:max_authors]

        if not all_targets:
            msg = "深掘り対象のアカウントがありません（全アカウントの投稿が十分です）"
            self.stdout.write(msg)
            if job:
                job.status = 'COMPLETED'
                job.completed_at = timezone.now()
                job.result_count = 0
                job.error_message = msg
                job.save(update_fields=['status', 'completed_at', 'result_count', 'error_message'])
            return

        self.stdout.write(f"深掘りスキャン開始: {len(all_targets)} アカウント")
        logger.info("[CMD] th_buzz_deep_scan 開始: targets=%d", len(all_targets))

        total_new = 0
        processed = 0
        error_occurred = None

        try:
            with ThreadsBuzzScraper() as scraper:
                for author in all_targets:
                    self.stdout.write(f"\n--- @{author.username} (現在投稿数: {author.total_post_count or 0}) ---")
                    try:
                        new_count = self._fetch_author_posts(
                            scraper, author, max_scrolls, exclude_replies,
                        )
                        total_new += new_count
                        processed += 1
                        self.stdout.write(
                            f"  完了: 新規 {new_count} 件, "
                            f"score={author.growth_score}, "
                            f"投稿数={author.total_post_count}"
                        )
                    except Exception as e:
                        logger.exception("[CMD] 深掘り失敗 @%s", author.username)
                        self.stderr.write(f"  @{author.username} エラー（スキップ）: {e}")

        except Exception as e:
            logger.exception("[CMD] 深掘りスキャン全体エラー")
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

        self.stdout.write(
            f"\n深掘りスキャン完了: {processed}/{len(all_targets)} アカウント処理, "
            f"新規投稿 {total_new} 件"
        )
        logger.info(
            "[CMD] th_buzz_deep_scan 完了: processed=%d, new_posts=%d",
            processed, total_new,
        )
