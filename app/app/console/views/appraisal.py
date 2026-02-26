# -*- coding: utf-8 -*-
"""AI鑑定文生成コンソール View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from social.models import DMMessage, DMContact, Platform

logger = logging.getLogger(__name__)

DIVINATION_PRESETS = {
    'tarot':      'タロット占い',
    'western':    '西洋占星術',
    'numerology': '数秘術',
    'shichu':     '四柱推命',
    'seimei':     '姓名判断',
}


@staff_member_required
def appraisal_gen(request):
    """AI鑑定文生成画面"""
    from ig.models import InstagramBusinessAccount

    accounts = InstagramBusinessAccount.objects.filter(is_active=True)

    # DM相手の候補（最近50ユーザー）
    dm_users = (
        DMMessage.objects
        .filter(platform=Platform.INSTAGRAM)
        .values_list('user_id', flat=True)
        .distinct()[:50]
    )

    # URLパラメータからuser_idを引き継ぎ
    preselect_user_id = request.GET.get('user_id', '')

    context = {
        'title': 'AI鑑定文生成',
        'accounts': accounts,
        'dm_users': list(dm_users),
        'divination_presets': DIVINATION_PRESETS,
        'preselect_user_id': preselect_user_id,
    }
    return render(request, 'admin/console/appraisal_gen.html', context)


@staff_member_required
@require_POST
def appraisal_generate_api(request):
    """鑑定文生成 API"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    birthdate = data.get('birthdate', '').strip()
    concern = data.get('concern', '').strip()
    divination = data.get('divination', 'tarot').strip()
    character_desc = data.get('character_desc', '').strip()

    if not birthdate:
        return JsonResponse({'error': '生年月日を入力してください'}, status=400)
    if not concern:
        return JsonResponse({'error': '悩み・相談内容を入力してください'}, status=400)

    from ig.services.appraisal_generator import generate_appraisal
    result = generate_appraisal(
        birthdate=birthdate,
        concern=concern,
        divination=divination,
        character_desc=character_desc,
    )
    if not result.get('ok'):
        return JsonResponse({'error': result.get('error', '生成失敗')}, status=500)

    return JsonResponse({'ok': True, 'appraisal_text': result['appraisal_text']})


@staff_member_required
@require_POST
def appraisal_send_dm_api(request):
    """鑑定文をDM送信 API"""
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

    contact = DMContact.objects.filter(ig_user_id=user_id).first()
    thread_key = contact.thread_key if contact else None
    psid = (contact.psid if contact else None) or user_id

    try:
        from social.services.ig_api import send_dm_flexible
        result = send_dm_flexible(access_token=token, psid=psid, thread_key=thread_key, text=text)
    except Exception as e:
        logger.exception('appraisal_send_dm_api: DM送信失敗')
        return JsonResponse({'error': str(e)}, status=500)

    dm = DMMessage.objects.create(
        platform=Platform.INSTAGRAM,
        user_id=user_id,
        text=text,
        direction=DMMessage.Direction.OUT,
        sent_at=timezone.now(),
        raw_json=result or {},
    )

    IGDMReplyLog.objects.create(
        dm=dm,
        recipient_id=user_id,
        biz_ig_id=account.ig_business_id,
        text=text,
        ok=True,
        http_status=200,
        response=result or {},
    )

    return JsonResponse({'ok': True, 'message': 'DM送信しました'})
