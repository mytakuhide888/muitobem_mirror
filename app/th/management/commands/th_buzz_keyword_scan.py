# -*- coding: utf-8 -*-
"""
キーワード一括巡回コマンド
複数キーワードで検索 → 新規投稿者のプロフィール取得 → 成長スコア計算を一括実行する。

使用例:
  python manage.py th_buzz_keyword_scan -k "占い" "タロット" "霊視"
  python manage.py th_buzz_keyword_scan --job-id 3
"""
import json
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from th.models import THBuzzAuthor, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import ThreadsBuzzScraper, ViralityDetector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "キーワード一括巡回: 検索 → プロフィール取得 → 成長スコア算出"

    def add_arguments(self, parser):
        parser.add_argument(
            '-k', '--keywords', nargs='+',
            help='検索キーワード（複数指定可）',
        )
        parser.add_argument(
            '--job-id', type=int, default=None,
            help='THBuzzSearchJob の ID を指定して実行',
        )
        parser.add_argument(
            '--max-profile-fetch', type=int, default=20,
            help='1回の巡回で取得するプロフィールの最大数（デフォルト: 20）',
        )
        parser.add_argument(
            '--sort-order', type=str, default='recent',
            choices=['recent', 'default'],
            help='検索結果の並び順: recent=新しい順, default=おすすめ順（デフォルト: recent）',
        )
        parser.add_argument(
            '--growth-filter', action='store_true',
            help='急成長フィルタ: コンセプト候補に該当しないアカウントの投稿を除外する',
        )

    def _recalc_author_posts(self, author):
        """投稿者のフォロワー数が判明した後、全投稿の ER / バズ判定を再計算"""
        posts = THBuzzPost.objects.filter(author=author)
        updated = 0
        for p in posts:
            post_data = {
                'like_count': p.like_count or 0,
                'reply_count': p.reply_count or 0,
                'repost_count': p.repost_count or 0,
            }
            virality = ViralityDetector.is_viral(post_data, author.followers_count)
            p.engagement_rate = virality['engagement_rate']
            p.engagement_score = virality['engagement_score']
            p.is_viral = virality['is_viral']
            p.save(update_fields=['engagement_rate', 'engagement_score', 'is_viral'])
            updated += 1
        if updated:
            logger.info("[CMD] @%s: %d件の投稿のER/バズ判定を再計算", author.username, updated)

    def handle(self, *args, **opts):
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        job = None
        keywords = opts.get('keywords') or []
        max_profile_fetch = opts['max_profile_fetch']
        growth_filter = opts.get('growth_filter', False)

        # ジョブ ID 指定の場合
        if opts['job_id']:
            try:
                job = THBuzzSearchJob.objects.get(pk=opts['job_id'])
                keywords = json.loads(job.keywords)
                if job.status != 'RUNNING':
                    job.status = 'RUNNING'
                    job.started_at = timezone.now()
                    job.save(update_fields=['status', 'started_at'])
            except THBuzzSearchJob.DoesNotExist:
                self.stderr.write(f"ジョブ ID {opts['job_id']} が見つかりません")
                return

        if not keywords:
            self.stderr.write("キーワードを指定してください (-k または --job-id)")
            return

        self.stdout.write(f"一括巡回開始: {keywords}")
        logger.info("[CMD] th_buzz_keyword_scan 開始: keywords=%s", keywords)

        total_new_posts = 0
        new_authors_fetched = 0
        error_occurred = None

        try:
            with ThreadsBuzzScraper() as scraper:
                # ─── Step 1: 各キーワードで検索 → 投稿保存 ───
                authors_to_fetch = set()

                for kw in keywords:
                    self.stdout.write(f"\n--- 検索中: {kw} ---")
                    logger.info("[SCAN] 検索実行: keyword=%s", kw)

                    sort_order = opts.get('sort_order', 'recent')
                    posts = scraper.search_keyword(kw, sort_order=sort_order)
                    self.stdout.write(f"  取得件数: {len(posts)}")

                    for post_data in posts:
                        username = post_data.get('username', '')
                        if not username:
                            continue

                        author, created = THBuzzAuthor.objects.get_or_create(
                            username=username,
                            defaults={
                                'display_name': post_data.get('display_name', ''),
                                'profile_url': f"https://www.threads.com/@{username}",
                            },
                        )

                        # バズ判定
                        followers = author.followers_count or 0
                        virality = ViralityDetector.is_viral(post_data, followers)

                        # 投稿を保存
                        text = post_data.get('text_content', '')
                        if not text:
                            continue

                        existing = THBuzzPost.objects.filter(
                            author=author, text_content=text,
                        ).first()
                        imp = post_data.get('impressions')

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
                            # 検索キーワードが未設定なら埋める
                            if not existing.search_keyword and kw:
                                existing.search_keyword = kw
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
                                search_keyword=kw,
                                posted_at=post_data.get('posted_at'),
                                raw_json=raw_json,
                                media_type=post_data.get('media_type', ''),
                                media_urls=post_data.get('media_urls', []),
                            )
                            total_new_posts += 1

                        # プロフィール未取得のアカウントを記録
                        if not author.followers_count:
                            authors_to_fetch.add(author.pk)

                # ─── Step 2: 新規投稿者のプロフィール取得 ───
                fetch_targets = list(authors_to_fetch)[:max_profile_fetch]
                self.stdout.write(f"\n--- プロフィール取得: {len(fetch_targets)}/{len(authors_to_fetch)} 件 ---")

                for author_pk in fetch_targets:
                    author = THBuzzAuthor.objects.get(pk=author_pk)
                    try:
                        profile = scraper.fetch_author_profile(author.username)
                        author.display_name = profile.get('display_name') or author.display_name
                        author.bio = profile.get('bio', '')
                        author.followers_count = profile.get('followers_count')
                        author.following_count = profile.get('following_count')
                        author.is_verified = profile.get('is_verified', False)
                        author.raw_json = profile
                        author.save()

                        # 成長指標を計算
                        author.update_growth_stats()
                        new_authors_fetched += 1

                        # フォロワー数が判明したので ER/バズ判定を再計算
                        if author.followers_count:
                            self._recalc_author_posts(author)

                        # 急成長フィルタ: 候補でないアカウントの投稿を削除
                        if growth_filter and not author.is_concept_candidate:
                            removed = THBuzzPost.objects.filter(author=author).count()
                            THBuzzPost.objects.filter(author=author).delete()
                            total_new_posts = max(total_new_posts - removed, 0)
                            self.stdout.write(
                                f"  @{author.username}: 候補外 → 投稿{removed}件を除外"
                            )
                        else:
                            self.stdout.write(
                                f"  @{author.username}: "
                                f"followers={author.followers_count}, "
                                f"score={author.growth_score}, "
                                f"f/day={author.followers_per_day}"
                                f"{' [候補]' if author.is_concept_candidate else ''}"
                            )
                    except Exception as e:
                        logger.warning("プロフィール取得失敗 @%s: %s", author.username, e)
                        self.stdout.write(f"  @{author.username}: 取得失敗 - {e}")

                # ─── Step 3: 既存アカウントの成長指標も更新 ───
                existing_authors = THBuzzAuthor.objects.filter(
                    followers_count__isnull=False,
                    growth_score__isnull=True,
                )
                for author in existing_authors:
                    author.update_growth_stats()

        except Exception as e:
            logger.exception("一括巡回エラー")
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
                        job.result_count = total_new_posts
                        job.save(update_fields=['status', 'completed_at', 'result_count'])
                except Exception as e:
                    logger.error("ジョブステータス更新失敗 (job_id=%s): %s", job.id, e)

        if error_occurred:
            return

        self.stdout.write(
            f"\n一括巡回完了: 新規投稿 {total_new_posts} 件, "
            f"プロフィール取得 {new_authors_fetched} 件"
        )
        logger.info(
            "[CMD] th_buzz_keyword_scan 完了: new_posts=%d, profiles=%d",
            total_new_posts, new_authors_fetched,
        )
