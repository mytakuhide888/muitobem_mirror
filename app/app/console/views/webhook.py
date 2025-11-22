# app/console/views/webhook.py
import json, os
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ig.models import IGWebhookEvent

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "dev-verify-token")

@require_http_methods(["GET","POST"])
@csrf_exempt
def instagram_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge or "")
        return HttpResponse(status=403)

    # POST
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {"raw": request.body.decode("utf-8", "ignore")}
    # 必要に応じて IGWebhookEvent へ保存（最低限）
    IGWebhookEvent.objects.create(summary=json.dumps(payload)[:5000])
    return HttpResponse("EVENT_RECEIVED")
