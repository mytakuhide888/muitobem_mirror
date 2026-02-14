# -*- coding: utf-8 -*-
"""
既存の THBuzzAuthor に対して占い属性分類を一括実行する Management Command。
"""
from django.core.management.base import BaseCommand
from th.models import THBuzzAuthor
from th.services.fortune_classifier import update_author_fortune_classification


class Command(BaseCommand):
    help = '全ての THBuzzAuthor に対して占い属性分類を一括実行する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='DB更新せずに結果を表示のみ',
        )
        parser.add_argument(
            '--limit', type=int, default=0,
            help='処理件数を制限（0=全件）',
        )
        parser.add_argument(
            '--min-posts', type=int, default=0,
            help='指定件数以上の投稿があるアカウントのみ処理',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        min_posts = options['min_posts']

        qs = THBuzzAuthor.objects.all().order_by('-updated_at')

        if min_posts > 0:
            qs = qs.filter(total_post_count__gte=min_posts)

        if limit > 0:
            qs = qs[:limit]

        total = qs.count() if limit == 0 else min(limit, qs.count())
        self.stdout.write(f'対象: {total} 件')

        fortune_count = 0
        excluded_count = 0

        for i, author in enumerate(qs.iterator(), 1):
            result = update_author_fortune_classification(author)

            if result['fortune_relevance_score'] > 0:
                fortune_count += 1

            if result['auto_exclude']:
                excluded_count += 1

            if not dry_run:
                update_fields = [
                    'fortune_relevance_score', 'genre_tags',
                    'monetization_signals', 'auto_excluded_reason',
                ]
                if result['auto_exclude'] and author.is_excluded:
                    update_fields.append('is_excluded')
                author.save(update_fields=update_fields)

            # 進捗表示（100件ごと）
            if i % 100 == 0 or i == total:
                self.stdout.write(
                    f'  [{i}/{total}] '
                    f'占い関連: {fortune_count}, 自動対象外: {excluded_count}'
                )

            # 高スコアのログ
            if result['fortune_relevance_score'] >= 30:
                tags = ', '.join(result['genre_tags'][:5])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ★ @{author.username}: '
                        f'スコア={result["fortune_relevance_score"]:.1f} '
                        f'ジャンル=[{tags}]'
                    )
                )

        mode_str = '(dry-run)' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n完了 {mode_str}: {total}件処理, '
            f'占い関連: {fortune_count}件, 自動対象外: {excluded_count}件'
        ))
