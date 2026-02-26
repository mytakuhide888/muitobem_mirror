# -*- coding: utf-8 -*-
"""自動返信設定 View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from social.models import AutoReplyRule, DMReplyTemplate, Platform

logger = logging.getLogger(__name__)


@staff_member_required
def auto_reply_settings(request):
    """自動返信ルール一覧画面"""
    rules = AutoReplyRule.objects.select_related('reply_template').order_by('pk')
    templates = DMReplyTemplate.objects.all().order_by('pk')
    context = {
        'title': '自動返信設定',
        'rules': rules,
        'templates': templates,
        'platform_choices': Platform.choices,
    }
    return render(request, 'admin/console/auto_reply_settings.html', context)


@staff_member_required
@require_POST
def auto_reply_toggle_api(request, pk):
    """ルールON/OFF切り替え API"""
    try:
        rule = AutoReplyRule.objects.get(pk=pk)
    except AutoReplyRule.DoesNotExist:
        return JsonResponse({'error': 'ルールが見つかりません'}, status=404)
    rule.enabled = not rule.enabled
    rule.save(update_fields=['enabled'])
    return JsonResponse({'ok': True, 'enabled': rule.enabled})
