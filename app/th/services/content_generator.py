# -*- coding: utf-8 -*-
"""投稿文AI生成サービス（Claude API連携）"""
import logging
import re

from django.conf import settings

from .ng_word_checker import check_ng_words

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# プリセット定義
# ──────────────────────────────────────────────

SYSTEM_PROMPT = (
    "あなたは占い師アカウントのSNS投稿文を作成するプロです。\n"
    "Threads向けの投稿文を作成してください。\n"
    "以下のルールを守ってください：\n"
    "- 指定された文体・トーンに従う\n"
    "- 指定された最大文字数を厳守する\n"
    "- ハッシュタグは最後にまとめて3〜5個付ける\n"
    "- 読者が「保存したい」と思う有益な内容にする\n"
    "- 冒頭の1行で注意を引くフックを入れる\n"
    "- 法令違反（霊感商法・薬機法・景表法）に抵触する表現は絶対に使わない\n"
)

STYLE_PRESETS = {
    'casual': '親しみやすいカジュアルな口調。絵文字あり。',
    'professional': '信頼感のある丁寧な口調。',
    'mystical': '神秘的で引き込む口調。',
}

TOPIC_PRESETS = {
    'daily_fortune': '今日の運勢（12星座/タロット）',
    'love': '恋愛運・復縁・ツインレイ',
    'money': '金運・開運',
    'work': '仕事運・適職',
    'spiritual': 'スピリチュアル・浄化・波動',
}


def _build_user_prompt(topic, style, character_desc, reference_posts, max_length, count):
    """Claude APIに送るユーザープロンプトを組み立てる"""
    topic_desc = TOPIC_PRESETS.get(topic, topic)
    style_desc = STYLE_PRESETS.get(style, style)

    parts = [
        f"【トピック】{topic_desc}",
        f"【文体】{style_desc}",
        f"【最大文字数】{max_length}文字以内",
        f"【生成数】{count}件の候補を作成してください",
    ]

    if character_desc:
        parts.append(f"【キャラ設定】{character_desc}")

    if reference_posts:
        ref_text = "\n---\n".join(reference_posts[:5])
        parts.append(f"【参考投稿（トーンや構成を参考にしてください）】\n{ref_text}")

    parts.append(
        "\n各候補は「---候補N---」で区切って出力してください。"
        "投稿文のみを出力し、説明は不要です。"
    )

    return "\n".join(parts)


def _parse_candidates(text, count):
    """Claude APIの応答を候補ごとに分割"""
    parts = re.split(r'---候補\d+---', text)
    candidates = [p.strip() for p in parts if p.strip()]
    if not candidates:
        candidates = [text.strip()]
    return candidates[:count]


def generate_post(
    topic,
    style='casual',
    character_desc='',
    reference_posts=None,
    max_length=500,
    count=3,
):
    """
    Claude APIで投稿文を生成し、NGワードチェックも実施する。

    Returns:
        {
            'candidates': [
                {'text': str, 'char_count': int, 'ng_check': dict},
                ...
            ],
            'error': str | None
        }
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return {
            'candidates': [],
            'error': 'ANTHROPIC_API_KEY が設定されていません。.env に追加してください。',
        }

    try:
        import anthropic
    except ImportError:
        return {
            'candidates': [],
            'error': 'anthropic パッケージがインストールされていません。pip install anthropic を実行してください。',
        }

    user_prompt = _build_user_prompt(
        topic, style, character_desc, reference_posts, max_length, count,
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_prompt}],
        )
        response_text = message.content[0].text
    except Exception as e:
        logger.exception('Claude API呼び出しエラー')
        return {
            'candidates': [],
            'error': f'Claude API エラー: {e}',
        }

    raw_candidates = _parse_candidates(response_text, count)

    candidates = []
    for text in raw_candidates:
        candidates.append({
            'text': text,
            'char_count': len(text),
            'ng_check': check_ng_words(text),
        })

    return {
        'candidates': candidates,
        'error': None,
    }
