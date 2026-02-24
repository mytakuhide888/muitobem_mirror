# -*- coding: utf-8 -*-
"""
占い属性分類サービス

バズアカウントが占い・スピリチュアル系かどうかを判定し、
コンセプト設計のためのリサーチ適合スコアを算出する。
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── 占い・スピ系キーワード辞書 ───
# 重み: 高い = より特殊で占い専門性が高い、低い = 一般的にも使われうる

FORTUNE_KEYWORDS: Dict[str, List[Tuple[str, float]]] = {
    # --- 占術名（高い専門性）---
    'divination_methods': [
        ('タロット', 3.0), ('タロットカード', 3.0), ('オラクルカード', 3.0),
        ('ルノルマン', 3.5), ('ルノルマンカード', 3.5),
        ('西洋占星術', 3.5), ('ホロスコープ', 3.0), ('アストロ', 2.0),
        ('四柱推命', 3.5), ('算命学', 3.5), ('紫微斗数', 4.0),
        ('宿曜', 3.5), ('宿曜占星術', 3.5),
        ('数秘術', 3.0), ('数秘', 3.0),
        ('手相', 2.5), ('人相', 2.5), ('姓名判断', 3.0),
        ('風水', 2.5), ('九星気学', 3.5), ('九星', 3.0),
        ('易', 2.0), ('易占い', 3.0), ('周易', 3.5),
        ('六壬', 4.0), ('奇門遁甲', 4.0), ('断易', 4.0),
        ('霊感', 2.5), ('透視', 2.5), ('霊視', 3.0),
        ('チャネリング', 3.0), ('リーディング', 2.0),
        ('カードリーディング', 3.0), ('サイキック', 3.0),
        ('五星三心', 3.5), ('五星三心占い', 4.0),
        ('オリエンタル占星術', 4.0), ('マヤ暦', 3.5),
        ('インド占星術', 3.5), ('ジョーティシュ', 4.0),
    ],

    # --- スピリチュアル用語 ---
    'spiritual_terms': [
        ('スピリチュアル', 2.5), ('スピ', 1.5),
        ('ツインレイ', 4.0), ('ツインソウル', 3.5), ('ツインフレーム', 3.5),
        ('ソウルメイト', 3.0), ('魂の伴侶', 3.0),
        ('アセンション', 3.5), ('覚醒', 1.5), ('意識の覚醒', 3.0),
        ('ライトワーカー', 3.5), ('スターシード', 3.5),
        ('アカシックレコード', 4.0), ('アカシック', 3.5),
        ('インナーチャイルド', 2.5), ('ハイヤーセルフ', 3.0),
        ('チャクラ', 2.5), ('オーラ', 2.0), ('波動', 2.0),
        ('エンジェルナンバー', 3.5), ('エンジェル', 1.5),
        ('ヒーリング', 2.0), ('レイキ', 2.5), ('エネルギーワーク', 2.5),
        ('パワーストーン', 3.0), ('天然石', 1.5), ('クリスタル', 1.5),
        ('浄化', 1.5), ('お清め', 1.5), ('セージ', 1.5),
        ('前世', 2.5), ('カルマ', 2.5), ('因果', 1.5),
        ('引き寄せ', 2.0), ('引き寄せの法則', 3.0),
        ('マニフェスト', 2.0), ('願望実現', 2.5),
        ('宇宙の法則', 2.5), ('宇宙エネルギー', 2.5),
        ('高次元', 2.5), ('次元上昇', 3.0),
        ('ゼロポイント', 3.5), ('スーパーコンジャンクション', 4.0),
        ('ディバインマスキュリン', 3.5), ('ディバインフェミニン', 3.5),
        ('神聖な結合', 3.0), ('ミラーソウル', 3.5),
    ],

    # --- 有名占い師・メソッド（日本市場特化）---
    'famous_figures': [
        ('ゲッターズ飯田', 4.0), ('水晶玉子', 4.0),
        ('細木数子', 3.5), ('細木かおり', 3.5),
        ('しいたけ占い', 4.0), ('しいたけ', 1.5),
        ('石井ゆかり', 3.5), ('鏡リュウジ', 3.5),
        ('中園ミホ', 3.0), ('星ひとみ', 3.5),
        ('琉球風水', 3.5), ('大串ノリコ', 3.5),
        ('スピ童貞', 3.0), ('木下レオン', 3.5),
        ('Love Me Do', 3.0), ('ラブちゃん', 2.5),
    ],

    # --- 星座・12星座 ---
    'zodiac': [
        ('12星座', 3.0), ('星座占い', 3.0), ('星座', 1.5),
        ('おひつじ座', 2.5), ('牡羊座', 2.5), ('おうし座', 2.5), ('牡牛座', 2.5),
        ('ふたご座', 2.5), ('双子座', 2.5), ('かに座', 2.5), ('蟹座', 2.5),
        ('しし座', 2.5), ('獅子座', 2.5), ('おとめ座', 2.5), ('乙女座', 2.5),
        ('てんびん座', 2.5), ('天秤座', 2.5), ('さそり座', 2.5), ('蠍座', 2.5),
        ('いて座', 2.5), ('射手座', 2.5), ('やぎ座', 2.5), ('山羊座', 2.5),
        ('みずがめ座', 2.5), ('水瓶座', 2.5), ('うお座', 2.5), ('魚座', 2.5),
        ('月星座', 3.0), ('太陽星座', 3.0), ('上昇星座', 3.0),
        ('アセンダント', 3.5), ('MC', 1.0), ('ハウス', 1.0),
    ],

    # --- 恋愛・悩み系（占い顧客の悩みキーワード）---
    'love_concerns': [
        ('復縁', 3.0), ('片思い', 2.0), ('両想い', 2.0),
        ('不倫', 2.0), ('二股', 2.0), ('離婚', 1.5),
        ('縁結び', 3.0), ('良縁', 2.5), ('相性', 1.5), ('相性占い', 3.0),
        ('運命の人', 2.5), ('赤い糸', 2.0),
        ('恋愛運', 3.0), ('結婚運', 3.0), ('出会い運', 3.0),
    ],

    # --- 金運・開運・暦 ---
    'fortune_calendar': [
        ('金運', 3.0), ('財運', 3.0), ('臨時収入', 2.5), ('宝くじ', 1.5),
        ('開運', 2.5), ('開運日', 3.5), ('運気', 2.5), ('運勢', 2.5),
        ('天赦日', 4.0), ('一粒万倍日', 4.0), ('寅の日', 3.5), ('巳の日', 3.5),
        ('己巳の日', 4.0), ('甲子の日', 3.5),
        ('大安', 2.0), ('不成就日', 3.5), ('仏滅', 1.5),
        ('六曜', 3.0), ('暦', 1.5),
        ('最強開運日', 4.0), ('吉日', 2.5),
        ('満月', 2.0), ('新月', 2.0), ('満月の日', 2.5), ('新月の願い事', 3.5),
        ('月のリズム', 3.0), ('月の暦', 3.0),
        ('春分', 1.5), ('秋分', 1.5), ('冬至', 1.5), ('夏至', 1.5),
        ('水星逆行', 4.0), ('惑星逆行', 3.5), ('レトログレード', 3.0),
        ('グランドクロス', 3.5), ('コンジャンクション', 3.5),
        ('風の時代', 3.5), ('地の時代', 3.0),
    ],

    # --- 占いコンテンツ関連 ---
    'fortune_content': [
        ('占い', 2.0), ('占い師', 3.0), ('鑑定', 3.0), ('鑑定士', 3.0),
        ('鑑定書', 3.5), ('無料鑑定', 4.0), ('有料鑑定', 4.0),
        ('今日の運勢', 3.0), ('今週の運勢', 3.0), ('今月の運勢', 3.0),
        ('〇〇年運勢', 3.0), ('年間運勢', 3.0),
        ('おみくじ', 2.0), ('厄年', 2.5), ('厄除け', 2.0),
        ('パワースポット', 2.0), ('お守り', 1.5), ('御朱印', 1.5),
        ('ユニバーサルイヤーナンバー', 4.0), ('パーソナルイヤーナンバー', 4.0),
    ],

    # --- 年間イベント・時期キーワード ---
    'seasonal': [
        ('節分', 1.5), ('立春', 2.0), ('二十四節気', 3.0),
        ('お彼岸', 1.5), ('七夕', 1.0), ('お盆', 1.0),
        ('年末年始', 1.0), ('初詣', 1.5),
        ('恵方', 2.0), ('恵方巻', 1.0),
    ],
}

# --- マネタイズシグナル ---
MONETIZATION_SIGNALS: List[Tuple[str, float]] = [
    ('鑑定', 3.0), ('有料', 2.5), ('無料鑑定', 3.5),
    ('STORES', 4.0), ('stores', 4.0), ('BASE', 2.0),
    ('LINE', 1.5), ('公式LINE', 3.0), ('LINE登録', 2.5),
    ('募集中', 2.0), ('受付中', 2.0), ('受付開始', 2.5),
    ('限定', 1.5), ('残り', 1.5), ('満席', 2.0),
    ('お申込み', 2.5), ('お申し込み', 2.5), ('申込', 2.0),
    ('プロフのリンク', 2.0), ('リンクから', 1.5),
    ('セッション', 1.5), ('個別セッション', 3.0),
    ('モニター', 2.0), ('モニター募集', 3.0),
    ('DMください', 2.5), ('DM下さい', 2.5),
    ('ココナラ', 3.0), ('coconala', 3.0),
    ('電話占い', 3.5), ('チャット占い', 3.5),
]

# --- マネタイズURL パターン（bio内リンクのドメイン解析用）---
MONETIZATION_URL_PATTERNS: List[Tuple[str, float]] = [
    (r'stores\.jp', 4.0), (r'thebase\.in', 3.5), (r'lin\.ee', 3.5),
    (r'lit\.link', 3.0), (r'linktr\.ee', 2.5), (r'coconala\.com', 3.5),
    (r'mosh\.jp', 3.0), (r'note\.com', 1.5), (r'line\.me', 3.0),
    (r'potofu\.me', 2.5), (r'peraichi\.com', 2.5),
]

# --- 非占い属性キーワード ---
# 注意: 占い投稿にも含まれうるワードは除外済み（ダイエット、料理、美容等）
NON_FORTUNE_KEYWORDS: List[Tuple[str, float]] = [
    # IT・ビジネス系
    ('プログラミング', 3.0), ('エンジニア', 2.5), ('プログラマー', 3.0),
    ('React', 3.0), ('Python', 3.0), ('JavaScript', 3.0),
    ('コンサル', 2.0), ('コンサルタント', 2.5), ('マーケティング', 2.0),
    ('SEO', 2.5), ('アフィリエイト', 2.5),
    # 金融・投資
    ('FX', 2.5), ('株取引', 2.5), ('仮想通貨', 2.5), ('ビットコイン', 2.5),
    ('デイトレ', 2.5), ('トレーダー', 2.0),
    # スポーツ・フィットネス
    ('筋トレ', 2.5), ('ベンチプレス', 3.0), ('デッドリフト', 3.0),
    ('マラソン', 2.5), ('サッカー', 2.5), ('野球', 2.5),
    # 政治・ニュース
    ('選挙', 2.0), ('政治', 2.0), ('国会', 2.5),
    # 芸能（占い師でない有名人）
    ('YouTuber', 1.5), ('配信者', 1.5), ('ゲーム実況', 2.5),
]


def _flatten_keywords(category_dict: Dict[str, List[Tuple[str, float]]]) -> List[Tuple[str, float]]:
    """カテゴリ辞書をフラットなリストに変換"""
    result = []
    for keywords in category_dict.values():
        result.extend(keywords)
    return result


def _count_keyword_hits(text: str, keywords: List[Tuple[str, float]]) -> Tuple[float, List[str]]:
    """
    テキストからキーワードのヒット数とスコアを算出。
    戻り値: (加重スコア合計, ヒットしたキーワードリスト)
    """
    if not text:
        return 0.0, []

    text_lower = text.lower()
    total_score = 0.0
    hits = []
    seen = set()

    for keyword, weight in keywords:
        kw_lower = keyword.lower()
        if kw_lower in text_lower and kw_lower not in seen:
            total_score += weight
            hits.append(keyword)
            seen.add(kw_lower)

    return total_score, hits


def _detect_monetization_urls(text: str) -> Tuple[float, List[str]]:
    """
    テキスト内のURLからマネタイズ関連ドメインを検出する。
    戻り値: (加重スコア合計, マッチしたドメインパターンリスト)
    """
    if not text:
        return 0.0, []

    # URL を抽出
    urls = re.findall(r'https?://[^\s<>"\']+|(?:[\w-]+\.)+[a-z]{2,}[/\w.-]*', text.lower())
    if not urls:
        return 0.0, []

    total_score = 0.0
    hits = []
    seen = set()

    for url in urls:
        for pattern, weight in MONETIZATION_URL_PATTERNS:
            if pattern not in seen and re.search(pattern, url):
                total_score += weight
                hits.append(pattern.replace(r'\.', '.'))
                seen.add(pattern)

    return total_score, hits


def classify_fortune_relevance(
    bio: str,
    post_texts: List[str],
    display_name: str = '',
    followers_count: Optional[int] = None,
    total_post_count: Optional[int] = None,
) -> Dict:
    """
    アカウントの占い・スピリチュアル属性を分類する。

    Args:
        bio: プロフィールの自己紹介
        post_texts: 投稿テキストのリスト
        display_name: 表示名

    Returns:
        {
            'fortune_relevance_score': float (0-100),
            'genre_score': float (0-100),
            'monetization_score': float (0-100),
            'genre_tags': list[str],           # 検出されたジャンルタグ
            'monetization_signals': list[str], # 検出されたマネタイズシグナル
            'non_fortune_score': float,        # 非占い属性スコア
            'auto_exclude': bool,              # 自動対象外にすべきか
            'auto_exclude_reason': str,        # 理由
            'category_breakdown': dict,        # カテゴリ別スコア
        }
    """
    all_fortune_kw = _flatten_keywords(FORTUNE_KEYWORDS)

    # --- bio の分析（重み2倍: プロフィールは意図が強い）---
    combined_name_bio = f"{display_name} {bio}"
    bio_score, bio_hits = _count_keyword_hits(combined_name_bio, all_fortune_kw)
    bio_score *= 2.0  # bio は重み倍増

    bio_monet_score, bio_monet_hits = _count_keyword_hits(combined_name_bio, MONETIZATION_SIGNALS)
    bio_monet_score *= 2.0

    # bio内URL解析によるマネタイズ度加算
    bio_url_score, bio_url_hits = _detect_monetization_urls(combined_name_bio)
    bio_monet_score += bio_url_score * 2.0  # bio重み倍増を適用

    bio_non_score, bio_non_hits = _count_keyword_hits(combined_name_bio, NON_FORTUNE_KEYWORDS)
    bio_non_score *= 2.0

    # --- 投稿テキストの分析 ---
    post_fortune_score = 0.0
    post_fortune_hits = set()
    post_monet_score = 0.0
    post_monet_hits = set()
    post_non_score = 0.0
    all_post_text = ''

    total_weight = 0.0
    for i, text in enumerate(post_texts):
        if not text:
            continue
        all_post_text += ' ' + text

        # 直近重み付け（index 0=最新）
        if i < 5:
            w = 2.0
        elif i < 10:
            w = 1.5
        elif i < 20:
            w = 1.0
        else:
            w = 0.7
        total_weight += w

        score, hits = _count_keyword_hits(text, all_fortune_kw)
        post_fortune_score += score * w
        post_fortune_hits.update(hits)

        m_score, m_hits = _count_keyword_hits(text, MONETIZATION_SIGNALS)
        post_monet_score += m_score * w
        post_monet_hits.update(m_hits)

        n_score, _ = _count_keyword_hits(text, NON_FORTUNE_KEYWORDS)
        post_non_score += n_score * w

    # 加重合計で正規化（直近重み付けに対応）
    total_weight = max(total_weight, 1.0)
    post_fortune_avg = post_fortune_score / total_weight
    post_non_avg = post_non_score / total_weight

    # --- カテゴリ別ブレイクダウン ---
    category_breakdown = {}
    for cat_name, cat_keywords in FORTUNE_KEYWORDS.items():
        _, cat_hits = _count_keyword_hits(all_post_text + ' ' + combined_name_bio, cat_keywords)
        category_breakdown[cat_name] = cat_hits

    # --- ジャンルタグ（ユニークなヒットキーワード）---
    all_genre_hits = set(bio_hits) | post_fortune_hits
    all_monet_hits = set(bio_monet_hits) | set(bio_url_hits) | post_monet_hits

    # --- ジャンル適合度スコア (0-100) ---
    # bio にキーワードがある = 非常に強いシグナル
    # 投稿にキーワードがある = 中程度のシグナル
    raw_genre = bio_score + post_fortune_avg * 5  # 投稿平均を増幅
    genre_score = min(raw_genre / 15.0 * 100, 100)  # 15点で100%に正規化

    # --- マネタイズ度スコア (0-100) ---
    raw_monet = bio_monet_score + post_monet_score / total_weight * 3
    monetization_score = min(raw_monet / 10.0 * 100, 100)

    # --- 非占い属性スコア ---
    non_fortune_total = bio_non_score + post_non_avg * 3

    # --- 自動対象外判定 ---
    auto_exclude = False
    auto_exclude_reason = ''

    if genre_score < 5.0 and non_fortune_total > 10.0:
        auto_exclude = True
        auto_exclude_reason = f'占い関連キーワードが極めて少なく、非占い属性が強い (non_fortune={non_fortune_total:.1f})'
    elif genre_score < 3.0 and len(all_genre_hits) == 0 and bio.strip():
        auto_exclude = True
        auto_exclude_reason = 'bio/投稿に占い関連キーワードが一切含まれていない'

    # --- 占いリサーチ適合スコア (0-100) ---
    # ジャンル適合度(40%) + マネタイズ度(15%) を genre_score と monetization_score から
    # 成長力(25%) + エンゲージ品質(20%) は呼び出し元の update_growth_stats() で統合
    fortune_relevance_score = round(
        genre_score * 0.70 + monetization_score * 0.30,
        1,
    )

    # 非占い属性が強い場合はペナルティ
    if non_fortune_total > 5.0:
        penalty = min(non_fortune_total / 20.0 * 30, 30)  # 最大30点減
        fortune_relevance_score = max(fortune_relevance_score - penalty, 0)

    # フォロワー/投稿比率の信頼度補正
    # フォロワーが多いのに投稿が極端に少ない → 買いフォロワーや非活動の疑い
    if (followers_count is not None and followers_count > 100
            and total_post_count is not None):
        min_expected_posts = followers_count / 500
        if total_post_count < min_expected_posts:
            ratio = total_post_count / max(min_expected_posts, 1)
            fp_penalty = min((1 - ratio) * 15, 15)  # 最大15点減
            fortune_relevance_score = max(fortune_relevance_score - fp_penalty, 0)

    return {
        'fortune_relevance_score': round(fortune_relevance_score, 1),
        'genre_score': round(genre_score, 1),
        'monetization_score': round(monetization_score, 1),
        'genre_tags': sorted(all_genre_hits),
        'monetization_signals': sorted(all_monet_hits),
        'non_fortune_score': round(non_fortune_total, 1),
        'auto_exclude': auto_exclude,
        'auto_exclude_reason': auto_exclude_reason,
        'category_breakdown': {
            k: v for k, v in category_breakdown.items() if v
        },
    }


def update_author_fortune_classification(author) -> Dict:
    """
    THBuzzAuthor インスタンスの占い属性を分類し、フィールドをセットする。
    save() は呼ばない（呼び出し元で一括 save する前提）。

    Args:
        author: THBuzzAuthor インスタンス

    Returns:
        classify_fortune_relevance の結果辞書
    """
    from th.models import THBuzzPost

    # 投稿テキストを取得（最新50件まで）
    post_texts = list(
        THBuzzPost.objects.filter(author=author)
        .order_by('-posted_at')
        .values_list('text_content', flat=True)[:50]
    )

    result = classify_fortune_relevance(
        bio=author.bio or '',
        post_texts=post_texts,
        display_name=author.display_name or '',
        followers_count=author.followers_count,
        total_post_count=author.total_post_count,
    )

    # モデルフィールドをセット（save は呼ばない）
    author.fortune_relevance_score = result['fortune_relevance_score']
    author.genre_tags = result['genre_tags']
    author.monetization_signals = result['monetization_signals']

    # 自動対象外（手動で外した場合は上書きしない）
    if result['auto_exclude'] and not author.is_excluded:
        author.is_excluded = True
        author.auto_excluded_reason = result['auto_exclude_reason']
        logger.info(
            'Auto-excluded @%s: %s', author.username, result['auto_exclude_reason']
        )
    elif not result['auto_exclude']:
        author.auto_excluded_reason = ''

    return result

