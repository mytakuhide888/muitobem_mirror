# -*- coding: utf-8 -*-
"""Instagram投稿管理 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ig.models import InstagramBusinessAccount, IGPost

logger = logging.getLogger(__name__)


@staff_member_required
def ig_post_manager(request):
    """Instagram投稿管理画面"""
    accounts = InstagramBusinessAccount.objects.filter(is_active=True)
    posts = IGPost.objects.select_related("account").order_by("-posted_at")[:50]
    context = {
        "title": "Instagram投稿管理",
        "accounts": accounts,
        "posts": posts,
    }
    return render(request, "admin/console/ig_post_manager.html", context)


@staff_member_required
@require_POST
def ig_post_api(request):
    """Instagram投稿作成 API（Ajax）"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    account_id = data.get("account_id")
    caption = data.get("caption", "").strip()
    media_type = data.get("media_type", "IMAGE")
    media_url = data.get("media_url", "").strip()

    if not caption:
        return JsonResponse({"error": "キャプションが空です"}, status=400)
    if media_type in ("IMAGE", "REELS") and not media_url:
        return JsonResponse({"error": "メディアURLが必要です"}, status=400)
    if not account_id:
        return JsonResponse({"error": "アカウントを選択してください"}, status=400)

    try:
        account = InstagramBusinessAccount.objects.get(pk=account_id, is_active=True)
    except InstagramBusinessAccount.DoesNotExist:
        return JsonResponse({"error": "アカウントが見つかりません"}, status=404)

    try:
        from ig.services.ig_poster import post_image, post_reel
        if media_type == "REELS":
            post = post_reel(account, caption, media_url)
        else:
            post = post_image(account, caption, media_url)
        return JsonResponse({
            "ok": True,
            "post_id": post.pk,
            "external_id": post.external_post_id,
            "message": f"投稿しました (ID: {post.external_post_id})",
        })
    except Exception as e:
        logger.exception("IG投稿失敗")
        return JsonResponse({"error": str(e)}, status=500)


@staff_member_required
@require_POST
def ig_posts_sync_api(request):
    """IGから投稿一覧を同期 API（Ajax）"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    account_id = data.get("account_id")
    if not account_id:
        return JsonResponse({"error": "アカウントを選択してください"}, status=400)

    try:
        account = InstagramBusinessAccount.objects.get(pk=account_id, is_active=True)
    except InstagramBusinessAccount.DoesNotExist:
        return JsonResponse({"error": "アカウントが見つかりません"}, status=404)

    try:
        from ig.services.ig_poster import sync_posts
        count = sync_posts(account)
        return JsonResponse({"ok": True, "new_posts": count, "message": f"{count}件の新規投稿を同期しました"})
    except Exception as e:
        logger.exception("IG同期失敗")
        return JsonResponse({"error": str(e)}, status=500)
