# -*- coding: utf-8 -*-
"""
バズ投稿取得 - Views
"""
import json
import logging
import subprocess
import sys
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

import re
import urllib.request

from th.models import THBuzzAuthor, THBuzzAuthorAnalysis, THBuzzPost, THBuzzSearchJob
from th.services.buzz_scraper import ViralityDetector, check_session_validity

logger = logging.getLogger(__name__)


@staff_member_required
def buzz_search(request):
    """バズ投稿取得メイン画面"""

    # ─── フィルタ/ソートパラメータ ───
    sort_by = request.GET.get('sort', '-scraped_at')
    author_filter = request.GET.get('author', '')
    keyword_filter = request.GET.get('keyword', '')
    viral_only = request.GET.get('viral', '')
    favorite_only = request.GET.get('favorite', '')
    include_excluded = request.GET.get('include_excluded', '')
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
    if favorite_only == '1':
        qs = qs.filter(author__is_favorited=True)
    elif favorite_only == '0':
        qs = qs.filter(author__is_favorited=False)
    if not include_excluded:
        qs = qs.filter(author__is_excluded=False)
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

    # media_urls を正しい JSON 文字列に変換（テンプレートの safe フィルタ用）
    for post in page_obj:
        post.media_urls_json = json.dumps(post.media_urls or [], ensure_ascii=False)

    # ─── 検索キーワード一覧（フィルタ用） ───
    keywords_list = (
        THBuzzPost.objects
        .exclude(search_keyword='')
        .values_list('search_keyword', flat=True)
        .distinct()
        .order_by('search_keyword')
    )

    # ─── stale ジョブ検出: 3時間以上 RUNNING のジョブを終了扱いに ───
    stale_cutoff = timezone.now() - timedelta(hours=3)
    stale_jobs = THBuzzSearchJob.objects.filter(
        status='RUNNING', started_at__lt=stale_cutoff,
    )
    for stale_job in stale_jobs:
        if stale_job.result_count and stale_job.result_count > 0:
            # 途中結果があれば部分完了として COMPLETED にする
            stale_job.status = 'COMPLETED'
            stale_job.completed_at = timezone.now()
            stale_job.error_message = f'タイムアウト（3時間超過）: 途中まで {stale_job.result_count} 件取得済みで部分完了'
            stale_job.save(update_fields=['status', 'completed_at', 'error_message'])
        else:
            stale_job.status = 'FAILED'
            stale_job.completed_at = timezone.now()
            stale_job.error_message = 'タイムアウト: 3時間以上実行中のため自動終了'
            stale_job.save(update_fields=['status', 'completed_at', 'error_message'])
    if stale_jobs.exists():
        logger.warning("stale ジョブを検出・更新")

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
        'current_favorite': favorite_only,
        'current_include_excluded': include_excluded,
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

    # ─── 分析メモの取得/作成 ───
    analysis, _ = THBuzzAuthorAnalysis.objects.get_or_create(author=author)

    # ─── フィルタ/ソートパラメータ ───
    sort_by = request.GET.get('sort', '-scraped_at')
    keyword_filter = request.GET.get('keyword', '')
    viral_only = request.GET.get('viral', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    like_min = request.GET.get('like_min', '')
    like_max = request.GET.get('like_max', '')
    reply_min = request.GET.get('reply_min', '')
    reply_max = request.GET.get('reply_max', '')
    score_min = request.GET.get('score_min', '')
    score_max = request.GET.get('score_max', '')
    er_min = request.GET.get('er_min', '')
    er_max = request.GET.get('er_max', '')

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
    qs = author.buzz_posts.all()

    if keyword_filter:
        qs = qs.filter(
            Q(text_content__icontains=keyword_filter)
            | Q(search_keyword__icontains=keyword_filter)
        )
    if viral_only == '1':
        qs = qs.filter(is_viral=True)
    if date_from:
        qs = qs.filter(scraped_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(scraped_at__date__lte=date_to)
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

    # media_urls を正しい JSON 文字列に変換（テンプレートの safe フィルタ用）
    for post in page_obj:
        post.media_urls_json = json.dumps(post.media_urls or [], ensure_ascii=False)

    # ─── ピン留め投稿を分離 ───
    pinned_posts = []
    for p in author.buzz_posts.all():
        raw = p.raw_json or {}
        if not isinstance(raw, dict):
            # 旧データ等で raw_json が辞書以外でも詳細画面が落ちないようにする
            raw = {}
        if raw.get('is_pinned'):
            pinned_posts.append(p)
    for post in pinned_posts:
        post.media_urls_json = json.dumps(post.media_urls or [], ensure_ascii=False)

    # ─── 検索キーワード一覧（フィルタ用） ───
    keywords_list = (
        author.buzz_posts
        .exclude(search_keyword='')
        .values_list('search_keyword', flat=True)
        .distinct()
        .order_by('search_keyword')
    )

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

    # ─── 投稿パターン分析データ ───
    all_posts = list(author.buzz_posts.all())
    pattern_stats = _calc_post_pattern_stats(all_posts, author.followers_count or 0)

    ctx = {
        'title': f'投稿者: @{author.username}',
        'author': author,
        'analysis': analysis,
        'pattern_stats': json.dumps(pattern_stats, ensure_ascii=False),
        'page_obj': page_obj,
        'pinned_posts': pinned_posts,
        'keywords_list': keywords_list,
        'session_warning': session_warning,
        'current_sort': sort_by,
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

        # 即時実行: ステータスを先に RUNNING に設定してからプロセスを起動
        job.status = 'RUNNING'
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])

        cmd = [sys.executable, 'manage.py', 'th_buzz_search', '--job-id', str(job.id)]
        if not request.POST.get('exclude_replies'):
            cmd.append('--include-replies')
        sort_order = request.POST.get('sort_order', 'recent')
        if sort_order in ('recent', 'default'):
            cmd.extend(['--sort-order', sort_order])
        if request.POST.get('growth_filter'):
            cmd.append('--growth-filter')
        if request.POST.get('fetch_posts'):
            cmd.append('--fetch-posts')
            # 「投稿者情報を詳細取得」ON時は過去投稿を深く取得
            cmd.extend(['--author-post-scrolls', '30'])
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
def buzz_run_account_fetch(request):
    """アカウント指定検索ジョブを開始する API"""
    try:
        usernames_raw = request.POST.get('usernames', '').strip()
        scheduled_at = request.POST.get('scheduled_at', '').strip()

        if not usernames_raw:
            return JsonResponse({'ok': False, 'error': 'アカウント名を入力してください'}, status=400)

        # カンマ/改行区切りでパース、@を除去
        usernames = [
            u.strip().lstrip('@')
            for u in usernames_raw.replace('\n', ',').split(',')
            if u.strip()
        ]
        if not usernames:
            return JsonResponse({'ok': False, 'error': 'アカウント名を入力してください'}, status=400)

        # ジョブレコード作成
        job = THBuzzSearchJob.objects.create(
            job_type='account',
            keywords=json.dumps(usernames, ensure_ascii=False),
            status='PENDING',
            scheduled_at=scheduled_at if scheduled_at else None,
        )

        if scheduled_at:
            return JsonResponse({
                'ok': True,
                'message': f'アカウント取得ジョブを予約しました (ID: {job.id})',
                'job_id': job.id,
            })

        # 即時実行
        job.status = 'RUNNING'
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])

        cmd = [sys.executable, 'manage.py', 'th_buzz_fetch_author', '--job-id', str(job.id)]
        if request.POST.get('exclude_replies'):
            pass  # デフォルトでリプライ除外（--include-replies を付けない）
        else:
            cmd.append('--include-replies')
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
            'message': f'アカウント取得を開始しました (ID: {job.id}, {len(usernames)}件)',
            'job_id': job.id,
        })

    except Exception as e:
        logger.exception("buzz_run_account_fetch エラー")
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

        # ジョブレコード作成
        job = THBuzzSearchJob.objects.create(
            job_type='account',
            keywords=json.dumps([author.username], ensure_ascii=False),
            status='RUNNING',
            started_at=timezone.now(),
        )

        # バックグラウンドプロセスで起動
        cmd = [
            sys.executable, 'manage.py', 'th_buzz_fetch_author',
            '--job-id', str(job.id),
        ]
        if not request.POST.get('exclude_replies'):
            cmd.append('--include-replies')
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
            'message': f'@{author.username} の投稿取得を開始しました (ID: {job.id})',
            'job_id': job.id,
        })

    except Exception as e:
        logger.exception("buzz_fetch_author_posts エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def _classify_job_error(job):
    """ジョブのエラーを分類し (category, remedy) を返す"""
    msg = (job.error_message or '').lower()
    tb_text = (job.error_traceback or '').lower()
    combined = msg + ' ' + tb_text

    if '[session]' in msg or 'sessionid' in combined or 'cookie' in combined:
        return 'SESSION', (
            'セッション Cookie が期限切れの可能性があります。\n'
            '1. ブラウザで threads.com にログイン\n'
            '2. Cookie をエクスポート（threads_session.json）\n'
            '3. 所定のパスに配置して再実行'
        )
    if 'challenge' in combined or 'blocked' in combined or '429' in combined:
        return 'BLOCKED', (
            'Threads からアクセスが制限されています。\n'
            '1. 数時間〜半日待ってから再実行\n'
            '2. IPアドレスの変更を検討\n'
            '3. 実行間隔・件数を減らす'
        )
    if 'タイムアウト' in msg or '30分以上' in msg:
        return 'TIMEOUT', (
            '処理がタイムアウトしました。\n'
            '1. 対象件数やスクロール回数を減らして再実行\n'
            '2. ネットワーク状態を確認'
        )
    if 'connection' in combined or 'timeout' in combined or 'errno' in combined:
        return 'NETWORK', (
            'ネットワーク接続エラーです。\n'
            '1. インターネット接続を確認\n'
            '2. VPN/プロキシの状態を確認\n'
            '3. しばらく待って再実行'
        )
    return 'UNKNOWN', (
        'トレースバックを展開して原因を確認してください。\n'
        'deploy/ ディレクトリのログファイルも確認してください。'
    )


@staff_member_required
def buzz_job_status(request, pk):
    """ジョブステータス確認 API"""
    job = get_object_or_404(THBuzzSearchJob, pk=pk)
    data = {
        'id': job.id,
        'status': job.status,
        'result_count': job.result_count,
        'error_message': job.error_message,
        'error_traceback': job.error_traceback,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
    }
    if job.status == 'FAILED' and job.error_message:
        category, remedy = _classify_job_error(job)
        data['error_category'] = category
        data['remedy'] = remedy
    return JsonResponse(data)


# ─── Phase B: 急成長アカウント発見 ───


@staff_member_required
def buzz_growth_ranking(request):
    """急成長アカウントランキング画面"""

    # ─── フィルタ/ソートパラメータ ───
    sort_by = request.GET.get('sort', '-growth_score')
    min_followers = request.GET.get('min_followers', '')
    min_score = request.GET.get('min_score', '')
    max_age_days = request.GET.get('max_age_days', '')
    category = request.GET.get('category', '')
    q = request.GET.get('q', '')
    candidates_only = request.GET.get('candidates_only', '')
    quality_only = request.GET.get('quality_only', '')
    include_excluded = request.GET.get('include_excluded', '')
    fortune_only = request.GET.get('fortune_only', '')
    min_fortune_score = request.GET.get('min_fortune_score', '')
    has_memo = request.GET.get('has_memo', '')
    attention_only = request.GET.get('attention_only', '')

    allowed_sorts = {
        'growth_score', '-growth_score',
        'followers_per_day', '-followers_per_day',
        'followers_count', '-followers_count',
        'account_age_days', '-account_age_days',
        'avg_likes', '-avg_likes',
        'updated_at', '-updated_at',
        'quality_score', '-quality_score',
        'fortune_relevance_score', '-fortune_relevance_score',
    }
    if sort_by not in allowed_sorts:
        sort_by = '-growth_score'

    # ─── クエリセット構築 ───
    qs = THBuzzAuthor.objects.all()

    if q:
        qs = qs.filter(
            Q(username__icontains=q) | Q(display_name__icontains=q) | Q(bio__icontains=q)
        )
    if min_followers:
        try:
            qs = qs.filter(followers_count__gte=int(min_followers))
        except (ValueError, TypeError):
            pass
    if min_score:
        try:
            qs = qs.filter(growth_score__gte=float(min_score))
        except (ValueError, TypeError):
            pass
    if max_age_days:
        try:
            qs = qs.filter(account_age_days__lte=int(max_age_days))
        except (ValueError, TypeError):
            pass
    if category:
        qs = qs.filter(category_tags__icontains=category)
    if candidates_only:
        qs = qs.filter(is_concept_candidate=True)
    if quality_only:
        qs = qs.filter(is_quality_account=True)
    if fortune_only:
        qs = qs.filter(fortune_relevance_score__isnull=False, fortune_relevance_score__gt=0)
    if min_fortune_score:
        try:
            qs = qs.filter(fortune_relevance_score__gte=float(min_fortune_score))
        except (ValueError, TypeError):
            pass
    if has_memo:
        qs = qs.exclude(memo='')
    if attention_only:
        qs = qs.filter(is_attention_needed=True)
    if not include_excluded:
        qs = qs.filter(is_excluded=False)

    qs = qs.order_by(sort_by)

    # ─── ページネーション ───
    paginator = Paginator(qs, 30)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # カテゴリタグ一覧（フィルタ用）
    all_tags = set()
    for tags_str in THBuzzAuthor.objects.exclude(category_tags='').values_list('category_tags', flat=True):
        for tag in tags_str.split(','):
            tag = tag.strip()
            if tag:
                all_tags.add(tag)
    all_tags = sorted(all_tags)

    # 深掘り対象アカウント数（フォロワー不明 + 投稿不足 + 参加日未取得）
    deep_scan_target_count = (
        # フォロワー不明
        THBuzzAuthor.objects.filter(
            Q(followers_count__isnull=True) | Q(followers_count=0),
            is_excluded=False,
        ).count()
        +
        # フォロワー既知 + 投稿不足
        THBuzzAuthor.objects.filter(
            followers_count__isnull=False,
            followers_count__gt=0,
            is_excluded=False,
        ).filter(
            Q(total_post_count__lte=3) | Q(total_post_count__isnull=True)
        ).count()
        +
        # 参加日未取得
        THBuzzAuthor.objects.filter(
            is_excluded=False,
        ).filter(
            Q(raw_json__joined_at__isnull=True) | Q(raw_json__joined_at='')
        ).count()
    )

    # パイプライン統計
    from datetime import timedelta as td
    week_ago = timezone.now() - td(days=7)
    attention_total = THBuzzAuthor.objects.filter(is_attention_needed=True).count()
    attention_new_this_week = THBuzzAuthor.objects.filter(
        is_attention_needed=True, attention_set_at__gte=week_ago,
    ).count()
    new_authors_this_week = THBuzzAuthor.objects.filter(
        first_scraped_at__gte=week_ago, is_excluded=False,
    ).count()
    analyzed_count = THBuzzAuthor.objects.filter(is_analyzed=True).count()

    ctx = {
        'title': '急成長アカウントランキング',
        'page_obj': page_obj,
        'all_tags': all_tags,
        'total_count': paginator.count,
        'deep_scan_target_count': deep_scan_target_count,
        # パイプライン統計
        'attention_total': attention_total,
        'attention_new_this_week': attention_new_this_week,
        'new_authors_this_week': new_authors_this_week,
        'analyzed_count': analyzed_count,
        # 現在のフィルタ値
        'current_sort': sort_by,
        'current_min_followers': min_followers,
        'current_min_score': min_score,
        'current_max_age_days': max_age_days,
        'current_category': category,
        'current_q': q,
        'current_candidates_only': bool(candidates_only),
        'current_candidates_only_str': '1' if candidates_only else '',
        'current_quality_only': bool(quality_only),
        'current_quality_only_str': '1' if quality_only else '',
        'current_include_excluded': include_excluded,
        'current_include_excluded_str': '1' if include_excluded else '',
        'current_fortune_only': bool(fortune_only),
        'current_fortune_only_str': '1' if fortune_only else '',
        'current_min_fortune_score': min_fortune_score,
        'current_has_memo': bool(has_memo),
        'current_has_memo_str': '1' if has_memo else '',
        'current_attention_only': bool(attention_only),
        'current_attention_only_str': '1' if attention_only else '',
        # ページネーション用クエリパラメータ
        'query_params': (
            f"&sort={sort_by}&q={q}"
            f"&min_followers={min_followers or ''}"
            f"&min_score={min_score or ''}"
            f"&max_age_days={max_age_days or ''}"
            f"&category={category or ''}"
            f"&candidates_only={'1' if candidates_only else ''}"
            f"&quality_only={'1' if quality_only else ''}"
            f"&include_excluded={'1' if include_excluded else ''}"
            f"&fortune_only={'1' if fortune_only else ''}"
            f"&min_fortune_score={min_fortune_score or ''}"
            f"&has_memo={'1' if has_memo else ''}"
            f"&attention_only={'1' if attention_only else ''}"
        ),
    }
    return render(request, 'admin/console/buzz_growth_ranking.html', ctx)


@staff_member_required
def buzz_keyword_scan(request):
    """キーワード一括巡回画面"""

    # 最近のジョブ一覧
    recent_jobs = THBuzzSearchJob.objects.order_by('-created_at')[:20]

    # 定義済みキーワードセット
    keyword_presets = {
        '占い基本セット': '占い,タロット,霊視,スピリチュアル,四柱推命,数秘術',
        'ツインレイ・恋愛セット': 'ツインレイ,ソウルメイト,復縁,片思い占い,恋愛占い',
        '金運・開運セット': '金運,開運,パワーストーン,風水,引き寄せ',
        '仕事・転職セット': '仕事運,転職占い,適職診断,キャリア占い',
    }

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
        'title': 'キーワード一括巡回',
        'recent_jobs': recent_jobs,
        'keyword_presets': keyword_presets,
        'session_warning': session_warning,
    }
    return render(request, 'admin/console/buzz_keyword_scan.html', ctx)


