"""簡易スケジューラ"""
from django.utils import timezone
from ..models import ScheduledPost, Post, Platform
from .threads_api import post_thread
from .instagram_api import post_instagram
from django.contrib.contenttypes.models import ContentType


def run_once():
    """承認済みの予約投稿をチェックして送信する"""
    now = timezone.now()
    targets = ScheduledPost.objects.filter(status=ScheduledPost.Status.APPROVED, scheduled_at__lte=now)
    for sp in targets:
        if sp.platform == Platform.THREADS:
            post_thread('', '', sp.body)
        else:
            post_instagram('', '', sp.body)
        Post.objects.create(
            platform=sp.platform,
            content_type=sp.content_type,
            object_id=sp.object_id,
            external_post_id=f'dummy-{sp.id}',
            posted_at=now,
            content=sp.body,
            like_count=0,
            raw_json={},
        )
        sp.status = ScheduledPost.Status.SENT
        sp.save()
