# app/ig/management/commands/ig_webhook_subscribe.py
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from urllib.parse import urljoin
import os
from app.console.utils import meta as metaapi

def _app_token(app_id: str) -> str:
    secret = (
        getattr(settings, "META_APP_SECRET", "") or
        getattr(settings, "IG_APP_SECRET", "") or
        getattr(settings, "META_IG_APP_SECRET", "")
    )
    if not (app_id and secret):
        raise CommandError("META_APP_ID / *APP_SECRET が未設定です。")
    return f"{app_id}|{secret}"

def _public_origin() -> str:
    # 環境変数優先 → settings → 最後は例外
    for key in ("PUBLIC_ORIGIN", "META_PUBLIC_BASE_URL"):
        v = os.getenv(key)
        if v:
            return v.rstrip("/")
    try:
        if settings.CSRF_TRUSTED_ORIGINS:
            return settings.CSRF_TRUSTED_ORIGINS[0].rstrip("/")
    except Exception:
        pass
    raise CommandError("公開オリジンが不明です。PUBLIC_ORIGIN か META_PUBLIC_BASE_URL を設定してください。")

class Command(BaseCommand):
    help = "Instagram Webhooks を購読登録（comments/messages/mentions）"

    def add_arguments(self, parser):
        parser.add_argument("--callback", help="絶対URL。未指定なら PUBLIC_ORIGIN などから自動組み立て")
        parser.add_argument("--fields", default="comments,messages,mentions",
                            help="カンマ区切り。既定: comments,messages,mentions")
        parser.add_argument("--app-id", default=None, help="使う App ID（既定: settings.META_APP_ID）")
        parser.add_argument("--verify-token", default=None,
                            help="既定: settings.META_WEBHOOK_VERIFY_TOKEN")

    def handle(self, *args, **opts):
        app_id = opts["app_id"] or getattr(settings, "META_APP_ID", None)
        if not app_id:
            raise CommandError("META_APP_ID が未設定です。")
        verify_token = opts["verify_token"] or getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "")
        if not verify_token:
            raise CommandError("META_WEBHOOK_VERIFY_TOKEN が未設定です。")

        callback = opts["callback"] or urljoin(_public_origin() + "/", "oauth/meta/webhook/")
        if not callback.startswith("http"):
            raise CommandError(f"callback_url が絶対URLではありません: {callback}")

        fields = [s.strip() for s in opts["fields"].split(",") if s.strip()]

        payload = {
            "object": "instagram",
            "callback_url": callback,
            "verify_token": verify_token,
            "fields": ",".join(fields),
            "access_token": _app_token(str(app_id)),
        }

        resp = metaapi.api_post(f"{app_id}/subscriptions", data=payload)
        self.stdout.write(self.style.SUCCESS(f"subscribe -> {resp}"))