@staff_member_required
@require_POST
def buzz_run_keyword_scan(request):
    """キーワード一括巡回ジョブを開始する API"""
    try:
        keywords_raw = request.POST.get('keywords', '').strip()
        if not keywords_raw:
            return JsonResponse({'ok': False, 'error': 'キーワードを入力してください'}, status=400)

        keywords = [kw.strip() for kw in keywords_raw.replace('\n', ',').split(',') if kw.strip()]
        if not keywords:
            return JsonResponse({'ok': False, 'error': 'キーワードを入力してください'}, status=400)

        # ジョブレコード作成
        job = THBuzzSearchJob.objects.create(
            keywords=json.dumps(keywords, ensure_ascii=False),
            status='RUNNING',
            started_at=timezone.now(),
        )

        # バックグラウンドで一括巡回コマンドを起動
        cmd = [sys.executable, 'manage.py', 'th_buzz_keyword_scan', '--job-id', str(job.id)]
        sort_order = request.POST.get('sort_order', 'recent')
        if sort_order in ('recent', 'default'):
            cmd.extend(['--sort-order', sort_order])
        if request.POST.get('growth_filter'):
            cmd.append('--growth-filter')
        if request.POST.get('fetch_posts'):
            cmd.append('--fetch-posts')
            # 「投稿者情報を詳細取得」ON時は過去投稿を深く取得
            cmd.extend(['--author-post-scrolls', '30'])
        log_dir = settings.BASE_DIR / 'deploy'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_out = open(log_dir / 'buzz_keyword_scan_stdout.log', 'a')
        log_err = open(log_dir / 'buzz_keyword_scan_stderr.log', 'a')
        subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=log_out,
            stderr=log_err,
        )

        return JsonResponse({
            'ok': True,
            'message': f'一括巡回を開始しました (ID: {job.id}, {len(keywords)}キーワード)',
            'job_id': job.id,
        })

    except Exception as e:
        logger.exception("buzz_run_keyword_scan エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ─── Phase C: Googleトレンド連携 ───


@staff_member_required
def buzz_trends(request):
    """Googleトレンド分析画面"""
    ctx = {
        'title': 'Googleトレンド分析',
    }
    return render(request, 'admin/console/buzz_trends.html', ctx)


@staff_member_required
def buzz_trends_api(request):
    """Googleトレンドデータ取得 API（GET）"""
    from th.services.trend_analyzer import TrendAnalyzer

    keywords_raw = request.GET.get('keywords', '').strip()
    timeframe = request.GET.get('timeframe', 'today 3-m')
    action = request.GET.get('action', 'interest')

    if not keywords_raw:
        return JsonResponse({'ok': False, 'error': 'キーワードを指定してください'}, status=400)

    keywords = [kw.strip() for kw in keywords_raw.replace('\n', ',').split(',') if kw.strip()]
    if not keywords:
        return JsonResponse({'ok': False, 'error': 'キーワードを指定してください'}, status=400)

    # timeframe の安全性チェック
    allowed_timeframes = {
        'now 7-d', 'today 1-m', 'today 3-m', 'today 12-m', 'today 5-y',
    }
    if timeframe not in allowed_timeframes:
        timeframe = 'today 3-m'

    ta = TrendAnalyzer()

    try:
        if action == 'interest':
            data = ta.get_keyword_interest(keywords[:5], timeframe=timeframe)
            if data is None:
                return JsonResponse({'ok': False, 'error': 'トレンドデータの取得に失敗しました'}, status=500)
            return JsonResponse({'ok': True, 'data': data})

        elif action == 'related':
            keyword = keywords[0]
            queries = ta.get_related_queries(keyword)
            topics = ta.get_related_topics(keyword)
            return JsonResponse({
                'ok': True,
                'data': {
                    'keyword': keyword,
                    'related_queries': queries,
                    'related_topics': topics,
                },
            })

        else:
            return JsonResponse({'ok': False, 'error': f'不明なアクション: {action}'}, status=400)

    except Exception as e:
        logger.exception("buzz_trends_api エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@staff_member_required
@require_POST
def buzz_toggle_favorite(request, pk):
    """投稿者のお気に入りをトグルする API"""
    author = get_object_or_404(THBuzzAuthor, pk=pk)
    author.is_favorited = not author.is_favorited
    author.save(update_fields=['is_favorited'])
    return JsonResponse({'ok': True, 'is_favorited': author.is_favorited})


@staff_member_required
@require_POST
def buzz_toggle_excluded(request, pk):
    """投稿者の対象外フラグをトグルする API"""
    author = get_object_or_404(THBuzzAuthor, pk=pk)
    author.is_excluded = not author.is_excluded
    author.save(update_fields=['is_excluded'])
    return JsonResponse({'ok': True, 'is_excluded': author.is_excluded})


@staff_member_required
@require_POST
def buzz_save_memo(request, pk):
    """投稿者のメモを保存する API"""
    author = get_object_or_404(THBuzzAuthor, pk=pk)
    try:
        body = json.loads(request.body)
        memo = body.get('memo', '')
    except (json.JSONDecodeError, AttributeError):
        memo = request.POST.get('memo', '')
    author.memo = memo
    author.save(update_fields=['memo'])
    return JsonResponse({'ok': True, 'memo': author.memo})


@staff_member_required
@require_POST
def buzz_bulk_exclude(request):
    """投稿者の対象外フラグを一括更新する API"""
    try:
        body = json.loads(request.body)
        author_ids = body.get('author_ids', [])
        exclude = body.get('exclude', True)
        if not author_ids:
            return JsonResponse({'ok': False, 'error': 'author_ids が必要です'}, status=400)
        updated_count = THBuzzAuthor.objects.filter(pk__in=author_ids).update(is_excluded=exclude)
        return JsonResponse({'ok': True, 'updated_count': updated_count})
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'リクエストの形式が不正です'}, status=400)
    except Exception as e:
        logger.exception("buzz_bulk_exclude エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@staff_member_required
@require_POST
def buzz_recalc_er(request):
    """フォロワー既知の投稿者の投稿について ER/バズ判定を一括再計算する API"""
    try:
        authors = THBuzzAuthor.objects.filter(followers_count__isnull=False, followers_count__gt=0)
        total_updated = 0
        for author in authors:
            posts = THBuzzPost.objects.filter(author=author)
            for p in posts:
                post_data = {
                    'like_count': p.like_count or 0,
                    'reply_count': p.reply_count or 0,
                    'repost_count': p.repost_count or 0,
                }
                virality = ViralityDetector.is_viral(post_data, author.followers_count)
                p.engagement_rate = virality['engagement_rate']
                p.engagement_score = virality['engagement_score']
                p.is_viral = virality['is_viral']
                p.save(update_fields=['engagement_rate', 'engagement_score', 'is_viral'])
                total_updated += 1

        return JsonResponse({
            'ok': True,
            'message': f'{total_updated}件の投稿のER/バズ判定を再計算しました',
            'updated_count': total_updated,
        })
    except Exception as e:
        logger.exception("buzz_recalc_er エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@staff_member_required
@require_POST
def buzz_run_deep_scan(request):
    """投稿不足アカウントの深掘りスキャンジョブを開始する API"""
    try:
        max_authors = int(request.POST.get('max_authors', 10))
        max_authors = max(1, min(max_authors, 5000))
        # 投稿不足解消を優先し、1アカウントあたりの取得深度を上げる
        max_scrolls = int(request.POST.get('max_scrolls', 30))
        max_scrolls = max(5, min(max_scrolls, 80))

        # 深掘り対象数を確認（フォロワー未取得 or 投稿不足 or プロフィール画像未取得 or 参加日未取得）
        target_count = THBuzzAuthor.objects.filter(
            is_excluded=False,
        ).filter(
            Q(followers_count__isnull=True) | Q(followers_count=0)
            | Q(total_post_count__lte=5) | Q(total_post_count__isnull=True)
            | Q(profile_pic_url='')
            | Q(raw_json__joined_at__isnull=True) | Q(raw_json__joined_at='')
        ).count()

        if target_count == 0:
            return JsonResponse({
                'ok': True,
                'message': '深掘り対象のアカウントがありません（全アカウントの情報が揃っています）',
                'job_id': None,
            })

        # ジョブレコード作成
        job = THBuzzSearchJob.objects.create(
            job_type='keyword',
            keywords=json.dumps(['deep_scan'], ensure_ascii=False),
            status='RUNNING',
            started_at=timezone.now(),
        )

        # バックグラウンドで深掘りスキャンコマンドを起動
        cmd = [
            sys.executable, 'manage.py', 'th_buzz_deep_scan',
            '--job-id', str(job.id),
            '--max-authors', str(max_authors),
            '--max-scrolls', str(max_scrolls),
        ]
        log_dir = settings.BASE_DIR / 'deploy'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_out = open(log_dir / 'buzz_deep_scan_stdout.log', 'a')
        log_err = open(log_dir / 'buzz_deep_scan_stderr.log', 'a')
        subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=log_out,
            stderr=log_err,
        )

        return JsonResponse({
            'ok': True,
            'message': f'深掘りスキャンを開始しました (ID: {job.id}, 対象: 最大{max_authors}件 / {target_count}件)',
            'job_id': job.id,
        })

    except Exception as e:
        logger.exception("buzz_run_deep_scan エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ─── メディアプロキシ ───

# Instagram CDN ドメインのホワイトリスト
_CDN_PATTERN = re.compile(r'^https://scontent[-\w]*\.cdninstagram\.com/')


@staff_member_required
def buzz_media_proxy(request):
    """Instagram CDN 画像/動画のプロキシ（CORP ヘッダー回避用）"""
    from django.http import HttpResponse

    url = request.GET.get('url', '')
    if not url or not _CDN_PATTERN.match(url):
        return HttpResponse(b'Invalid URL', status=400, content_type='text/plain')

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.threads.com/',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            response = HttpResponse(content, content_type=content_type)
            response['Cache-Control'] = 'public, max-age=86400'
            return response
    except Exception as e:
        logger.warning("buzz_media_proxy エラー: %s (url=%s)", e, url[:120])
        return HttpResponse(b'Fetch failed', status=502, content_type='text/plain')


# ─── 投稿パターン分析ヘルパー ───

def _calc_post_pattern_stats(posts, followers_count):
    """投稿パターンの統計を算出する"""
    from collections import Counter
    import re as _re

    stats = {
        'total_posts': len(posts),
        'hourly_heatmap': [[0]*24 for _ in range(7)],  # [dow][hour]
        'media_type_dist': {'text': 0, 'image': 0, 'video': 0, 'carousel': 0},
        'text_length_dist': {'short': 0, 'medium': 0, 'long': 0},  # <100, 100-300, >300
        'viral_posts_count': 0,
        'avg_text_length': 0,
        'avg_viral_text_length': 0,
        'er_trend': [],  # [{date, er}]
        'top_words': [],  # [{word, count}]
        'hashtag_freq': [],  # [{tag, count}]
        'posting_freq_weekly': 0,
    }

    if not posts:
        return stats

    text_lengths = []
    viral_text_lengths = []
    word_counter = Counter()
    hashtag_counter = Counter()
    er_data = []

    # ストップワード
    STOPWORDS = {
        'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ',
        'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として', 'い', 'や',
        'ない', 'この', 'ため', 'その', 'あと', 'よう', 'なる', 'まで', 'また',
        'どの', 'https', 'http', 'www', 'com', 'jp', 'co', 'net',
    }

    for p in posts:
        # 時間帯ヒートマップ
        if p.posted_at:
            dow = p.posted_at.weekday()  # 0=Mon
            hour = p.posted_at.hour
            stats['hourly_heatmap'][dow][hour] += 1

        # メディアタイプ分布
        mt = (p.media_type or 'text').lower()
        if mt in stats['media_type_dist']:
            stats['media_type_dist'][mt] += 1
        else:
            stats['media_type_dist']['text'] += 1

        # テキスト長分布
        tlen = len(p.text_content or '')
        text_lengths.append(tlen)
        if tlen < 100:
            stats['text_length_dist']['short'] += 1
        elif tlen < 300:
            stats['text_length_dist']['medium'] += 1
        else:
            stats['text_length_dist']['long'] += 1

        # バズ投稿
        if p.is_viral:
            stats['viral_posts_count'] += 1
            viral_text_lengths.append(tlen)

        # ER推移データ
        if p.posted_at and p.engagement_rate is not None:
            er_data.append({
                'date': p.posted_at.strftime('%Y-%m-%d'),
                'er': round(p.engagement_rate, 2),
            })

        # テキスト解析（簡易形態素解析: 2-6文字の連続カタカナ/漢字を抽出）
        text = p.text_content or ''
        # ハッシュタグ
        tags = _re.findall(r'[#＃]([\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+)', text)
        for tag in tags:
            hashtag_counter[tag] += 1

        # 単語抽出（カタカナ3文字以上 or 漢字2文字以上）
        katakana_words = _re.findall(r'[\u30A0-\u30FF]{3,}', text)
        kanji_words = _re.findall(r'[\u4E00-\u9FFF]{2,6}', text)
        for w in katakana_words + kanji_words:
            if w.lower() not in STOPWORDS and len(w) >= 2:
                word_counter[w] += 1

    stats['avg_text_length'] = round(sum(text_lengths) / len(text_lengths)) if text_lengths else 0
    stats['avg_viral_text_length'] = round(sum(viral_text_lengths) / len(viral_text_lengths)) if viral_text_lengths else 0

    # ER推移（日付順）
    er_data.sort(key=lambda x: x['date'])
    stats['er_trend'] = er_data[-50:]  # 直近50件

    # 頻出ワード Top20
    stats['top_words'] = [{'word': w, 'count': c} for w, c in word_counter.most_common(20)]

    # ハッシュタグ Top15
    stats['hashtag_freq'] = [{'tag': t, 'count': c} for t, c in hashtag_counter.most_common(15)]

    # 週あたり投稿頻度
    dated_posts = [p for p in posts if p.posted_at]
    if len(dated_posts) >= 2:
        sorted_dates = sorted(p.posted_at for p in dated_posts)
        span_days = max((sorted_dates[-1] - sorted_dates[0]).days, 1)
        stats['posting_freq_weekly'] = round(len(dated_posts) / span_days * 7, 1)

    return stats


# ─── 構造化分析メモ保存 API ───

@staff_member_required
@require_POST
def buzz_save_analysis(request, pk):
    """構造化分析メモを保存する API"""
    author = get_object_or_404(THBuzzAuthor, pk=pk)
    analysis, _ = THBuzzAuthorAnalysis.objects.get_or_create(author=author)

    fields = [
        'factor_profile', 'factor_concept', 'factor_content',
        'factor_format', 'factor_frequency', 'factor_engagement',
        'factor_funnel', 'factor_other',
        'overall_assessment', 'concept_inspiration', 'differentiation_idea',
    ]
    for f in fields:
        val = request.POST.get(f, '').strip()
        setattr(analysis, f, val)
    analysis.save()

    # 分析済みフラグ更新
    has_content = analysis.has_content()
    if has_content != author.is_analyzed:
        author.is_analyzed = has_content
        author.save(update_fields=['is_analyzed'])

    return JsonResponse({'ok': True, 'is_analyzed': has_content})


# ─── 自動巡回パイプライン手動実行 API ───

@staff_member_required
@require_POST
def buzz_run_pipeline(request):
    """自動巡回パイプラインを手動で実行開始する API"""
    from pathlib import Path

    dry_run = request.POST.get('dry_run', '') == '1'
    cmd = [sys.executable, 'manage.py', 'th_buzz_auto_pipeline', '-v', '2']
    if dry_run:
        cmd.append('--dry-run')

    log_dir = Path(settings.BASE_DIR) / 'deploy'
    log_dir.mkdir(parents=True, exist_ok=True)

    try:
        log_out = open(log_dir / 'pipeline_stdout.log', 'a')
        log_err = open(log_dir / 'pipeline_stderr.log', 'a')
        subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=log_out,
            stderr=log_err,
        )
        return JsonResponse({'ok': True, 'message': 'パイプライン実行を開始しました'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ─── 類似アカウント自動発見 ───


@staff_member_required
def buzz_find_similar(request, pk):
    """類似アカウントを検索する API（GET）"""
    from th.services.similar_finder import extract_search_keywords, find_similar_authors

    author = get_object_or_404(THBuzzAuthor, pk=pk)

    try:
        keywords = extract_search_keywords(author)
        results = find_similar_authors(author, keywords, max_results=15)

        return JsonResponse({
            'ok': True,
            'keywords': keywords,
            'results': results,
        })
    except Exception as e:
        logger.exception("buzz_find_similar エラー")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ─── NGワードチェッカー ───


@staff_member_required
def buzz_ng_checker(request):
    """NGワードチェッカー画面"""
    return render(request, 'admin/console/buzz_ng_checker.html', {
        'title': 'NGワードチェッカー',
    })


@staff_member_required
@require_POST
def buzz_ng_check_api(request):
    """NGワードチェック API（POST）"""
    from th.services.ng_word_checker import check_ng_words

    try:
        body = json.loads(request.body)
        text = body.get('text', '')
    except (json.JSONDecodeError, AttributeError):
        text = request.POST.get('text', '')

    if not text.strip():
        return JsonResponse({'ok': False, 'error': 'テキストを入力してください'}, status=400)

    result = check_ng_words(text)
    return JsonResponse({'ok': True, **result})
