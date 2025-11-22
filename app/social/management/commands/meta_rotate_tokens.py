# app/social/management/commands/meta_rotate_tokens.py
from __future__ import annotations
from django.core.management.base import BaseCommand
from ig.models import InstagramBusinessAccount
from social.services.meta_tokens import ensure_fresh_page_token_by_igbiz, debug_token

class Command(BaseCommand):
    help = "Metaトークンを期限前に自動更新（IGビジネスに紐づくPageトークンを点検・更新）"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        cnt = 0
        for acc in InstagramBusinessAccount.objects.all():
            igbiz = str(acc.ig_business_id)
            if not igbiz:
                continue
            try:
                # 現状トークンが有効でも7日未満なら ensure_fresh... 内で更新される
                if dry:
                    self.stdout.write(f"[DRY] check {igbiz}")
                    continue
                tok, pid = ensure_fresh_page_token_by_igbiz(igbiz)
                # ついでに有効性を出力
                info = debug_token(tok)
                self.stdout.write(f"Refreshed {igbiz} (page {pid}) valid={info.get('data',{}).get('is_valid')} expires={info.get('data',{}).get('expires_at')}")
                cnt += 1
            except Exception as e:
                self.stderr.write(f"[WARN] {igbiz}: {e}")
        self.stdout.write(self.style.SUCCESS(f"done. refreshed={cnt}"))
