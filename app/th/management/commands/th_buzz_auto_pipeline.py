# -*- coding: utf-8 -*-
"""
自動巡回パイプライン
登録キーワードで一括巡回 → 深掘りスキャン → 要注目フラグ設定を自動実行する。

使用例:
  python manage.py th_buzz_auto_pipeline
  python manage.py th_buzz_auto_pipeline --dry-run
  python manage.py th_buzz_auto_pipeline --growth-threshold 50 --fortune-threshold 20
"""
import logging
import os
import traceback as tb
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from th.models import THBuzzAuthor, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import (
    ThreadsBuzzScraper, ViralityDetector, check_session_validity,
)

logger = logging.getLogger(__name__)

# デフォルトの巡回キーワード
DEFAULT_KEYWORDS = [
    '占い', 'タロット', '霊視', 'ツインレイ', '金運占い',
    '恋愛占い', 'スピリチュアル', '四柱推命', '数秘術',
    'パワーストーン', '波動修正',
]

# 深掘り対象の投稿数閾値
POSTS_THRESHOLD = 3


class Command(BaseCommand):
    help = "自動巡回パイプライン: キーワード巡回 → 深掘りスキャン → 要注目フラグ設定"

    def add_arguments(self, parser):
        parser.add_argument(
            '-k', '--keywords', nargs='+', default=None,
            help=f'検索キーワード（未指定時はデフォルト{len(DEFAULT_KEYWORDS)}語）',
        )
        parser.add_argument(
            '--growth-threshold', type=float, default=100.0,
            help='要注目とする成長スコアの閾値（デフォルト: 100）',
        )
        parser.add_argument(
            '--fortune-threshold', type=float, default=30.0,
            help='要注目とする占い適合スコアの閾値（デフォルト: 30）',
        )
        parser.add_argument(
            '--max-profile-fetch', type=int, default=30,
            help='キーワード巡回で取得するプロフィールの最大数（デフォルト: 30）',
        )
        parser.add_argument(
            '--max-deep-scan', type=int, default=15,
            help='深掘りスキャンするアカウント数の上限（デフォルト: 15）',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='実際のスクレイピングを行わずフラグ設定のみ実行',
        )

    def handle(self, *args, **opts):
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        keywords = opts['keywords'] or DEFAULT_KEYWORDS
        growth_threshold = opts['growth_threshold']
        fortune_threshold = opts['fortune_threshold']
        max_profile_fetch = opts['max_profile_fetch']
        max_deep_scan = opts['max_deep_scan']
        dry_run = opts['dry_run']

        now = timezone.now()
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== 自動巡回パイプライン開始 [{now:%Y-%m-%d %H:%M}] ==="
        ))

        stats = {
            'keywords_scanned': 0,
            'new_posts_found': 0,
            'new_authors_found': 0,
            'profiles_fetched': 0,
            'deep_scanned': 0,
            'attention_set': 0,
            'attention_cleared': 0,
            'errors': [],
        }

        if dry_run:
            self.stdout.write(self.style.WARNING(">>> DRY RUN モード（スクレイピングをスキップ）"))
            self._update_attention_flags(growth_threshold, fortune_threshold, stats)
            self._print_summary(stats)
            return

        # セッション確認
        session = check_session_validity()
        if not session['valid']:
            self.stdout.write(self.style.ERROR(
                f"セッション無効: {session['message']}\n"
                "th_buzz_login を実行してセッションを更新してください。"
            ))
            return

        # ─── Phase 1: キーワード巡回 ───
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n--- Phase 1: キーワード巡回 ({len(keywords)}語) ---"
        ))

        try:
            with ThreadsBuzzScraper() as scraper:
                # Phase 1: キーワード巡回
                self._phase_keyword_scan(scraper, keywords, max_profile_fetch, stats)

                # Phase 2: 深掘りスキャン
                self._phase_deep_scan(scraper, max_deep_scan, fortune_threshold, stats)

        except Exception as e:
            msg = f"スクレイパーエラー: {e}"
            logger.error(msg, exc_info=True)
            stats['errors'].append(msg)
            self.stdout.write(self.style.ERROR(msg))

        # ─── Phase 3: 要注目フラグ更新 ───
        self._update_attention_flags(growth_threshold, fortune_threshold, stats)

        # ─── 結果サマリ ───
        self._print_summary(stats)

    def _phase_keyword_scan(self, scraper, keywords, max_profile_fetch, stats):
        """Phase 1: キーワード巡回"""
        profiles_fetched = 0
        new_author_usernames = set()

        for kw in keywords:
            if profiles_fetched >= max_profile_fetch:
                self.stdout.write(f"  プロフィール取得上限({max_profile_fetch})に到達、巡回終了")
                break

            self.stdout.write(f"  検索中: 「{kw}」 ... ", ending='')
            stats['keywords_scanned'] += 1

            try:
                posts = scraper.search_keyword(kw, exclude_replies=True, sort_order='recent')
                self.stdout.write(f"{len(posts)}件")
            except Exception as e:
                msg = f"検索エラー [{kw}]: {e}"
                stats['errors'].append(msg)
                self.stdout.write(self.style.ERROR(msg))
                continue

            for post_data in posts:
                username = post_data.get('username', '')
                if not username:
                    continue

                # 投稿を保存
                author, created = THBuzzAuthor.objects.get_or_create(
                    username=username,
                    defaults={
                        'display_name': post_data.get('display_name', ''),
                        'bio': post_data.get('bio', ''),
                        'followers_count': post_data.get('followers_count'),
                        'is_verified': post_data.get('is_verified', False),
                    }
                )

                # 投稿を保存（重複チェック）
                post_url = post_data.get('post_url', '')
                if post_url and not THBuzzPost.objects.filter(post_url=post_url).exists():
                    virality = ViralityDetector.is_viral(
                        post_data, author.followers_count or 0
                    )
                    THBuzzPost.objects.create(
                        author=author,
                        post_url=post_url,
                        text_content=post_data.get('text_content', ''),
                        like_count=post_data.get('like_count', 0),
                        reply_count=post_data.get('reply_count', 0),
                        repost_count=post_data.get('repost_count', 0),
                        impressions=post_data.get('impressions'),
                        engagement_rate=virality.get('engagement_rate'),
                        engagement_score=virality.get('engagement_score'),
                        is_viral=virality.get('is_viral', False),
                        search_keyword=kw,
                        posted_at=post_data.get('posted_at'),
                        raw_json=post_data.get('raw_json', {}),
                        media_type=post_data.get('media_type', ''),
                        media_urls=post_data.get('media_urls', []),
                    )
                    stats['new_posts_found'] += 1

                if created:
                    new_author_usernames.add(username)
                    stats['new_authors_found'] += 1

        # 新規アカウントのプロフィール取得
        for username in list(new_author_usernames)[:max_profile_fetch - profiles_fetched]:
            try:
                author = THBuzzAuthor.objects.get(username=username)
                if author.is_excluded:
                    continue

                profile = scraper.fetch_author_profile(username)
                author.display_name = profile.get('display_name') or author.display_name
                author.bio = profile.get('bio', '')
                author.followers_count = profile.get('followers_count')
                author.following_count = profile.get('following_count')
                author.is_verified = profile.get('is_verified', False)
                author.profile_pic_url = profile.get('profile_pic_url', '') or author.profile_pic_url
                old_raw = author.raw_json or {}
                merged_profile = dict(profile or {})
                if not merged_profile.get('joined_at') and old_raw.get('joined_at'):
                    merged_profile['joined_at'] = old_raw.get('joined_at')
                author.raw_json = merged_profile
                author.save()
                author.update_growth_stats()

                profiles_fetched += 1
                stats['profiles_fetched'] += 1
                self.stdout.write(f"    プロフィール取得: @{username} (F:{author.followers_count})")

            except Exception as e:
                msg = f"プロフィール取得エラー [@{username}]: {e}"
                stats['errors'].append(msg)
                logger.warning(msg)

    def _phase_deep_scan(self, scraper, max_deep_scan, fortune_threshold, stats):
        """Phase 2: 投稿不足アカウントの深掘りスキャン"""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n--- Phase 2: 深掘りスキャン (上限{max_deep_scan}件) ---"
        ))

        # 深掘り対象: 占い適合スコアがある程度あり、投稿が少ないアカウント
        targets = THBuzzAuthor.objects.filter(
            is_excluded=False,
            followers_count__isnull=False,
            followers_count__gt=0,
        ).filter(
            Q(fortune_relevance_score__gte=fortune_threshold) |
            Q(fortune_relevance_score__isnull=True, bio__icontains='占')
        ).filter(
            Q(total_post_count__lte=POSTS_THRESHOLD) |
            Q(total_post_count__isnull=True)
        ).order_by('-growth_score')[:max_deep_scan]

        count = targets.count()
        self.stdout.write(f"  対象: {count}件")

        for i, author in enumerate(targets):
            try:
                self.stdout.write(
                    f"  [{i+1}/{count}] @{author.username} "
                    f"(F:{author.followers_count}, posts:{author.total_post_count or 0})"
                )

                # プロフィール更新
                profile = scraper.fetch_author_profile(author.username)
                author.display_name = profile.get('display_name') or author.display_name
                author.bio = profile.get('bio', '')
                author.followers_count = profile.get('followers_count')
                author.following_count = profile.get('following_count')
                author.is_verified = profile.get('is_verified', False)
                author.profile_pic_url = profile.get('profile_pic_url', '') or author.profile_pic_url
                old_raw = author.raw_json or {}
                merged_profile = dict(profile or {})
                if not merged_profile.get('joined_at') and old_raw.get('joined_at'):
                    merged_profile['joined_at'] = old_raw.get('joined_at')
                author.raw_json = merged_profile
                author.save()

                # 過去投稿取得
                posts = scraper.fetch_author_posts(
                    author.username, max_scrolls=8, exclude_replies=True
                )
                new_count = 0
                for post_data in posts:
                    post_url = post_data.get('post_url', '')
                    if post_url and not THBuzzPost.objects.filter(post_url=post_url).exists():
                        virality = ViralityDetector.is_viral(
                            post_data, author.followers_count or 0
                        )
                        THBuzzPost.objects.create(
                            author=author,
                            post_url=post_url,
                            text_content=post_data.get('text_content', ''),
                            like_count=post_data.get('like_count', 0),
                            reply_count=post_data.get('reply_count', 0),
                            repost_count=post_data.get('repost_count', 0),
                            impressions=post_data.get('impressions'),
                            engagement_rate=virality.get('engagement_rate'),
                            engagement_score=virality.get('engagement_score'),
                            is_viral=virality.get('is_viral', False),
                            search_keyword='[deep_scan]',
                            posted_at=post_data.get('posted_at'),
                            raw_json=post_data.get('raw_json', {}),
                            media_type=post_data.get('media_type', ''),
                            media_urls=post_data.get('media_urls', []),
                        )
                        new_count += 1

                author.update_growth_stats()
                stats['deep_scanned'] += 1
                self.stdout.write(f"    → {new_count}件の新規投稿を取得")

            except Exception as e:
                msg = f"深掘りエラー [@{author.username}]: {e}"
                stats['errors'].append(msg)
                logger.warning(msg)

    def _update_attention_flags(self, growth_threshold, fortune_threshold, stats):
        """Phase 3: 要注目フラグの更新"""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n--- Phase 3: 要注目フラグ更新 "
            f"(成長≧{growth_threshold}, 占い適合≧{fortune_threshold}) ---"
        ))

        now = timezone.now()

        # 条件を満たすアカウントに要注目フラグを設定
        new_attention = THBuzzAuthor.objects.filter(
            is_excluded=False,
            is_attention_needed=False,
            growth_score__gte=growth_threshold,
            fortune_relevance_score__gte=fortune_threshold,
        )
        set_count = new_attention.update(
            is_attention_needed=True,
            attention_set_at=now,
        )
        stats['attention_set'] = set_count

        # 条件を満たさなくなったアカウントのフラグをクリア
        # （ただし分析済みのものはクリアしない）
        stale = THBuzzAuthor.objects.filter(
            is_attention_needed=True,
            is_analyzed=False,
        ).filter(
            Q(growth_score__lt=growth_threshold) |
            Q(growth_score__isnull=True) |
            Q(fortune_relevance_score__lt=fortune_threshold) |
            Q(fortune_relevance_score__isnull=True) |
            Q(is_excluded=True)
        )
        cleared_count = stale.update(is_attention_needed=False)
        stats['attention_cleared'] = cleared_count

        # 現在の要注目数
        total_attention = THBuzzAuthor.objects.filter(
            is_attention_needed=True
        ).count()
        self.stdout.write(
            f"  新規要注目: {set_count}件, クリア: {cleared_count}件, "
            f"現在の合計: {total_attention}件"
        )

    def _print_summary(self, stats):
        """結果サマリの出力"""
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== パイプライン完了 ==="))
        self.stdout.write(f"  キーワード巡回: {stats['keywords_scanned']}語")
        self.stdout.write(f"  新規投稿発見:   {stats['new_posts_found']}件")
        self.stdout.write(f"  新規アカウント: {stats['new_authors_found']}件")
        self.stdout.write(f"  プロフィール取得: {stats['profiles_fetched']}件")
        self.stdout.write(f"  深掘りスキャン: {stats['deep_scanned']}件")
        self.stdout.write(f"  要注目フラグ:   +{stats['attention_set']} / -{stats['attention_cleared']}")

        if stats['errors']:
            self.stdout.write(self.style.ERROR(
                f"\n  エラー: {len(stats['errors'])}件"
            ))
            for err in stats['errors'][:10]:
                self.stdout.write(f"    - {err}")
