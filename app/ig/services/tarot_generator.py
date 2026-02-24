# -*- coding: utf-8 -*-
"""タロット3択リール投稿文生成サービス（Claude API連携）"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "あなたは占いアカウントのInstagramリール用投稿文を作成するプロです。\n"
    "タロット占い『3択リール』フォーマットで投稿文を作成してください。\n"
    "以下のルールを厳守してください：\n"
    "- 3枚のタロットカードを提示し、フォロワーに直感で選ばせる\n"
    "- コメントを促す問いかけを必ず入れる\n"
    "- ハッシュタグは末尾に5〜8個\n"
    "- 法令違反（霊感商法・薬機法・景表法・確実性表現）は絶対に使わない\n"
    "- AI生成であることを示す文言を入れない\n"
    "- キャプション全体は2,200文字以内\n"
)

THEME_PRESETS = {
    "love": "恋愛運・パートナーシップ",
    "money": "金運・仕事運",
    "work": "仕事運・キャリア",
    "overall": "全体運・今週の流れ",
    "relationship": "人間関係・縁",
}

TAROT_CARDS = [
    "愚者", "魔術師", "女教皇", "女帝", "皇帝", "法王", "恋人", "戦車",
    "力", "隠者", "運命の輪", "正義", "吊るされた男", "死神", "節制",
    "悪魔", "塔", "星", "月", "太陽", "審判", "世界",
]

OUTPUT_FORMAT = """
以下のJSON形式のみで返答してください（説明文不要）：
{
  "caption": "投稿本文（キャプション全体。ハッシュタグ含む）",
  "card_a": "カードA名",
  "card_b": "カードB名",
  "card_c": "カードC名",
  "reading_a": "カードAの解釈（今週のメッセージ、2〜3文）",
  "reading_b": "カードBの解釈（今週のメッセージ、2〜3文）",
  "reading_c": "カードCの解釈（今週のメッセージ、2〜3文）"
}
"""


def generate_tarot_options(theme: str = "overall", style: str = "casual", character_desc: str = "") -> dict:
    """
    Claude APIでタロット3択投稿文を生成する。
    戻り値: {ok, caption, card_a, card_b, card_c, reading_a, reading_b, reading_c, error}
    """
    import anthropic
    import json

    theme_desc = THEME_PRESETS.get(theme, theme)

    user_prompt_parts = [
        f"【テーマ】{theme_desc}",
        f"【文体】{'親しみやすいカジュアルな口調。絵文字あり。' if style == 'casual' else '神秘的で引き込む口調。'}",
    ]
    if character_desc:
        user_prompt_parts.append(f"【キャラクター設定】{character_desc}")
    user_prompt_parts.append("【カード候補】" + "、".join(TAROT_CARDS[:12]))
    user_prompt_parts.append(OUTPUT_FORMAT)

    user_prompt = "\n".join(user_prompt_parts)

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()

        # JSONブロックを抽出
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        parsed = json.loads(raw)
        parsed["ok"] = True
        return parsed

    except Exception as e:
        logger.exception("タロット生成失敗")
        return {"ok": False, "error": str(e)}
