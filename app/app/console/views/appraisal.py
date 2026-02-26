# -*- coding: utf-8 -*-
"""AI鑑定文生成コンソール View v2"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from social.models import (
    DMMessage, DMContact, Platform,
    AppraisalCharacter, AppraisalTemplate, AppraisalCustomer, AppraisalHistory,
)

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
    characters = AppraisalCharacter.objects.filter(is_active=True)

    # DM相手の候補（最近50ユーザー）
    dm_users = (
        DMMessage.objects
        .filter(platform=Platform.INSTAGRAM)
        .values_list('user_id', flat=True)
        .distinct()[:50]
    )

    preselect_user_id = request.GET.get('user_id', '')

    # 最近の鑑定履歴（10件）
    recent_histories = AppraisalHistory.objects.select_related(
        'character', 'customer'
    )[:10]

    context = {
        'title': 'AI鑑定文生成',
        'accounts': accounts,
        'characters': characters,
        'dm_users': list(dm_users),
        'divination_presets': DIVINATION_PRESETS,
        'preselect_user_id': preselect_user_id,
        'recent_histories': recent_histories,
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
    character_id = data.get('character_id')
    template_id = data.get('template_id')
    customer_id = data.get('customer_id')

    if not birthdate:
        return JsonResponse({'error': '生年月日を入力してください'}, status=400)
    if not concern:
        return JsonResponse({'error': '悩み・相談内容を入力してください'}, status=400)

    # v2: キャラクター・テンプレート・顧客を取得
    character = None
    template = None
    customer = None
    customer_context = ''
    dm_context = ''

    if character_id:
        try:
            character = AppraisalCharacter.objects.get(pk=character_id, is_active=True)
        except AppraisalCharacter.DoesNotExist:
            pass

    if template_id:
        try:
            template = AppraisalTemplate.objects.get(pk=template_id, is_active=True)
        except AppraisalTemplate.DoesNotExist:
            pass

    if customer_id:
        try:
            customer = AppraisalCustomer.objects.get(pk=customer_id)
            customer_context = customer.personality_analysis or ''
            # DM履歴もコンテキストに含める
            from ig.services.customer_analyzer import get_customer_dm_history
            dm_history = get_customer_dm_history(
                customer.platform_user_id, customer.platform
            )
            if dm_history:
                dm_context = "\n".join(
                    f"[{m['direction']}] {m['text']}" for m in dm_history[-10:]
                )
        except AppraisalCustomer.DoesNotExist:
            pass

    from ig.services.appraisal_generator import generate_appraisal
    result = generate_appraisal(
        birthdate=birthdate,
        concern=concern,
        divination=divination,
        character_desc=character_desc,
        character=character,
        template=template,
        customer_context=customer_context,
        dm_context=dm_context,
    )
    if not result.get('ok'):
        return JsonResponse({'error': result.get('error', '生成失敗')}, status=500)

    # 鑑定履歴を保存
    history = AppraisalHistory.objects.create(
        character=character,
        template=template,
        customer=customer,
        birthdate=birthdate,
        concern=concern,
        divination=divination,
        generated_text=result['appraisal_text'],
        system_prompt_used=result.get('system_prompt', ''),
        user_prompt_used=result.get('user_prompt', ''),
    )

    return JsonResponse({
        'ok': True,
        'appraisal_text': result['appraisal_text'],
        'history_id': history.pk,
    })


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
    history_id = data.get('history_id')

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

    # 鑑定履歴のDM送信ステータスを更新
    if history_id:
        AppraisalHistory.objects.filter(pk=history_id).update(
            sent_text=text,
            dm_sent=True,
            dm_sent_at=timezone.now(),
        )

    return JsonResponse({'ok': True, 'message': 'DM送信しました'})


# ── 新規 API エンドポイント ──

@staff_member_required
@require_GET
def appraisal_templates_api(request):
    """キャラクターに紐づくテンプレート一覧を返す"""
    character_id = request.GET.get('character_id')
    if not character_id:
        return JsonResponse({'templates': []})

    templates = AppraisalTemplate.objects.filter(
        character_id=character_id, is_active=True
    ).order_by('sort_order', 'name')

    data = [
        {
            'id': t.pk,
            'name': t.name,
            'category': t.category,
            'category_label': t.get_category_display(),
            'word_count_min': t.word_count_min,
            'word_count_max': t.word_count_max,
        }
        for t in templates
    ]
    return JsonResponse({'templates': data})


@staff_member_required
@require_POST
def appraisal_fetch_customer_api(request):
    """顧客の投稿を取得し、性格分析を行う"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = data.get('username', '').strip().lstrip('@')
    platform = data.get('platform', 'THREADS').strip()

    if not username:
        return JsonResponse({'error': 'ユーザー名を入力してください'}, status=400)

    # 顧客レコードを取得 or 作成
    customer, created = AppraisalCustomer.objects.get_or_create(
        platform=platform,
        platform_user_id=username,
        defaults={'username': username},
    )

    # 投稿を取得
    from ig.services.customer_analyzer import (
        fetch_customer_posts, save_customer_posts, analyze_customer_personality,
    )

    posts = fetch_customer_posts(username, platform)
    if not posts:
        return JsonResponse({
            'ok': True,
            'customer_id': customer.pk,
            'username': customer.username,
            'posts_count': 0,
            'personality_analysis': '',
            'warning': '投稿が取得できませんでした',
        })

    save_customer_posts(customer, posts)

    # 性格分析
    analysis = analyze_customer_personality(customer)

    return JsonResponse({
        'ok': True,
        'customer_id': customer.pk,
        'username': customer.username,
        'posts_count': len(posts),
        'personality_analysis': analysis,
        'posts': [
            {
                'text': p.get('text', '')[:200],
                'url': p.get('url', ''),
                'like_count': p.get('like_count', 0),
            }
            for p in posts[:10]
        ],
    })


@staff_member_required
@require_GET
def appraisal_dm_history_api(request):
    """DM履歴を取得する"""
    user_id = request.GET.get('user_id', '').strip()
    platform = request.GET.get('platform', 'INSTAGRAM').strip()

    if not user_id:
        return JsonResponse({'messages': []})

    from ig.services.customer_analyzer import get_customer_dm_history
    messages = get_customer_dm_history(user_id, platform, limit=30)

    return JsonResponse({'messages': messages})


@staff_member_required
@require_GET
def appraisal_customer_info_api(request):
    """顧客情報を取得する"""
    user_id = request.GET.get('user_id', '').strip()
    platform = request.GET.get('platform', 'INSTAGRAM').strip()

    if not user_id:
        return JsonResponse({'error': 'user_id が必要です'}, status=400)

    try:
        customer = AppraisalCustomer.objects.get(
            platform_user_id=user_id, platform=platform,
        )
    except AppraisalCustomer.DoesNotExist:
        return JsonResponse({'customer': None})

    posts = customer.posts.all()[:10]

    return JsonResponse({
        'customer': {
            'id': customer.pk,
            'username': customer.username,
            'display_name': customer.display_name,
            'birthdate': customer.birthdate,
            'personality_analysis': customer.personality_analysis,
            'memo': customer.memo,
            'posts_fetched_at': customer.posts_fetched_at.isoformat() if customer.posts_fetched_at else None,
            'posts': [
                {
                    'text': p.text_content[:200],
                    'url': p.post_url,
                    'like_count': p.like_count,
                    'posted_at': p.posted_at.isoformat() if p.posted_at else None,
                }
                for p in posts
            ],
        }
    })
