# -*- coding: utf-8 -*-
"""
類似アカウント自動発見サービス

DB内の THBuzzAuthor から、指定アカウントに類似するアカウントを
キーワードマッチ + スコアリングで検索する。
"""

import re
import logging
from typing import Dict, List

from django.db.models import Q

from th.services.fortune_classifier import FORTUNE_KEYWORDS, _flatten_keywords

logger = logging.getLogger(__name__)

# ストップワード（検索キーワードから除外）
_STOPWORDS = {
    'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ',
    'ある', 'いる', 'する', 'から', 'こと', 'ない', 'この', 'その', 'よう',
    'ため', 'また', 'なる', 'まで', 'どの', 'もの', 'それ', 'これ', 'あの',
}


def extract_search_keywords(author) -> List[str]:
    """
    アカウントから類似検索用のキーワードを抽出する。

    優先順:
    1. genre_tags から占い関連キーワード（最高優先度）
    2. bio からカタカナ3文字以上 + 漢字2-6文字
    3. バズ投稿の頻出ワード
    """
    keywords_scored = {}  # {keyword: score}

    # 占い関連キーワードの一覧（優先度判定用）
    fortune_kw_set = set()
    for kw, _ in _flatten_keywords(FORTUNE_KEYWORDS):
        fortune_kw_set.add(kw)

    # 1. genre_tags（最高優先度）
    genre_tags = author.genre_tags or []
    for tag in genre_tags:
        score = 10.0 if tag in fortune_kw_set else 5.0
        keywords_scored[tag] = max(keywords_scored.get(tag, 0), score)

    # 2. bio からキーワード抽出
    bio = author.bio or ''
    if bio:
        katakana = re.findall(r'[\u30A0-\u30FF]{3,}', bio)
        kanji = re.findall(r'[\u4E00-\u9FFF]{2,6}', bio)
        for w in katakana + kanji:
            if w in _STOPWORDS or len(w) < 2:
                continue
            score = 6.0 if w in fortune_kw_set else 3.0
            keywords_scored[w] = max(keywords_scored.get(w, 0), score)

    # 3. バズ投稿からの頻出ワード
    from collections import Counter
    word_counter = Counter()
    viral_posts = list(
        author.buzz_posts.filter(is_viral=True)
        .order_by('-engagement_score')
        .values_list('text_content', flat=True)[:10]
    )
    for text in viral_posts:
        if not text:
            continue
        katakana = re.findall(r'[\u30A0-\u30FF]{3,}', text)
        kanji = re.findall(r'[\u4E00-\u9FFF]{2,6}', text)
        for w in katakana + kanji:
            if w not in _STOPWORDS and len(w) >= 2:
                word_counter[w] += 1

    for w, count in word_counter.most_common(20):
        if w not in keywords_scored:
            score = 4.0 if w in fortune_kw_set else 2.0
            keywords_scored[w] = score

    # 占い関連度の高いワードを優先してトップ5
    sorted_kws = sorted(keywords_scored.items(), key=lambda x: -x[1])
    return [kw for kw, _ in sorted_kws[:5]]


def find_similar_authors(source_author, keywords: List[str], max_results: int = 15) -> List[Dict]:
    """
    キーワードでDB内の THBuzzAuthor を検索し、類似度スコアで順位付けする。

    Args:
        source_author: 検索元の THBuzzAuthor
        keywords: extract_search_keywords() で取得したキーワード
        max_results: 最大結果件数

    Returns:
        [{id, username, display_name, bio, scores, match_reasons}, ...]
    """
    from th.models import THBuzzAuthor

    if not keywords:
        return []

    # キーワードで OR 検索（bio / display_name / genre_tags）
    q_filter = Q()
    for kw in keywords:
        q_filter |= Q(bio__icontains=kw)
        q_filter |= Q(display_name__icontains=kw)
        q_filter |= Q(genre_tags__icontains=kw)

    candidates = (
        THBuzzAuthor.objects
        .filter(q_filter)
        .exclude(pk=source_author.pk)
        .exclude(is_excluded=True)
        [:200]  # パフォーマンスのため上限
    )

    source_genre = set(source_author.genre_tags or [])
    source_monet = set(source_author.monetization_signals or [])
    source_bio_words = set(
        re.findall(r'[\u30A0-\u30FF]{3,}|[\u4E00-\u9FFF]{2,6}', source_author.bio or '')
    )

    results = []
    for candidate in candidates:
        score = 0.0
        reasons = []

        # ジャンルタグ重複
        cand_genre = set(candidate.genre_tags or [])
        genre_overlap = source_genre & cand_genre
        if genre_overlap:
            score += len(genre_overlap) * 15
            reasons.append(f"ジャンルタグ共通: {', '.join(sorted(genre_overlap))}")

        # マネタイズシグナル重複
        cand_monet = set(candidate.monetization_signals or [])
        monet_overlap = source_monet & cand_monet
        if monet_overlap:
            score += len(monet_overlap) * 5
            reasons.append(f"マネタイズ共通: {', '.join(sorted(monet_overlap))}")

        # bioキーワード重複
        cand_bio_words = set(
            re.findall(r'[\u30A0-\u30FF]{3,}|[\u4E00-\u9FFF]{2,6}', candidate.bio or '')
        )
        bio_overlap = source_bio_words & cand_bio_words - _STOPWORDS
        if bio_overlap:
            score += len(bio_overlap) * 3
            overlap_display = sorted(bio_overlap)[:5]
            reasons.append(f"bioワード共通: {', '.join(overlap_display)}")

        # 検索キーワードマッチ
        cand_text = (candidate.bio or '') + ' ' + (candidate.display_name or '')
        cand_genre_str = ' '.join(candidate.genre_tags or [])
        for kw in keywords:
            if kw in cand_genre_str:
                score += 8
                reasons.append(f"キーワード'{kw}'がジャンルタグにマッチ")
            elif kw in cand_text:
                score += 5
                reasons.append(f"キーワード'{kw}'がbio/名前にマッチ")

        # 成長スコアボーナス
        if candidate.growth_score:
            bonus = min(candidate.growth_score / 10, 10)
            score += bonus

        if score > 0:
            results.append({
                'id': candidate.pk,
                'username': candidate.username,
                'display_name': candidate.display_name or candidate.username,
                'bio': (candidate.bio or '')[:200],
                'profile_pic_url': candidate.profile_pic_url or '',
                'followers_count': candidate.followers_count,
                'growth_score': candidate.growth_score,
                'fortune_relevance_score': candidate.fortune_relevance_score,
                'similarity_score': round(score, 1),
                'match_reasons': reasons[:5],
            })

    # スコア降順で上位を返す
    results.sort(key=lambda x: -x['similarity_score'])
    return results[:max_results]
