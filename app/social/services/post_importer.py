"""投稿データ取り込みのスタブ"""
from datetime import datetime
from .threads_api import fetch_posts as threads_fetch
from .instagram_api import fetch_posts as instagram_fetch
from ..models import Post, Platform, ThreadsAccount, InstagramAccount
from django.contrib.contenttypes.models import ContentType


def full_import() -> int:
    """全件取り込み"""
    count = 0
    for account in ThreadsAccount.objects.all():
        posts = threads_fetch('', account.threads_user_id)
        count += _save_posts(account, Platform.THREADS, posts)
    for account in InstagramAccount.objects.all():
        posts = instagram_fetch('', account.instagram_user_id)
        count += _save_posts(account, Platform.INSTAGRAM, posts)
    return count


def sync_latest() -> int:
    """差分取り込み"""
    # ダミーでは full_import と同じ動作
    return full_import()


def _save_posts(account, platform, posts) -> int:
    ct = ContentType.objects.get_for_model(account)
    count = 0
    for p in posts:
        Post.objects.update_or_create(
            external_post_id=p['id'],
            defaults={
                'platform': platform,
                'content_type': ct,
                'object_id': account.id,
                'posted_at': datetime.fromisoformat(p['posted_at']),
                'content': p['content'],
                'like_count': p['like_count'],
                'view_count': p.get('view_count'),
                'raw_json': p,
            }
        )
        count += 1
    return count
