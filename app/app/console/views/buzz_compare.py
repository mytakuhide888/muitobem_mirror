# -*- coding: utf-8 -*-
"""
アカウント比較画面 - Views
"""
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render

from th.models import THBuzzAuthor
from .buzz import _calc_post_pattern_stats


@staff_member_required
def buzz_compare(request):
    """複数アカウントの比較画面（最大5件）"""

    ids_raw = request.GET.get('ids', '')
    if not ids_raw:
        raise Http404('比較対象のIDが指定されていません')

    try:
        author_ids = [int(x.strip()) for x in ids_raw.split(',') if x.strip()]
    except (ValueError, TypeError):
        raise Http404('IDの形式が不正です')

    if len(author_ids) < 2:
        raise Http404('比較には2件以上のアカウントが必要です')
    if len(author_ids) > 5:
        author_ids = author_ids[:5]

    authors = list(THBuzzAuthor.objects.filter(pk__in=author_ids))
    if len(authors) < 2:
        raise Http404('指定されたアカウントが見つかりません')

    # 各アカウントの比較データを構築
    compare_data = []
    all_genre_tags = []
    all_monet_signals = []

    for author in authors:
        all_posts = list(author.buzz_posts.all())
        pattern_stats = _calc_post_pattern_stats(all_posts, author.followers_count or 0)

        # 分析メモの取得
        analysis = None
        try:
            from th.models import THBuzzAuthorAnalysis
            analysis = THBuzzAuthorAnalysis.objects.filter(author=author).first()
        except Exception:
            pass

        genre_tags = author.genre_tags or []
        monet_signals = author.monetization_signals or []
        all_genre_tags.append(set(genre_tags))
        all_monet_signals.append(set(monet_signals))

        compare_data.append({
            'author': author,
            'pattern_stats': json.dumps(pattern_stats, ensure_ascii=False),
            'analysis': analysis,
            'genre_tags': genre_tags,
            'monet_signals': monet_signals,
        })

    # 共通キーワード検出（ジャンルタグの集合演算）
    common_keywords = []
    if all_genre_tags:
        common_set = all_genre_tags[0]
        for s in all_genre_tags[1:]:
            common_set = common_set & s
        common_keywords = sorted(common_set)

    ctx = {
        'title': 'アカウント比較',
        'compare_data': compare_data,
        'common_keywords': common_keywords,
    }
    return render(request, 'admin/console/buzz_compare.html', ctx)
