# -*- coding: utf-8 -*-
"""投稿文AI生成 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from th.models import THScheduledPost, ThreadsAccount
from th.services.content_generator import (
    STYLE_PRESETS, TOPIC_PRESETS, generate_post,
)

logger = logging.getLogger(__name__)


@staff_member_required
def content_generator(request):
    """投稿文生成画面"""
    accounts = ThreadsAccount.objects.filter(is_active=True)
    context = {
        'title': '投稿文AI生成',
        'topic_presets': TOPIC_PRESETS,
        'style_presets': STYLE_PRESETS,
        'accounts': accounts,
    }
    return render(request, 'admin/console/content_generator.html', context)


@staff_member_required
@require_POST
def content_generate_api(request):
    """投稿文生成 API（Ajax）"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    topic = data.get('topic', '')
    style = data.get('style', 'casual')
    character_desc = data.get('character_desc', '')
    reference_posts = data.get('reference_posts', [])
    max_length = int(data.get('max_length', 500))
    count = min(int(data.get('count', 3)), 5)

    if not topic:
        return JsonResponse({'error': 'トピックを指定してください'}, status=400)

    result = generate_post(
        topic=topic,
        style=style,
        character_desc=character_desc,
        reference_posts=reference_posts if reference_posts else None,
        max_length=max_length,
        count=count,
    )
    return JsonResponse(result)


@staff_member_required
@require_POST
def content_schedule_api(request):
    """生成した投稿を予約投稿に追加 API"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    body = data.get('body', '').strip()
    scheduled_at_str = data.get('scheduled_at', '')
    account_id = data.get('account_id')

    if not body:
        return JsonResponse({'error': '投稿本文が空です'}, status=400)
    if not scheduled_at_str:
        return JsonResponse({'error': '予約日時を指定してください'}, status=400)

    scheduled_at = parse_datetime(scheduled_at_str)
    if not scheduled_at:
        return JsonResponse({'error': '日時の形式が不正です'}, status=400)

    if account_id:
        try:
            account = ThreadsAccount.objects.get(pk=account_id, is_active=True)
        except ThreadsAccount.DoesNotExist:
            return JsonResponse({'error': 'アカウントが見つかりません'}, status=404)
    else:
        account = ThreadsAccount.objects.filter(is_active=True).first()
        if not account:
            return JsonResponse({'error': 'アクティブなThreadsアカウントがありません'}, status=400)

    post = THScheduledPost.objects.create(
        account=account,
        title=body[:50],
        topic='ai_generated',
        body=body,
        scheduled_at=scheduled_at,
        status=THScheduledPost.Status.DRAFT,
        created_by=request.user,
    )

    return JsonResponse({
        'ok': True,
        'post_id': post.pk,
        'message': f'予約投稿(ID:{post.pk})を下書きとして作成しました',
    })
