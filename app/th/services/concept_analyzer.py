# -*- coding: utf-8 -*-
"""コンセプト設計 — AI分析・コンセプト生成サービス"""
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

MODEL_ID = 'claude-haiku-4-5-20251001'


# ─── Step 2: 個別アカウント分析 ───

ANALYSIS_PROMPT = """\
以下はThreadsで急成長している占いアカウントの情報です。
このアカウントが「なぜ伸びているか」を分析してください。

【アカウント情報】
- 表示名: {display_name}
- ユーザー名: @{username}
- bio: {bio}
- フォロワー: {followers_count}
- アカウント日数: {account_age_days}日
- 成長スコア: {growth_score}
- 平均いいね: {avg_likes}
- 平均リプライ: {avg_replies}

【バズ投稿（上位5件）】
{top_posts}

【投稿全体の傾向】
- 投稿数: {total_post_count}
- 投稿頻度: 約{post_frequency}件/日

【分析の観点（必ず全て回答）】
1. コンテンツの型（代弁型/断言型/チェックリスト型/DM誘導型 等）
2. 感情のフック（どの感情に刺さっているか）
3. 運用面の強み（テンプレ化の容易さ、導線設計）
4. キャラクターの特徴（占術、口調、世界観、ターゲット）
5. 再現すべき骨格（上記から導かれる、パクるべき構造）3つ以上

【出力形式】
以下のJSON形式で出力してください。各項目は日本語で簡潔に。
```json
{{
  "content_type": "コンテンツの型の説明",
  "emotion_hook": "感情フックの説明",
  "operation_strength": "運用面の強みの説明",
  "character_traits": "キャラクター特徴の説明",
  "reproducible_bones": ["骨格1", "骨格2", "骨格3"],
  "summary": "このアカウントが伸びている理由を3文でまとめ"
}}
```"""


def _get_client():
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY が設定されていません')
    return anthropic.Anthropic(api_key=api_key)


def _format_top_posts(posts):
    """THBuzzPost のクエリセットからプロンプト用テキストを生成"""
    lines = []
    for i, p in enumerate(posts, 1):
        likes = p.like_count or 0
        replies = p.reply_count or 0
        text = (p.text_content or '')[:300]
        lines.append(f"[{i}] いいね:{likes} リプ:{replies}\n{text}")
    return "\n\n".join(lines) if lines else "(投稿データなし)"


def _extract_text_block(raw: str) -> str:
    if '```json' in raw:
        return raw.split('```json')[1].split('```')[0].strip()
    if '```' in raw:
        return raw.split('```')[1].split('```')[0].strip()
    return raw.strip()


def analyze_author(author) -> dict:
    """THBuzzAuthor を AI で分析し、結果を dict で返す"""
    import json

    # 上位5件の投稿を取得（エンゲージメントスコア順）
    top_posts = author.buzz_posts.order_by('-like_count')[:5]
    top_posts_text = _format_top_posts(top_posts)

    # 投稿頻度の概算
    age = author.account_age_days or 1
    total = author.total_post_count or 0
    post_frequency = round(total / age, 1) if age > 0 else 0

    prompt = ANALYSIS_PROMPT.format(
        display_name=author.display_name or '',
        username=author.username,
        bio=author.bio or '',
        followers_count=author.followers_count or 0,
        account_age_days=age,
        growth_score=author.growth_score or 0,
        avg_likes=author.avg_likes or 0,
        avg_replies=author.avg_replies or 0,
        top_posts=top_posts_text,
        total_post_count=total,
        post_frequency=post_frequency,
    )

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=1500,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = _extract_text_block(message.content[0].text.strip())

        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning('analyze_author: JSON parse failed for @%s, raw=%s', author.username, raw[:200])
        return {
            'content_type': '', 'emotion_hook': '', 'operation_strength': '',
            'character_traits': '', 'reproducible_bones': [], 'summary': raw[:500],
        }
    except Exception as e:
        logger.exception('analyze_author: AI分析失敗 @%s', author.username)
        raise


