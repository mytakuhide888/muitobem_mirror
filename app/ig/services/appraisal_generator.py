# -*- coding: utf-8 -*-
"""AI鑑定文生成サービス（Claude API連携）"""
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

DIVINATION_LABELS = {
    'tarot':      'タロット占い',
    'western':    '西洋占星術',
    'numerology': '数秘術',
    'shichu':     '四柱推命',
    'seimei':     '姓名判断',
}

_SYSTEM_PROMPT = """\
あなたはプロの占い師です。
依頼者の情報を元に、誠実で温かみのある鑑定文を生成してください。
鑑定文は日本語で、自然な文体で書いてください。
絵文字は適度に使用し、読みやすく改行してください。
"""


def generate_appraisal(
    birthdate: str,
    concern: str,
    divination: str,
    character_desc: str = '',
) -> dict:
    """
    Claude API で鑑定文を生成する。

    Args:
        birthdate: 生年月日 (例: 1990/05/15)
        concern: 悩み・相談内容
        divination: 占術キー (tarot/western/numerology/shichu/seimei)
        character_desc: キャラクター設定（任意）

    Returns:
        {'ok': True, 'appraisal_text': str} or {'ok': False, 'error': str}
    """
    divination_label = DIVINATION_LABELS.get(divination, divination)

    system = _SYSTEM_PROMPT
    if character_desc:
        system += f"\n\nキャラクター設定:\n{character_desc}"

    user_message = (
        f"【占術】{divination_label}\n"
        f"【生年月日】{birthdate}\n"
        f"【悩み・相談】{concern}\n\n"
        "上記の情報を元に、丁寧な鑑定文を生成してください。"
        "600〜1000文字程度で、具体的なアドバイスを含めてください。"
    )

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return {'ok': False, 'error': 'ANTHROPIC_API_KEY が設定されていません'}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1500,
            system=system,
            messages=[{'role': 'user', 'content': user_message}],
        )
        appraisal_text = message.content[0].text.strip()
        return {'ok': True, 'appraisal_text': appraisal_text}
    except Exception as e:
        logger.exception('appraisal_generator: Claude API 呼び出し失敗')
        return {'ok': False, 'error': str(e)}
