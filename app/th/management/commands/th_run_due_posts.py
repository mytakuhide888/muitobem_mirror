import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from social.services.threads_api import ThreadsApiClient, ThreadsCredentials, ThreadsApiError
from th.models import THScheduledPost

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Threads 予約投稿の実行（--dry-run で送信せずログだけ）"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        now = timezone.now()

        qs = THScheduledPost.objects.select_related("account").filter(
            status=THScheduledPost.Status.APPROVED,
            scheduled_at__lte=now,
        ).order_by("scheduled_at")

        cnt = qs.count()
        self.stdout.write(f"due: {cnt}")
        if not cnt:
            return

        for post in qs:
            msg = f'[id={post.id}] @{post.account} at {post.scheduled_at.isoformat()} "{(post.body or "")[:40]}"'
            if dry:
                self.stdout.write("DRY-RUN: " + msg)
                continue

            ok, err = self._post_to_threads(post)

            with transaction.atomic():
                post.status = THScheduledPost.Status.SENT if ok else THScheduledPost.Status.FAILED
                post.save(update_fields=["status"])
                self.stdout.write(("SENT: " if ok else "FAILED: ") + msg + ("" if ok else f" :: {err}"))

    def _post_to_threads(self, post):
        """
        実際の Threads 投稿処理。成功で (True, id)、失敗で (False, error) を返す。
        """
        try:
            account = post.account
            user_id = getattr(account, "threads_user_id", "") or getattr(account, "external_id", "")
            token = getattr(account, "access_token", "") or getattr(settings, "THREADS_USER_ACCESS_TOKEN", "")
            if not user_id or not token:
                return False, "missing user_id or access_token"

            client = ThreadsApiClient(ThreadsCredentials(user_id=user_id, access_token=token))
            creation_id = client.create_text_container(text=post.body or "")
            published_id = client.publish_container(creation_id=creation_id)
            # 外部投稿IDを保存（インサイト取得で使用）
            if published_id:
                post.external_post_id = str(published_id)
                post.save(update_fields=["external_post_id"])
            return True, published_id
        except ThreadsApiError as e:
            logger.warning("Threads API error: %s", e)
            return False, str(e)
        except Exception as e:
            logger.exception("Unexpected error posting to Threads")
            return False, str(e)
