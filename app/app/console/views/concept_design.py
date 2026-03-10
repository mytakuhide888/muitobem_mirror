# -*- coding: utf-8 -*-
"""コンセプト設計 — ビュー"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from th.models import ConceptProject, ConceptProjectAuthor, THBuzzAuthor

logger = logging.getLogger(__name__)


@staff_member_required
def concept_design(request):
    """プロジェクト一覧 + 新規作成画面"""
    from django.shortcuts import redirect

    # buzz_author_detail から ?username=xxx で遷移してきた場合
    username_param = request.GET.get('username', '').strip()
    if username_param:
        from django.urls import reverse
        project = ConceptProject.objects.filter(
            title=f'@{username_param} ベース設計',
            status='DRAFT',
            character__isnull=True,
            detailed_concept_md='',
        ).order_by('-updated_at').first()
        if project is None:
            project = ConceptProject.objects.create(
                title=f'@{username_param} ベース設計',
                status='DRAFT',
            )
        url = reverse('console:concept_project_detail', kwargs={'pk': project.pk})
        return redirect(f'{url}?username={username_param}')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        project = ConceptProject.objects.create(
            title=title or '新規コンセプト',
            status='DRAFT',
        )
        return redirect('console:concept_project_detail', pk=project.pk)

    projects = ConceptProject.objects.select_related('character').all()[:50]

    return render(request, 'admin/console/concept_design.html', {
        'projects': projects,
    })


@staff_member_required
def concept_project_detail(request, pk):
    """プロジェクト詳細（ステップ管理画面）"""
    project = get_object_or_404(ConceptProject, pk=pk)
    project_authors = project.project_authors.select_related('author').all()

    # ★ COMPLETED の場合は詳細閲覧画面へ
    if project.status == 'COMPLETED':
        from social.models import ThreadsAccount
        threads_accounts = ThreadsAccount.objects.all()
        return render(request, 'admin/console/project_detail.html', {
            'project': project,
            'project_authors': project_authors,
            'threads_accounts': threads_accounts,
        })

    # サジェスト用: お気に入り or コンセプト候補のアカウント
    suggest_authors = THBuzzAuthor.objects.filter(
        is_excluded=False,
    ).filter(
        models_Q_favorited_or_candidate()
    ).order_by('-growth_score')[:20]

    # ?username= パラメータ（buzz_author_detailからの遷移用）
    preset_username = request.GET.get('username', '').strip()

    return render(request, 'admin/console/concept_project_detail.html', {
        'project': project,
        'project_authors': project_authors,
        'suggest_authors': suggest_authors,
        'preset_username': preset_username,
    })


def models_Q_favorited_or_candidate():
    from django.db.models import Q
    return Q(is_favorited=True) | Q(is_concept_candidate=True)


@staff_member_required
@require_POST
def concept_analyze_api(request):
    """@username (最大3) → AI分析実行"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    usernames = data.get('usernames', [])

    if not project_id or not usernames:
        return JsonResponse({'ok': False, 'error': 'project_id と usernames が必要です'}, status=400)

    usernames = [u.lstrip('@').strip() for u in usernames[:3] if u.strip()]
    if not usernames:
        return JsonResponse({'ok': False, 'error': 'ユーザー名を1つ以上入力してください'}, status=400)

    project = get_object_or_404(ConceptProject, pk=project_id)

    from th.services.concept_analyzer import (
        analyze_author, ensure_author_data, synthesize_analysis_results,
    )

    results = []
    errors = []
    retained_author_ids = []

    for username in usernames:
        try:
            author = ensure_author_data(username)
            if not author:
                errors.append(f'@{username}: アカウントが見つかりませんでした')
                continue

            analysis = analyze_author(author)
            analysis['username'] = author.username
            analysis['display_name'] = author.display_name or ''

            # 中間テーブルに保存
            ConceptProjectAuthor.objects.update_or_create(
                project=project, author=author,
                defaults={
                    'ai_analysis': analysis,
                    'ai_summary': analysis.get('summary', ''),
                    'order': len(results),
                },
            )
            retained_author_ids.append(author.pk)

            results.append({
                'username': author.username,
                'display_name': author.display_name,
                'followers_count': author.followers_count,
                'analysis': analysis,
            })
        except Exception as e:
            logger.exception('concept_analyze_api: @%s の分析失敗', username)
            errors.append(f'@{username}: {str(e)}')

    project.project_authors.exclude(author_id__in=retained_author_ids).delete()

    # 統合分析結果をプロジェクトに保存
    if results:
        all_analyses = [r['analysis'] for r in results]
        synthesized = synthesize_analysis_results(all_analyses)

        project.analysis_result = {
            'individual': all_analyses,
            'shared_bones': synthesized.get('shared_bones', []),
        }
        project.analysis_summary = '\n'.join(
            f'- {line}' for line in synthesized.get('summary_bullets', []) if line
        )
        project.status = 'ANALYZING'
        project.save(update_fields=['analysis_result', 'analysis_summary', 'status'])
    else:
        project.analysis_result = {}
        project.analysis_summary = ''
        project.status = 'DRAFT'
        project.save(update_fields=['analysis_result', 'analysis_summary', 'status'])

    return JsonResponse({
        'ok': True,
        'results': results,
        'errors': errors,
        'summary': project.analysis_summary,
    })


