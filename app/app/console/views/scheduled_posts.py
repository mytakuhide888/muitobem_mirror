# -*- coding: utf-8 -*-
"""予約投稿管理 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from th.models import THScheduledPost, ThreadsAccount

logger = logging.getLogger(__name__)


@staff_member_required
def scheduled_posts(request):
    """予約投稿一覧画面"""
    status_filter = request.GET.get('status', '')
    qs = THScheduledPost.objects.select_related('account', 'created_by').all()
    if status_filter:
        qs = qs.filter(status=status_filter)

    statuses = THScheduledPost.Status
    counts = {s.value: THScheduledPost.objects.filter(status=s.value).count() for s in statuses}
    accounts = ThreadsAccount.objects.filter(is_active=True)

    context = {
        'title': '予約投稿管理',
        'posts': qs[:200],
        'status_filter': status_filter,
        'statuses': statuses,
        'counts': counts,
        'accounts': accounts,
    }
    return render(request, 'admin/console/scheduled_posts.html', context)


@staff_member_required
@require_POST
def scheduled_post_action_api(request, pk):
    """予約投稿のアクション API（承認/削除/日時変更）"""
    post = get_object_or_404(THScheduledPost, pk=pk)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    action = data.get('action', '')

    if action == 'approve':
        if post.status != THScheduledPost.Status.DRAFT:
            return JsonResponse({'error': '下書き以外は承認できません'}, status=400)
        post.status = THScheduledPost.Status.APPROVED
        post.save(update_fields=['status', 'updated_at'])
        return JsonResponse({'ok': True, 'message': '承認しました'})

    elif action == 'delete':
        post.delete()
        return JsonResponse({'ok': True, 'message': '削除しました'})

    elif action == 'reschedule':
        new_dt = data.get('scheduled_at', '')
        parsed = parse_datetime(new_dt)
        if not parsed:
            return JsonResponse({'error': '日時の形式が不正です'}, status=400)
        post.scheduled_at = parsed
        post.save(update_fields=['scheduled_at', 'updated_at'])
        return JsonResponse({'ok': True, 'message': '日時を変更しました'})

    return JsonResponse({'error': '不明なアクションです'}, status=400)


@staff_member_required
@require_POST
def scheduled_post_create_api(request):
    """手動で予約投稿を作成 API"""
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
        topic='manual',
        body=body,
        scheduled_at=scheduled_at,
        status=THScheduledPost.Status.DRAFT,
        created_by=request.user,
    )

    return JsonResponse({
        'ok': True,
        'post_id': post.pk,
        'message': f'予約投稿(ID:{post.pk})を作成しました',
    })
