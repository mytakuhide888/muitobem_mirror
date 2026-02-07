# -*- coding: utf-8 -*-
"""
バズ投稿取得 - Views
"""
import json
import logging
import subprocess
import sys

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from th.models import THBuzzAuthor, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import check_session_validity

logger = logging.getLogger(__name__)


@staff_member_required
def buzz_search(request):
    """バズ投稿取得メイン画面"""

    # ─── フィルタ/ソートパラメータ ───
    sort_by = request.GET.get('sort', '-scraped_at')
    author_filter = request.GET.get('author', '')
    keyword_filter = request.GET.get('keyword', '')
    viral_only = request.GET.get('viral', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # 数値範囲フィルタ
    like_min = request.GET.get('like_min', '')
    like_max = request.GET.get('like_max', '')
    reply_min = request.GET.get('reply_min', '')
    reply_max = request.GET.get('reply_max', '')
    score_min = request.GET.get('score_min', '')
    score_max = request.GET.get('score_max', '')
    er_min = request.GET.get('er_min', '')
    er_max = request.GET.get('er_max', '')

    # 許可されたソートフィールド
    allowed_sorts = {
        'scraped_at', '-scraped_at',
        'posted_at', '-posted_at',
        'like_count', '-like_count',
        'impressions', '-impressions',
        'engagement_score', '-engagement_score',
        'engagement_rate', '-engagement_rate',
        'reply_count', '-reply_count',
    }
    if sort_by not in allowed_sorts:
        sort_by = '-scraped_at'

    # ─── クエリセット構築 ───
    qs = THBuzzPost.objects.select_related('author').all()

    if author_filter:
        qs = qs.filter(author__username__icontains=author_filter)
    if keyword_filter:
        qs = qs.filter(search_keyword__icontains=keyword_filter)
    if viral_only == '1':
        qs = qs.filter(is_viral=True)
    if date_from:
        qs = qs.filter(scraped_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(scraped_at__date__lte=date_to)

    # 数値範囲フィルタ適用
    if like_min:
        try:
            qs = qs.filter(like_count__gte=int(like_min))
        except (ValueError, TypeError):
            pass
    if like_max:
        try:
            qs = qs.filter(like_count__lte=int(like_max))
        except (ValueError, TypeError):
            pass
    if reply_min:
        try:
            qs = qs.filter(reply_count__gte=int(reply_min))
        except (ValueError, TypeError):
            pass
    if reply_max:
        try:
            qs = qs.filter(reply_count__lte=int(reply_max))
        except (ValueError, TypeError):
            pass
    if score_min:
        try:
            qs = qs.filter(engagement_score__gte=float(score_min))
        except (ValueError, TypeError):
            pass
    if score_max:
        try:
            qs = qs.filter(engagement_score__lte=float(score_max))
        except (ValueError, TypeError):
            pass
    if er_min:
        try:
            qs = qs.filter(engagement_rate__gte=float(er_min))
        except (ValueError, TypeError):
            pass
    if er_max:
        try:
            qs = qs.filter(engagement_rate__lte=float(er_max))
        except (ValueError, TypeError):
            pass

    qs = qs.order_by(sort_by)

    # ─── ページネーション ───
    paginator = Paginator(qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # ─── 検索キーワード一覧（フィルタ用） ───
    keywords_list = (
        THBuzzPost.objects
        .exclude(search_keyword='')
        .values_list('search_keyword', flat=True)
        .distinct()
        .order_by('search_keyword')
    )

    # ─── 最近のジョブ ───
    recent_jobs = THBuzzSearchJob.objects.order_by('-created_at')[:10]

    # ─── Cookie 有効期限チェック ───
    session_info = check_session_validity()
    session_warning = None
    if not session_info['valid']:
        session_warning = session_info['message']
    elif session_info['expires_at']:
        from datetime import datetime, timezone as dt_timezone
        remaining = session_info['expires_at'] - datetime.now(tz=dt_timezone.utc)
        if remaining.days <= 3:
            session_warning = session_info['message']

    ctx = {
        'title': 'バズ投稿取得',
        'page_obj': page_obj,
        'recent_jobs': recent_jobs,
        'keywords_list': keywords_list,
        'session_warning': session_warning,
        # 現在のフィルタ値
        'current_sort': sort_by,
        'current_author': author_filter,
        'current_keyword': keyword_filter,
        'current_viral': viral_only,
        'current_date_from': date_from,
        'current_date_to': date_to,
        'current_like_min': like_min,
        'current_like_max': like_max,
        'current_reply_min': reply_min,
        'current_reply_max': reply_max,
        'current_score_min': score_min,
        'current_score_max': score_max,
        'current_er_min': er_min,
        'current_er_max': er_max,
    }
    return render(request, 'admin/console/buzz_search.html', ctx)


@staff_member_required
def buzz_author_detail(request, pk):
    """投稿者詳細画面"""
    author = get_object_or_404(THBuzzAuthor, pk=pk)
    posts = author.buzz_posts.order_by('-scraped_at')

    # Cookie 有効期限チェック
    session_info = check_session_validity()
    session_warning = None
    if not session_info['valid']:
        session_warning = session_info['message']
    elif session_info['expires_at']:
        from datetime import datetime, timezone as dt_timezone
        remaining = session_info['expires_at'] - datetime.now(tz=dt_timezone.utc)
        if remaining.days <= 3:
            session_warning = session_info['message']

    ctx = {
        'title': f'投稿者: @{author.username}',
        'author': author,
        'posts': posts,
        'session_warning': session_warning,
    }
    return render(request, 'admin/console/buzz_author_detail.html', ctx)


@staff_member_required
@require_POST
def buzz_run_search(request):
    """検索ジョブを開始する API"""
    try:
        keywords_raw = request.POST.get('keywords', '').strip()
        scheduled_at = request.POST.get('scheduled_at', '').strip()

        if not keywords_raw:
            return JsonResponse({'ok': False, 'error': 'キーワードを入力してください'}, status=400)

        # カンマ/改行区切りでパース
        keywords = [kw.strip() for kw in keywords_raw.replace('\n', ',').split(',') if kw.strip()]
        if not keywords:
            return JsonResponse({'ok': False, 'error': 'キーワードを入力してください'}, status=400)

        # ジョブレコード作成
        job = THBuzzSearchJob.objects.create(
            keywords=json.dumps(keywords, ensure_ascii=False),
            status='PENDING',
            scheduled_at=scheduled_at if scheduled_at else None,
        )

        if scheduled_at:
            # 予約実行: scheduler が拾う
            return JsonResponse({
                'ok': True,
                'message': f'検索ジョブを予約しました (ID: {job.id})',
                'job_id': job.id,
            })

        # 即時実行: バックグラウンドプロセスで起動
        cmd = [sys.executable, 'manage.py', 'th_buzz_search', '--job-id', str(job.id)]
        log_dir = settings.BASE_DIR / 'deploy'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_out = open(log_dir / 'buzz_search_stdout.log', 'a')
        log_err = open(log_dir / 'buzz_search_stderr.log', 'a')
        subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=log_out,
            stderr=log_err,
        )

        job.status = 'RUNNING'
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])

        return JsonResponse({
            'ok': True,
            'message': f'検索を開始しました (ID: {job.id})',
            'job_id': job.id,
        })

    except Exception as e:
        logger.exception("buzz_run_search エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@staff_member_required
@require_POST
def buzz_fetch_author_posts(request):
    """投稿者の過去投稿取得を開始する API"""
    try:
        author_id = request.POST.get('author_id')
        if not author_id:
            return JsonResponse({'ok': False, 'error': 'author_id が必要です'}, status=400)

        author = get_object_or_404(THBuzzAuthor, pk=author_id)

        # バックグラウンドプロセスで起動
        cmd = [
            sys.executable, 'manage.py', 'th_buzz_fetch_author',
            '--author-id', str(author.id),
        ]
        log_dir = settings.BASE_DIR / 'deploy'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_out = open(log_dir / 'buzz_fetch_stdout.log', 'a')
        log_err = open(log_dir / 'buzz_fetch_stderr.log', 'a')
        subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=log_out,
            stderr=log_err,
        )

        return JsonResponse({
            'ok': True,
            'message': f'@{author.username} の投稿取得を開始しました',
        })

    except Exception as e:
        logger.exception("buzz_fetch_author_posts エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@staff_member_required
def buzz_job_status(request, pk):
    """ジョブステータス確認 API"""
    job = get_object_or_404(THBuzzSearchJob, pk=pk)
    return JsonResponse({
        'id': job.id,
        'status': job.status,
        'result_count': job.result_count,
        'error_message': job.error_message,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
    })
