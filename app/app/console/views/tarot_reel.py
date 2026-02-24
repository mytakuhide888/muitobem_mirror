# -*- coding: utf-8 -*-
"""タロットリール生成 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from ig.models import InstagramBusinessAccount, IGScheduledPost
from ig.services.tarot_generator import THEME_PRESETS

logger = logging.getLogger(__name__)


@staff_member_required
def tarot_reel_gen(request):
    """タロットリール生成画面"""
    accounts = InstagramBusinessAccount.objects.filter(is_active=True)
    context = {
        "title": "タロットリール生成",
        "theme_presets": THEME_PRESETS,
        "accounts": accounts,
    }
    return render(request, "admin/console/tarot_reel_gen.html", context)


@staff_member_required
@require_POST
def tarot_generate_api(request):
    """タロット投稿文生成 API（Ajax）"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    theme = data.get("theme", "overall")
    style = data.get("style", "casual")
    character_desc = data.get("character_desc", "")

    from ig.services.tarot_generator import generate_tarot_options
    result = generate_tarot_options(theme=theme, style=style, character_desc=character_desc)
    return JsonResponse(result)


@staff_member_required
@require_POST
def tarot_schedule_api(request):
    """生成したタロット投稿を予約投稿に追加 API"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    account_id = data.get("account_id")
    caption = data.get("caption", "").strip()
    scheduled_at_str = data.get("scheduled_at", "")

    if not caption:
        return JsonResponse({"error": "キャプションが空です"}, status=400)
    if not scheduled_at_str:
        return JsonResponse({"error": "予約日時を指定してください"}, status=400)
    if not account_id:
        return JsonResponse({"error": "アカウントを選択してください"}, status=400)

    scheduled_at = parse_datetime(scheduled_at_str)
    if not scheduled_at:
        return JsonResponse({"error": "日時の形式が不正です"}, status=400)

    try:
        account = InstagramBusinessAccount.objects.get(pk=account_id, is_active=True)
    except InstagramBusinessAccount.DoesNotExist:
        return JsonResponse({"error": "アカウントが見つかりません"}, status=404)

    post = IGScheduledPost.objects.create(
        account=account,
        title=caption[:50],
        topic="tarot_reel",
        body=caption,
        scheduled_at=scheduled_at,
        status=IGScheduledPost.Status.DRAFT,
        created_by=request.user,
    )

    return JsonResponse({
        "ok": True,
        "post_id": post.pk,
        "message": f"予約投稿(ID:{post.pk})を下書きとして作成しました",
    })
