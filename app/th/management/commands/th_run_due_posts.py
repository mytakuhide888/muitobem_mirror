from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from th.models import THScheduledPost  # ← ここが大事（以前の ScheduledPost ではない）

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

            # --- 実投稿（Threads API 呼び出し部） ---
            ok, err = self._post_to_threads(post)
            # -------------------------------------

            with transaction.atomic():
                if ok:
                    post.status = THScheduledPost.Status.SENT
                else:
                    post.status = THScheduledPost.Status.FAILED
                post.save(update_fields=["status"])
                self.stdout.write(("SENT: " if ok else "FAILED: ") + msg + ("" if ok else f" :: {err}"))

    def _post_to_threads(self, post):
        """
        実際の Threads 投稿処理をここに実装。
        ひとまず成功した体で True を返す。エラー時は (False, '理由') を返す。
        """
        try:
            # 例：
            # token = post.account.access_token など取得し API 呼び出し
            # ...
            return True, None
        except Exception as e:
            return False, str(e)
