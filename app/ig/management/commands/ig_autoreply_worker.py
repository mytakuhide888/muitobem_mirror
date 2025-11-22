from django.core.management.base import BaseCommand
from django.utils import timezone
from ig.models import IGWebhookEvent, InstagramBusinessAccount, IGAutoReplyTemplate
from django.db import transaction

class Command(BaseCommand):
    help = "Process pending IG webhook events and mark as handled. (reply stub)"

    def handle(self, *args, **opts):
        qs = IGWebhookEvent.objects.filter(handled=False).order_by("id")[:50]
        if not qs.exists():
            self.stdout.write("no pending")
            return

        # 例: アカウント別にまとめてテンプレ返信する“ふり”をして handled にする
        with transaction.atomic():
            for ev in qs:
                kind = ev.event_type  # 'comments' or 'messages' など
                try:
                    iba = InstagramBusinessAccount.objects.get(ig_business_id=ev.ig_business_id)
                except InstagramBusinessAccount.DoesNotExist:
                    iba = None

                # ここで実際の返信APIを呼ぶ（stub）
                # 返信本文はテンプレから:
                #   name='DM:初回あいさつ' / 'コメント:お礼' などを選択
                #   tpl = IGAutoReplyTemplate.objects.filter(account=iba, name='DM:初回あいさつ').first()

                ev.handled = True
                ev.handled_at = timezone.now()
                ev.save(update_fields=["handled","handled_at"])

        self.stdout.write(self.style.SUCCESS(f"handled {qs.count()} events"))
