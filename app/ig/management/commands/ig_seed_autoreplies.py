from django.core.management.base import BaseCommand, CommandError
from ig.models import InstagramBusinessAccount, IGAutoReplyTemplate

# name をそのままテンプレ名に使う
TEMPLATES = {
    "DM:初回あいさつ": "ご連絡ありがとうございます！こちらで順次ご案内いたします。",
    "DM:不明メッセージ": "内容を確認できませんでした。キーワードを入れて再送してください。",
    "コメント:お礼":   "コメントありがとうございます！引き続きよろしくお願いします。",
}

class Command(BaseCommand):
    help = "IG自動返信テンプレの初期投入（引数: ig_business_id）"

    def add_arguments(self, parser):
        parser.add_argument("ig_business_id")

    def handle(self, ig_business_id, *args, **opts):
        try:
            iba = InstagramBusinessAccount.objects.get(ig_business_id=ig_business_id)
        except InstagramBusinessAccount.DoesNotExist:
            raise CommandError(f"InstagramBusinessAccount not found: {ig_business_id}")

        created = 0
        for name, body in TEMPLATES.items():
            tpl, was_created = IGAutoReplyTemplate.objects.get_or_create(
                account=iba,
                name=name,
                defaults={"body": body},
            )
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"seeded={created} for IG @{iba.username} (id={iba.ig_business_id})"
        ))