@staff_member_required
@require_POST
def concept_proposals_api(request):
    """分析結果からずらしコンセプト案5つ生成"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    user_context = data.get('user_context', '')

    project = get_object_or_404(ConceptProject, pk=project_id)

    if not project.analysis_result:
        return JsonResponse({'ok': False, 'error': '先にAI分析を実行してください'}, status=400)

    from th.services.concept_analyzer import generate_concept_proposals

    analysis_results = project.analysis_result.get('individual', [])

    try:
        proposals = generate_concept_proposals(analysis_results, user_context)
    except Exception as e:
        logger.exception('concept_proposals_api: 生成失敗')
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    project.concept_proposals = proposals
    project.status = 'CONCEPTS_GENERATED'
    project.save(update_fields=['concept_proposals', 'status'])

    return JsonResponse({'ok': True, 'proposals': proposals})


@staff_member_required
@require_POST
def concept_detail_api(request):
    """案選択 + 要望 → 詳細化"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    selected_index = data.get('selected_index')
    user_feedback = data.get('user_feedback', '')

    project = get_object_or_404(ConceptProject, pk=project_id)

    proposals = project.concept_proposals or []
    if (
        not proposals
        or not isinstance(selected_index, int)
        or selected_index < 0
        or selected_index >= len(proposals)
    ):
        return JsonResponse({'ok': False, 'error': '有効なコンセプト案を選択してください'}, status=400)

    selected = proposals[selected_index]

    from th.services.concept_analyzer import detail_concept

    try:
        project.status = 'DETAILING'
        project.selected_proposal_index = selected_index
        project.user_feedback = user_feedback
        project.save(update_fields=['status', 'selected_proposal_index', 'user_feedback'])

        detailed_md = detail_concept(selected, user_feedback)
    except Exception as e:
        logger.exception('concept_detail_api: 詳細化失敗')
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    project.detailed_concept_md = detailed_md
    project.save(update_fields=['detailed_concept_md'])

    return JsonResponse({'ok': True, 'detailed_md': detailed_md})


@staff_member_required
@require_POST
def concept_save_api(request):
    """コンセプト保存 → AppraisalCharacter生成"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    profile_bio = (data.get('profile_bio') or '').strip()
    pinned_post_samples = data.get('pinned_post_samples') or []
    if not isinstance(pinned_post_samples, list):
        return JsonResponse({'ok': False, 'error': 'pinned_post_samples は配列で指定してください'}, status=400)

    project = get_object_or_404(ConceptProject, pk=project_id)

    if not project.detailed_concept_md:
        return JsonResponse({'ok': False, 'error': '先にコンセプトを詳細化してください'}, status=400)

    from th.services.concept_saver import save_concept_to_character

    try:
        character = save_concept_to_character(
            project,
            profile_bio=profile_bio,
            pinned_post_samples=[str(item).strip() for item in pinned_post_samples if str(item).strip()],
        )
    except Exception as e:
        logger.exception('concept_save_api: 保存失敗')
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    project.status = 'COMPLETED'
    project.save(update_fields=['status'])

    return JsonResponse({
        'ok': True,
        'character_id': character.pk,
        'character_name': character.name,
    })


@staff_member_required
@require_POST
def concept_edit_md_api(request):
    """MD形式コンセプト文書の編集保存"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    md_content = data.get('md_content', '')

    project = get_object_or_404(ConceptProject, pk=project_id)
    project.detailed_concept_md = md_content
    project.save(update_fields=['detailed_concept_md'])

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def project_add_author_api(request):
    """COMPLETED プロジェクトに参考アカウントを追加"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    username = (data.get('username') or '').lstrip('@').strip()

    if not project_id or not username:
        return JsonResponse({'ok': False, 'error': 'project_id と username が必要です'}, status=400)

    project = get_object_or_404(ConceptProject, pk=project_id)

    from th.services.concept_analyzer import ensure_author_data, analyze_author

    try:
        author = ensure_author_data(username)
        if not author:
            return JsonResponse({'ok': False, 'error': f'@{username}: アカウントが見つかりませんでした'}, status=404)

        analysis = analyze_author(author)
        analysis['username'] = author.username
        analysis['display_name'] = author.display_name or ''

        pa, _ = ConceptProjectAuthor.objects.update_or_create(
            project=project, author=author,
            defaults={
                'ai_analysis': analysis,
                'ai_summary': analysis.get('summary', ''),
                'order': project.project_authors.count(),
            },
        )
    except Exception as e:
        logger.exception('project_add_author_api: @%s の追加失敗', username)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    return JsonResponse({
        'ok': True,
        'author': {
            'id': author.pk,
            'username': author.username,
            'display_name': author.display_name or '',
            'followers_count': author.followers_count,
            'summary': analysis.get('summary', ''),
        },
    })


@staff_member_required
@require_POST
def project_remove_author_api(request):
    """参考アカウントをプロジェクトから削除"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    author_id = data.get('author_id')

    if not project_id or not author_id:
        return JsonResponse({'ok': False, 'error': 'project_id と author_id が必要です'}, status=400)

    deleted, _ = ConceptProjectAuthor.objects.filter(
        project_id=project_id, author_id=author_id,
    ).delete()

    return JsonResponse({'ok': True, 'deleted': deleted > 0})


@staff_member_required
@require_POST
def project_link_account_api(request):
    """キャラクターにThreadsアカウントを紐付け"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    project_id = data.get('project_id')
    threads_account_id = data.get('threads_account_id')

    project = get_object_or_404(ConceptProject, pk=project_id)

    if not project.character:
        return JsonResponse({'ok': False, 'error': 'プロジェクトにキャラクターが紐付いていません'}, status=400)

    from social.models import ThreadsAccount

    if threads_account_id:
        account = get_object_or_404(ThreadsAccount, pk=threads_account_id)
        project.character.th_account = account
    else:
        project.character.th_account = None

    project.character.save(update_fields=['th_account'])

    return JsonResponse({
        'ok': True,
        'th_account_id': project.character.th_account_id,
        'th_account_name': str(project.character.th_account) if project.character.th_account else '',
    })