def ensure_author_data(username: str):
    """DBにTHBuzzAuthorが無ければスクレイピングで取得。投稿が少なければ追加取得。"""
    from th.models import THBuzzAuthor, THBuzzPost
    from th.services.buzz_scraper import BuzzScraper

    username = username.lstrip('@').strip()
    author = THBuzzAuthor.objects.filter(username=username).first()

    if not author:
        # スクレイピングで取得
        scraper = BuzzScraper()
        try:
            posts_data = scraper.fetch_author_posts(username, max_scrolls=5)
            if not posts_data:
                return None

            # 最初の投稿からプロフィール情報を取得
            first = posts_data[0] if posts_data else {}
            author_info = first.get('author', {})

            author = THBuzzAuthor.objects.create(
                username=username,
                display_name=author_info.get('display_name', ''),
                bio=author_info.get('bio', ''),
                followers_count=author_info.get('followers_count'),
                following_count=author_info.get('following_count'),
                is_verified=author_info.get('is_verified', False),
                profile_url=f'https://www.threads.com/@{username}',
                profile_pic_url=author_info.get('profile_pic_url', ''),
                raw_json=author_info,
            )

            # 投稿を保存
            _save_posts(author, posts_data)
            author.update_growth_stats()
        finally:
            scraper.close()

    elif author.buzz_posts.count() <= 3:
        # 投稿が少なければ追加取得
        scraper = BuzzScraper()
        try:
            posts_data = scraper.fetch_author_posts(username, max_scrolls=5)
            if posts_data:
                _save_posts(author, posts_data)
                author.update_growth_stats()
        finally:
            scraper.close()

    return author


def _save_posts(author, posts_data):
    """スクレイピング結果をDBに保存"""
    from th.models import THBuzzPost
    from django.utils.dateparse import parse_datetime

    for p in posts_data:
        post_url = p.get('post_url', '')
        if not post_url:
            continue
        if THBuzzPost.objects.filter(author=author, post_url=post_url).exists():
            continue

        posted_at = None
        if p.get('posted_at'):
            posted_at = parse_datetime(p['posted_at'])

        THBuzzPost.objects.create(
            author=author,
            post_url=post_url,
            text_content=p.get('text_content', ''),
            like_count=p.get('like_count', 0),
            reply_count=p.get('reply_count', 0),
            repost_count=p.get('repost_count', 0),
            posted_at=posted_at,
            raw_json=p,
            media_type=p.get('media_type', ''),
            media_urls=p.get('media_urls', []),
        )


# ─── Step 3: ずらしコンセプト案生成 ───

SUMMARY_PROMPT = """\
以下は複数の急成長アカウントの分析結果です。
共通して再現すべき骨格と、重要な差分を踏まえて統合まとめを作成してください。

【入力データ】
{analysis_dump}

【出力形式】
以下のJSONで返してください。
```json
{{
  "summary_bullets": ["箇条書き1", "箇条書き2", "箇条書き3"],
  "shared_bones": ["骨格1", "骨格2", "骨格3"]
}}
```
"""


def synthesize_analysis_results(analysis_results: list[dict]) -> dict:
    """個別分析を統合し、3行要約と共通骨格を返す。"""
    import json

    normalized = []
    all_bones = []
    for result in analysis_results:
        item = {
            'username': result.get('username', ''),
            'display_name': result.get('display_name', ''),
            'content_type': result.get('content_type', ''),
            'emotion_hook': result.get('emotion_hook', ''),
            'operation_strength': result.get('operation_strength', ''),
            'character_traits': result.get('character_traits', ''),
            'reproducible_bones': result.get('reproducible_bones', []),
            'summary': result.get('summary', ''),
        }
        normalized.append(item)
        all_bones.extend(item['reproducible_bones'])

    deduped_bones = list(dict.fromkeys(b for b in all_bones if b))
    if not normalized:
        return {'summary_bullets': [], 'shared_bones': []}

    prompt = SUMMARY_PROMPT.format(
        analysis_dump=json.dumps(normalized, ensure_ascii=False, indent=2),
    )

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=1200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = _extract_text_block(message.content[0].text.strip())
        result = json.loads(raw)
        bullets = result.get('summary_bullets') or []
        shared_bones = result.get('shared_bones') or deduped_bones
        return {
            'summary_bullets': bullets[:3],
            'shared_bones': list(dict.fromkeys(shared_bones))[:10],
        }
    except Exception:
        logger.exception('synthesize_analysis_results: 統合分析失敗')
        fallback_bullets = [
            r.get('summary', '') for r in normalized if r.get('summary')
        ]
        return {
            'summary_bullets': fallback_bullets[:3],
            'shared_bones': deduped_bones[:10],
        }

