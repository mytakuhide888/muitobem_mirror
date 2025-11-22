# app/console/views/webhook_setup.py
import os, requests
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib import messages

APP_ID = os.getenv("META_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET")
SITE_BASE = os.getenv("SITE_BASE", "").rstrip("/")
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "dev-verify-token")

def _app_token():
    r = requests.get("https://graph.facebook.com/oauth/access_token", params={
        "client_id": APP_ID, "client_secret": APP_SECRET, "grant_type": "client_credentials"
    }, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

@staff_member_required
def webhook_setup(request):
    cb = f"{SITE_BASE}/webhook/meta/instagram/"
    defaults = ["comments", "mentions", "messages"]  # 任意
    return render(request, "admin/console/webhook_setup.html", {
        "callback_url": cb,
        "verify_token": VERIFY_TOKEN,
        "fields_default": defaults,
    })

@staff_member_required
@require_POST
def webhook_subscribe(request):
    cb = f"{SITE_BASE}/webhook/meta/instagram/"
    fields = request.POST.getlist("fields")  # ["comments","mentions",...]
    token = _app_token()
    # App レベルの subscription: object=instagram
    r = requests.post(f"https://graph.facebook.com/{APP_ID}/subscriptions", data={
        "object": "instagram",
        "callback_url": cb,
        "verify_token": VERIFY_TOKEN,
        "fields": ",".join(fields),
        "include_values": "true",
        "access_token": token
    }, timeout=20)
    ok = r.status_code in (200, 201)
    messages.success(request, f"Webhooks 購読 {'成功' if ok else '失敗'}: {r.text[:500]}")
    return render(request, "admin/console/webhook_setup_result.html", {"ok": ok, "resp": r.text})
