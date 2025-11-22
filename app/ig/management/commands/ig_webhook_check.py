# app/ig/management/commands/ig_webhook_check.py
from django.core.management.base import BaseCommand
from django.conf import settings
from app.console.utils import meta as metaapi
from ig.models import InstagramBusinessAccount as IBA

def _app_token(app_id: str) -> str:
    """
    app_id に対応する app secret を環境設定から頑張って見つける
    （META_APP_* / META_IG_APP_* / IG_APP_* のいずれでもOK）
    """
    if str(app_id) == str(getattr(settings, "META_APP_ID", "")):
        secret = getattr(settings, "META_APP_SECRET", "")
    else:
        # 互換キーも順に探索
        secret = (
            getattr(settings, "META_IG_APP_SECRET", "") or
            getattr(settings, "IG_APP_SECRET", "") or
            getattr(settings, "META_APP_SECRET", "")
        )
    return f"{app_id}|{secret}"

def _list_subscriptions(app_id: str) -> dict:
    try:
        j = metaapi.api_get(f"{app_id}/subscriptions",
                            params={"access_token": _app_token(app_id)})
        return j or {"data": []}
    except Exception as e:
        return {"data": [], "error": str(e)}

class Command(BaseCommand):
    help = "Check Instagram webhook subscription (app-level) and update IBA.webhook_subscribed"

    def handle(self, *args, **opts):
        # 対象アプリIDの候補（存在するものだけ使う）
        app_ids = []
        for key in ("META_APP_ID", "META_IG_APP_ID", "IG_APP_ID"):
            v = getattr(settings, key, None)
            if v:
                app_ids.append(str(v))
        app_ids = list(dict.fromkeys(app_ids))  # 重複除去

        active = False
        details = []

        for aid in app_ids:
            j = _list_subscriptions(aid)
            data = j.get("data", [])
            # fields を見やすく
            entries = [
                {"object": d.get("object"), "fields": d.get("fields", [])}
                for d in data
            ]
            details.append({"app_id": aid, "entries": entries, "error": j.get("error")})
            if any(d.get("object") == "instagram" for d in data):
                active = True

        self.stdout.write(self.style.SUCCESS(f"active={active} details={details}"))

        # アプリ単位の購読状態を、全 IBA に反映（要件どおり：一括）
        updated = IBA.objects.update(webhook_subscribed=active)
        self.stdout.write(self.style.SUCCESS(f"updated {updated} records"))
