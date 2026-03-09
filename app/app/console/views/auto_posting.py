# -*- coding: utf-8 -*-
"""自動投稿ワークフロー View"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from th.models import (
    THScheduledPost, ThreadsAccount,
    ConceptProject, ConceptProjectAuthor,
)
from social.models import AppraisalCharacter

logger = logging.getLogger(__name__)


@staff_member_required
def auto_posting(request):
    """自動投稿ワークフロー画面（メイン）"""
    projects = ConceptProject.objects.filter(
        status='COMPLETED',
        character__isnull=False,
    ).select_related('character').order_by('-updated_at')

    # 選択中のプロジェクト
    selected_id = request.GET.get('project_id')
    selected_project = None
    project_authors = []
    scheduled_posts = []
    character = None

    if selected_id:
        try:
            selected_project = ConceptProject.objects.select_related('character').get(
                pk=selected_id, status='COMPLETED', character__isnull=False,
            )
            character = selected_project.character
            project_authors = ConceptProjectAuthor.objects.filter(
                project=selected_project,
            ).select_related('author').order_by('order')

            # このプロジェクトで生成されたスケジュール投稿を取得
            scheduled_posts = THScheduledPost.objects.filter(
                concept_project=selected_project,
            ).select_related('source_buzz_post', 'account').order_by('-scheduled_at')
        except ConceptProject.DoesNotExist:
            pass

    context = {
        'title': '自動投稿ワークフロー',
        'projects': projects,
        'selected_project': selected_project,
        'character': character,
        'project_authors': project_authors,
        'scheduled_posts': scheduled_posts,
    }
    return render(request, 'admin/console/auto_posting.html', context)


@staff_member_required
@require_POST
def auto_posting_generate_api(request):
    """POST: 参考投稿取得→AIリライト→スケジュール生成"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    author_username = data.get('author_username', '').strip().lstrip('@')
    interval_hours = int(data.get('interval_hours', 8))
    max_posts = min(int(data.get('max_posts', 5)), 10)
    style_hint = data.get('style_hint', '')

    if not project_id or not author_username:
        return JsonResponse({'error': 'project_id と author_username は必須です'}, status=400)

    try:
        project = ConceptProject.objects.select_related('character').get(
            pk=project_id, character__isnull=False,
        )
    except ConceptProject.DoesNotExist:
        return JsonResponse({'error': 'プロジェクトが見つかりません'}, status=404)

    character = project.character
    if not character:
        return JsonResponse({'error': 'キャラクターが紐付けされていません'}, status=400)

    account = character.th_account
    if not account:
        return JsonResponse({'error': 'Threadsアカウントが紐付けされていません'}, status=400)

    try:
        from th.services.auto_post_generator import generate_scheduled_posts
        posts = generate_scheduled_posts(
            project_id=project_id,
            author_username=author_username,
            account=account,
            character=character,
            interval_hours=interval_hours,
            max_posts=max_posts,
            style_hint=style_hint,
        )
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception('自動投稿生成エラー')
        return JsonResponse({'error': f'生成エラー: {e}'}, status=500)

    return JsonResponse({
        'success': True,
        'count': len(posts),
        'posts': [
            {
                'id': p.id,
                'body': p.body,
                'scheduled_at': p.scheduled_at.isoformat(),
                'status': p.status,
            }
            for p in posts
        ],
    })


@staff_member_required
@require_POST
def auto_posting_edit_api(request, pk):
    """POST: スケジュール投稿の本文・日時を編集"""
    post = get_object_or_404(THScheduledPost, pk=pk)

    if post.status not in (THScheduledPost.Status.DRAFT, THScheduledPost.Status.APPROVED):
        return JsonResponse({'error': '送信済み/失敗の投稿は編集できません'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    updated_fields = []

    body = data.get('body')
    if body is not None:
        post.body = body
        updated_fields.append('body')

    scheduled_at = data.get('scheduled_at')
    if scheduled_at:
        parsed = parse_datetime(scheduled_at)
        if parsed:
            post.scheduled_at = parsed
            updated_fields.append('scheduled_at')

    if updated_fields:
        updated_fields.append('updated_at')
        post.save(update_fields=updated_fields)

    return JsonResponse({
        'success': True,
        'id': post.id,
        'body': post.body,
        'scheduled_at': post.scheduled_at.isoformat(),
    })


@staff_member_required
@require_POST
def auto_posting_bulk_approve_api(request):
    """POST: 選択した投稿を一括承認(DRAFT→APPROVED)"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    post_ids = data.get('post_ids', [])
    if not post_ids:
        return JsonResponse({'error': '投稿を選択してください'}, status=400)

    updated = THScheduledPost.objects.filter(
        pk__in=post_ids,
        status=THScheduledPost.Status.DRAFT,
    ).update(status=THScheduledPost.Status.APPROVED)

    return JsonResponse({
        'success': True,
        'updated_count': updated,
    })


@staff_member_required
@require_POST
def auto_posting_refresh_insights_api(request):
    """POST: 選択した投稿のインサイトを手動更新"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    post_ids = data.get('post_ids', [])
    if not post_ids:
        return JsonResponse({'error': '投稿を選択してください'}, status=400)

    posts = THScheduledPost.objects.filter(
        pk__in=post_ids,
        status=THScheduledPost.Status.SENT,
    ).exclude(external_post_id='')

    if not posts.exists():
        return JsonResponse({'error': '更新対象の送信済み投稿がありません'}, status=400)

    try:
        from th.services.post_insights_fetcher import bulk_fetch_insights
        count = bulk_fetch_insights(posts)
    except Exception as e:
        logger.exception('インサイト更新エラー')
        return JsonResponse({'error': f'更新エラー: {e}'}, status=500)

    return JsonResponse({
        'success': True,
        'updated_count': count,
    })