PROPOSALS_PROMPT = """\
以下は急成長アカウントの分析結果です。
この「再現すべき骨格」を維持しつつ、差別化した新コンセプトを5案提示してください。

【再現すべき骨格】
{extracted_bones}

【ずらしの6軸を意識】
- 対象ずらし / 占術ずらし / キャラずらし / 世界観ずらし / 切り口ずらし / 導線ずらし

{user_context}

【各案に含める情報】
1. コンセプト一言（20文字以内）
2. ターゲット（誰に向けるか）
3. 占術
4. キャラクター像（口調、雰囲気）
5. 投稿の型（骨格を維持した投稿テンプレ1つ）
6. ずらしポイント（元アカウントと何を変えたか）
7. マネタイズ導線

【制約】
- 丸パクリは禁止。必ず1つ以上の軸でずらす
- 占いで爆売れしている人の7特徴を満たすこと
- コンセプト設計時に決めるべき項目を全て含めること

【出力形式】
以下のJSON配列で出力してください:
```json
[
  {{
    "title": "コンセプト一言",
    "target": "ターゲット",
    "divination": "占術",
    "character": "キャラクター像",
    "post_template": "投稿テンプレ",
    "shift_point": "ずらしポイント",
    "monetization": "マネタイズ導線"
  }}
]
```
5案を配列で出力してください。"""


def generate_concept_proposals(analysis_results: list, user_context: str = '') -> list:
    """複数アカウントの分析結果からずらしコンセプト案5つを生成"""
    import json

    # 全アカウントの骨格を統合
    all_bones = []
    summaries = []
    for result in analysis_results:
        bones = result.get('reproducible_bones', [])
        all_bones.extend(bones)
        if result.get('summary'):
            summaries.append(result['summary'])

    bones_text = "\n".join(f"- {b}" for b in all_bones) if all_bones else "(骨格データなし)"

    user_context_section = ''
    if user_context:
        user_context_section = f"【ユーザーの要望・補足】\n{user_context}\n"

    prompt = PROPOSALS_PROMPT.format(
        extracted_bones=bones_text,
        user_context=user_context_section,
    )

    if summaries:
        prompt = f"【分析まとめ】\n" + "\n".join(f"- {s}" for s in summaries) + "\n\n" + prompt

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=3000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = _extract_text_block(message.content[0].text.strip())

        proposals = json.loads(raw)
        if not isinstance(proposals, list):
            proposals = [proposals]
        return proposals[:5]
    except json.JSONDecodeError:
        logger.warning('generate_concept_proposals: JSON parse failed, raw=%s', raw[:200])
        return []
    except Exception as e:
        logger.exception('generate_concept_proposals: 失敗')
        raise


# ─── Step 3.3: コンセプト詳細化 ───

DETAIL_PROMPT = """\
以下のコンセプト案を選択しました。詳細を固めてください。

【選択したコンセプト】
{selected_concept}

{user_feedback_section}

【出力してほしい項目（全て必須、Markdown形式）】

## 基本設計
- キャラクター名（候補3つ）
- 肩書き（一言、プロフィールに表示）
- 経歴設定
- アイコンイメージ（AI画像生成用プロンプト）
- bio（160文字以内、Threads/Instagram用）
- ターゲット像（年齢、性別、悩み、心理状態）
- 悩みの深さ（どんな痛みを解決するか）
- 占術（メイン+サブ）
- 文体（口調の例文3つ）

## 投稿テンプレート（3本）
- 各テンプレートに: 冒頭フック / 本文構成 / 締め / ハッシュタグ

## マネタイズ設計
- 無料→有料の導線（具体的ステップ）
- 価格設定（無料鑑定/有料鑑定/アップセル）
- 購入方法（STORES/ココナラ/note）

## 運用計画
- 投稿頻度（1日何件）
- コンテンツカレンダー（1週間分のテーマ例）
- DM対応方針

## 爆売れ7特徴チェック
- [ ] 鑑定納品が早い → 具体的な対策
- [ ] 鑑定文内の教育が上手い → 具体的な対策
- [ ] コンセプトが強い → 具体的な対策
- [ ] 購入方法がわかりやすい → 具体的な対策
- [ ] SNSが上手い → 具体的な対策
- [ ] 親しみやすい雰囲気がある → 具体的な対策
- [ ] 感想の見せ方が上手い → 具体的な対策

## 収益化ロードマップ
- 月1-3: 目標と施策
- 月4-6: 目標と施策
- 月7-12: 目標と施策"""


def detail_concept(selected_proposal: dict, user_feedback: str = '') -> str:
    """選択されたコンセプト案を詳細化し、MD形式で返す"""
    import json

    concept_text = "\n".join(f"- {k}: {v}" for k, v in selected_proposal.items())

    user_feedback_section = ''
    if user_feedback:
        user_feedback_section = f"【ユーザーの要望・補足】\n{user_feedback}\n"

    prompt = DETAIL_PROMPT.format(
        selected_concept=concept_text,
        user_feedback_section=user_feedback_section,
    )

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=4000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.exception('detail_concept: 詳細化失敗')
        raise
