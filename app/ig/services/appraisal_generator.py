# -*- coding: utf-8 -*-
"""AI鑑定文生成サービス（Claude API連携） v2"""
import logging
import os

import anthropic

from ig.services.appraisal_rules import MASTER_APPRAISAL_RULES

logger = logging.getLogger(__name__)

DIVINATION_LABELS = {
    'tarot':      'タロット占い',
    'western':    '西洋占星術',
    'numerology': '数秘術',
    'shichu':     '四柱推命',
    'seimei':     '姓名判断',
}

# 旧バージョンとの下位互換用デフォルトプロンプト
_DEFAULT_SYSTEM_PROMPT = """\
あなたはプロの占い師です。
依頼者の情報を元に、誠実で温かみのある鑑定文を生成してください。
"""


def _build_system_prompt(
    *,
    character=None,
    template=None,
    customer_context: str = '',
    dm_context: str = '',
) -> str:
    """システムプロンプトを階層的に組み立てる。

    優先順:
    1. MASTER_APPRAISAL_RULES（常時）
    2. テンプレートの system_prompt（あれば）、なければデフォルト
    3. キャラクター設定注入
    4. 顧客コンテキスト
    5. DMコンテキスト
    """
    parts = [MASTER_APPRAISAL_RULES]

    # テンプレートのシステムプロンプト
    if template and template.system_prompt:
        parts.append(f"\n## テンプレート固有指示\n{template.system_prompt}")
    else:
        parts.append(f"\n## 基本指示\n{_DEFAULT_SYSTEM_PROMPT}")

    # キャラクター設定
    if character:
        char_parts = []
        if character.concept:
            char_parts.append(f"- 世界観・設定: {character.concept}")
        if character.writing_style:
            char_parts.append(f"- 口調・文体: {character.writing_style}")
        if character.background_story:
            char_parts.append(f"- 経歴: {character.background_story}")
        if character.target_audience:
            char_parts.append(f"- ターゲット層: {character.target_audience}")
        if char_parts:
            parts.append("\n## キャラクター設定\n" + "\n".join(char_parts))

    # 文字数指定
    if template:
        parts.append(
            f"\n## 文字数指定\n- {template.word_count_min}〜{template.word_count_max}文字で生成してください"
        )

    # 顧客コンテキスト
    if customer_context:
        parts.append(f"\n## 顧客の性格分析\n{customer_context}")

    # DMコンテキスト
    if dm_context:
        parts.append(f"\n## 過去のDM履歴（参考）\n{dm_context}")

    return "\n".join(parts)


def _build_user_prompt(
    *,
    birthdate: str,
    concern: str,
    divination: str,
    template=None,
) -> str:
    """ユーザープロンプトを組み立てる。"""
    divination_label = DIVINATION_LABELS.get(divination, divination)

    # テンプレートにユーザープロンプトがあればそれを使用（変数置換）
    if template and template.user_prompt_template:
        return template.user_prompt_template.format(
            divination=divination_label,
            birthdate=birthdate,
            concern=concern,
        )

    # デフォルト
    return (
        f"【占術】{divination_label}\n"
        f"【生年月日】{birthdate}\n"
        f"【悩み・相談】{concern}\n\n"
        "上記の情報を元に、鑑定文を生成してください。\n"
        "必ず【主感情への共鳴文】から書き始めてください。"
    )


def generate_appraisal(
    birthdate: str,
    concern: str,
    divination: str,
    character_desc: str = '',
    *,
    character=None,
    template=None,
    customer_context: str = '',
    dm_context: str = '',
) -> dict:
    """
    Claude API で鑑定文を生成する。

    Args:
        birthdate: 生年月日 (例: 1990/05/15)
        concern: 悩み・相談内容
        divination: 占術キー (tarot/western/numerology/shichu/seimei)
        character_desc: キャラクター設定テキスト（旧バージョン互換）
        character: AppraisalCharacter インスタンス（v2）
        template: AppraisalTemplate インスタンス（v2）
        customer_context: 顧客の性格分析テキスト
        dm_context: DM履歴テキスト

    Returns:
        {'ok': True, 'appraisal_text': str, 'system_prompt': str, 'user_prompt': str}
        or {'ok': False, 'error': str}
    """
    # v2パラメータがある場合は新ロジック
    if character or template:
        system = _build_system_prompt(
            character=character,
            template=template,
            customer_context=customer_context,
            dm_context=dm_context,
        )
    else:
        # 旧バージョン互換
        system = MASTER_APPRAISAL_RULES + "\n" + _DEFAULT_SYSTEM_PROMPT
        if character_desc:
            system += f"\n\nキャラクター設定:\n{character_desc}"

    user_message = _build_user_prompt(
        birthdate=birthdate,
        concern=concern,
        divination=divination,
        template=template,
    )

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return {'ok': False, 'error': 'ANTHROPIC_API_KEY が設定されていません'}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2000,
            system=system,
            messages=[{'role': 'user', 'content': user_message}],
        )
        appraisal_text = message.content[0].text.strip()
        return {
            'ok': True,
            'appraisal_text': appraisal_text,
            'system_prompt': system,
            'user_prompt': user_message,
        }
    except Exception as e:
        logger.exception('appraisal_generator: Claude API 呼び出し失敗')
        return {'ok': False, 'error': str(e)}
