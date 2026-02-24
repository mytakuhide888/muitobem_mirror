# -*- coding: utf-8 -*-
"""Instagram投稿パフォーマンス分析 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ig.models import IGPost, IGPostInsight, InstagramBusinessAccount

logger = logging.getLogger(__name__)


@staff_member_required
def post_analytics(request):
    """投稿パフォーマンス分析画面"""
    accounts = InstagramBusinessAccount.objects.filter(is_active=True)
    selected_account_id = request.GET.get("account_id")
    selected_account = None
    posts_data = []

    if selected_account_id:
        try:
            selected_account = InstagramBusinessAccount.objects.get(pk=selected_account_id, is_active=True)
        except InstagramBusinessAccount.DoesNotExist:
            pass

    if selected_account:
        posts = IGPost.objects.filter(account=selected_account).order_by("-posted_at")[:30]
        for post in posts:
            latest_insight = post.insights.first()
            posts_data.append({
                "id": post.pk,
                "external_post_id": post.external_post_id,
                "caption": (post.caption or "")[:80],
                "media_type": post.media_type,
                "posted_at": post.posted_at.strftime("%m/%d %H:%M") if post.posted_at else "",
                "like_count": post.like_count or 0,
                "impressions": latest_insight.impressions if latest_insight else None,
                "reach": latest_insight.reach if latest_insight else None,
                "er": latest_insight.er if latest_insight else None,
                "saved": latest_insight.saved if latest_insight else None,
            })

    context = {
        "title": "投稿パフォーマンス分析",
        "accounts": accounts,
        "selected_account": selected_account,
        "posts_data_json": json.dumps(posts_data, ensure_ascii=False),
        "posts_count": len(posts_data),
    }
    return render(request, "admin/console/post_analytics.html", context)


@staff_member_required
@require_POST
def post_insights_refresh_api(request):
    """投稿インサイト一括更新 API"""
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
        from ig.services.insights_fetcher import refresh_all_post_insights
        count = refresh_all_post_insights(account)
        return JsonResponse({"ok": True, "updated": count, "message": f"{count}件のインサイトを更新しました"})
    except Exception as e:
        logger.exception("インサイト更新失敗")
        return JsonResponse({"error": str(e)}, status=500)
