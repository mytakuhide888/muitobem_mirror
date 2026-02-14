# -*- coding: utf-8 -*-
"""
Threads バズ投稿検索コマンド
キーワードで Threads を検索し、バズ投稿を DB に保存する。

使用例:
  python manage.py th_buzz_search -k "AI" "副業"
  python manage.py th_buzz_search --job-id 3
"""
import json
import logging
import traceback as tb

from django.core.management.base import BaseCommand
from django.utils import timezone

from th.models import THBuzzAuthor, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import ThreadsBuzzScraper, ViralityDetector, check_session_validity

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Threads バズ投稿をキーワード検索で取得"

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
            '--dry-run', action='store_true',
            help='DB保存せずに結果を表示のみ',
        )
        parser.add_argument(
            '--include-replies', action='store_true',
            help='低品質リプライも含めて取得する',
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
        # Playwright sync API が内部でイベントループを作成するため、
        # Django ORM の async safety チェックを無効化する
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        job = None
        keywords = opts.get('keywords') or []

        # ジョブ ID 指定の場合
        if opts['job_id']:
            try:
                job = THBuzzSearchJob.objects.get(pk=opts['job_id'])
                keywords = json.loads(job.keywords)
                job.status = 'RUNNING'
                job.started_at = timezone.now()
                job.save(update_fields=['status', 'started_at'])
            except THBuzzSearchJob.DoesNotExist:
                self.stderr.write(f"ジョブ ID {opts['job_id']} が見つかりません")
                return

        if not keywords:
            self.stderr.write("キーワードを指定してください (-k または --job-id)")
            return

        growth_filter = opts.get('growth_filter', False)
        self.stdout.write(f"検索キーワード: {keywords}")
        logger.info("[CMD] th_buzz_search 開始: keywords=%s, job_id=%s", keywords, opts.get('job_id'))
        total_count = 0
        error_occurred = None
        error_tb = ''
        # 同一実行内でプロフィール取得済みのユーザーを追跡
        profile_fetched = set()

        try:
            with ThreadsBuzzScraper() as scraper:
                for kw in keywords:
                    self.stdout.write(f"\n--- 検索中: {kw} ---")
                    logger.info("[CMD] 検索実行: keyword=%s", kw)
                    exclude_replies = not opts.get('include_replies', False)
                    sort_order = opts.get('sort_order', 'recent')
                    posts = scraper.search_keyword(kw, exclude_replies=exclude_replies, sort_order=sort_order)
                    self.stdout.write(f"  取得件数: {len(posts)}")
                    logger.info("[CMD] 取得結果: keyword=%s, count=%d", kw, len(posts))

                    for post_data in posts:
                        username = post_data.get('username', '')
                        if not username:
                            continue

                        # 投稿者プロフィール取得 or 更新
                        author, _ = THBuzzAuthor.objects.get_or_create(
                            username=username,
                            defaults={
                                'display_name': post_data.get('display_name', ''),
                                'profile_url': f"https://www.threads.com/@{username}",
                            },
                        )

                        # バズ判定
                        followers = author.followers_count or 0
                        virality = ViralityDetector.is_viral(post_data, followers)

                        if opts['dry_run']:
                            self.stdout.write(
                                f"  [DRY-RUN] @{username}: {post_data.get('text_content', '')[:40]} "
                                f"(likes={post_data.get('like_count', 0)}, "
                                f"score={virality['engagement_score']}, "
                                f"viral={virality['is_viral']})"
                            )
                            continue

                        # DB保存（重複チェック: 同一URL or 同一テキスト+同一著者）
                        post_url = post_data.get('post_url', '')
                        text = post_data.get('text_content', '')

                        existing = THBuzzPost.objects.filter(
                            author=author, text_content=text,
                        ).first()
                        imp = post_data.get('impressions')

                        if existing:
                            # 既存レコードを更新
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
                            # メディア情報更新（常に上書き）
                            existing.media_type = post_data.get('media_type', '')
                            existing.media_urls = post_data.get('media_urls', [])
                            # 検索キーワードが未設定なら埋める
                            if not existing.search_keyword and kw:
                                existing.search_keyword = kw
                            existing.save()
                            self.stdout.write(f"  更新: @{username} - {text[:30]}")
                        else:
                            raw_json = {'is_pinned': post_data.get('is_pinned', False)}
                            THBuzzPost.objects.create(
                                author=author,
                                post_url=post_url,
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
                            total_count += 1
                            self.stdout.write(f"  保存: @{username} - {text[:30]}")

                        # 投稿者プロフィールを取得（同一実行内で未取得のアカウントのみ）
                        if username not in profile_fetched:
                            profile_fetched.add(username)
                            try:
                                profile = scraper.fetch_author_profile(username)
                                author.display_name = profile.get('display_name') or author.display_name
                                author.bio = profile.get('bio', '')
                                author.followers_count = profile.get('followers_count')
                                author.following_count = profile.get('following_count')
                                author.is_verified = profile.get('is_verified', False)
                                author.profile_pic_url = profile.get('profile_pic_url', '') or author.profile_pic_url
                                author.raw_json = profile
                                author.save()
                                # 成長指標を計算（占い分類も含む）
                                author.update_growth_stats()
                                # フォロワー数が判明したので ER/バズ判定を再計算
                                if author.followers_count:
                                    self._recalc_author_posts(author)
                                # 急成長フィルタ: 候補でないアカウントの投稿を削除
                                if growth_filter and not author.is_concept_candidate:
                                    removed = THBuzzPost.objects.filter(author=author).count()
                                    THBuzzPost.objects.filter(author=author).delete()
                                    total_count = max(total_count - removed, 0)
                                    self.stdout.write(f"  @{username}: 候補外 → 投稿{removed}件を除外")
                            except Exception as e:
                                logger.warning("プロフィール取得失敗 @%s: %s", username, e)

                    # キーワード処理完了ごとに途中経過を保存
                    if job and total_count > 0:
                        try:
                            job.result_count = total_count
                            job.save(update_fields=['result_count'])
                        except Exception:
                            pass

        except Exception as e:
            logger.exception("バズ検索エラー")
            self.stderr.write(f"エラー: {e}")
            error_occurred = e
            error_tb = tb.format_exc()

        finally:
            # ジョブステータスを確実に更新
            if job:
                try:
                    job.refresh_from_db()
                    if error_occurred:
                        # セッション状態も診断して付加
                        error_msg = str(error_occurred)
                        try:
                            session_info = check_session_validity()
                            if not session_info['valid']:
                                error_msg = f"[SESSION] {session_info['message']}\n\n元エラー: {error_msg}"
                        except Exception:
                            pass
                        if total_count > 0:
                            job.status = 'COMPLETED'
                            job.completed_at = timezone.now()
                            job.result_count = total_count
                            job.error_message = f'部分完了（{total_count}件取得後にエラー）: {error_msg}'
                            job.error_traceback = error_tb
                            job.save(update_fields=['status', 'completed_at', 'result_count', 'error_message', 'error_traceback'])
                        else:
                            job.status = 'FAILED'
                            job.completed_at = timezone.now()
                            job.error_message = error_msg
                            job.error_traceback = error_tb
                            job.save(update_fields=['status', 'completed_at', 'error_message', 'error_traceback'])
                    elif job.status == 'RUNNING':
                        job.status = 'COMPLETED'
                        job.completed_at = timezone.now()
                        job.result_count = total_count
                        job.save(update_fields=['status', 'completed_at', 'result_count'])
                except Exception as e:
                    logger.error("ジョブステータス更新失敗 (job_id=%s): %s", job.id, e)

        if error_occurred:
            return

        self.stdout.write(f"\n完了: 新規 {total_count} 件保存")
