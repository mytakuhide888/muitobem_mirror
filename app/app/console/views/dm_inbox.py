# -*- coding: utf-8 -*-
"""DM受信管理 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Max
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from social.models import DMMessage, DMContact, Platform

logger = logging.getLogger(__name__)


@staff_member_required
def dm_inbox(request):
    """DM受信管理画面"""
    from ig.models import InstagramBusinessAccount

    accounts = InstagramBusinessAccount.objects.filter(is_active=True)
    selected_user_id = request.GET.get('user_id', '')

    # ユーザー別の最新メッセージをまとめて取得
    convs_qs = (
        DMMessage.objects
        .filter(platform=Platform.INSTAGRAM)
        .values('user_id')
        .annotate(latest=Max('sent_at'), count=Count('id'))
        .order_by('-latest')[:50]
    )

    # 各会話の最新メッセージ本文を付加
    conversations = []
    for cv in convs_qs:
        last_msg = (
            DMMessage.objects
            .filter(platform=Platform.INSTAGRAM, user_id=cv['user_id'])
            .order_by('-sent_at')
            .values('text', 'direction')
            .first()
        )
        conversations.append({
            'user_id': cv['user_id'],
            'count': cv['count'],
            'latest': cv['latest'],
            'preview': (last_msg['text'] or '')[:40] if last_msg else '',
            'direction': last_msg['direction'] if last_msg else 'IN',
        })

    # 選択したユーザーの会話履歴
    thread_messages = []
    if selected_user_id:
        thread_messages = list(
            DMMessage.objects
            .filter(platform=Platform.INSTAGRAM, user_id=selected_user_id)
            .order_by('sent_at')
            .values('pk', 'text', 'direction', 'sent_at')
        )

    context = {
        'title': 'DM受信管理',
        'accounts': accounts,
        'conversations': conversations,
        'selected_user_id': selected_user_id,
        'thread_messages': thread_messages,
        'thread_messages_json': json.dumps(
            [
                {
                    'text': m['text'],
                    'direction': m['direction'],
                    'sent_at': m['sent_at'].strftime('%m/%d %H:%M'),
                }
                for m in thread_messages
            ],
            ensure_ascii=False,
        ),
    }
    return render(request, 'admin/console/dm_inbox.html', context)


@staff_member_required
@require_POST
def dm_reply_api(request):
    """DM手動返信 API"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_id = data.get('user_id', '').strip()
    text = data.get('text', '').strip()
    account_id = data.get('account_id')

    if not user_id:
        return JsonResponse({'error': '送信先ユーザーIDが空です'}, status=400)
    if not text:
        return JsonResponse({'error': '本文が空です'}, status=400)
    if not account_id:
        return JsonResponse({'error': 'アカウントを選択してください'}, status=400)

    from ig.models import InstagramBusinessAccount, IGDMReplyLog
    try:
        account = InstagramBusinessAccount.objects.get(pk=account_id, is_active=True)
    except InstagramBusinessAccount.DoesNotExist:
        return JsonResponse({'error': 'アカウントが見つかりません'}, status=404)

    token = account.best_send_token
    if not token:
        return JsonResponse({'error': 'アクセストークンが設定されていません'}, status=400)

    # DMContactからthread_key/psid解決
    contact = DMContact.objects.filter(ig_user_id=user_id).first()
    thread_key = contact.thread_key if contact else None
    psid = (contact.psid if contact else None) or user_id

    try:
        from social.services.ig_api import send_dm_flexible
        result = send_dm_flexible(access_token=token, psid=psid, thread_key=thread_key, text=text)
    except Exception as e:
        logger.exception("DM送信失敗")
        return JsonResponse({'error': str(e)}, status=500)

    # 送信履歴をDMMessageに保存
    dm = DMMessage.objects.create(
        platform=Platform.INSTAGRAM,
        user_id=user_id,
        text=text,
        direction=DMMessage.Direction.OUT,
        sent_at=timezone.now(),
        raw_json=result or {},
    )

    # IGDMReplyLogに送信ログ保存
    IGDMReplyLog.objects.create(
        dm=dm,
        recipient_id=user_id,
        biz_ig_id=account.ig_business_id,
        text=text,
        ok=True,
        http_status=200,
        response=result or {},
    )

    return JsonResponse({'ok': True, 'message': 'DMを送信しました'})
