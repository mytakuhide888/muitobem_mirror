# -*- coding: utf-8 -*-
"""コンセプト設計 — コンセプト→キャラクター保存サービス"""
import logging
import re

logger = logging.getLogger(__name__)


def save_concept_to_character(project, *, profile_bio: str = '', pinned_post_samples: list | None = None) -> 'AppraisalCharacter':
    """ConceptProject の詳細化結果を AppraisalCharacter に分解保存する。

    Args:
        project: ConceptProject インスタンス（detailed_concept_md が入っている前提）

    Returns:
        作成または更新された AppraisalCharacter
    """
    from social.models import AppraisalCharacter

    md = project.detailed_concept_md or ''
    if profile_bio or pinned_post_samples:
        md = _apply_draft_overrides(md, profile_bio=profile_bio, pinned_post_samples=pinned_post_samples or [])
        if md != (project.detailed_concept_md or ''):
            project.detailed_concept_md = md
            project.save(update_fields=['detailed_concept_md'])

    # MD から情報を抽出
    name = _extract_character_name(md, project)
    concept = _extract_section(md, '基本設計')
    writing_style = _extract_field(md, '文体')
    target_audience = _extract_field(md, 'ターゲット像')
    divination_methods = _extract_divination(md)
    background_story = _extract_field(md, '経歴設定') or _extract_field(md, '悩みの深さ')
    profile_bio = (profile_bio or '').strip() or _extract_field(md, 'bio')
    pinned_post_samples = pinned_post_samples or _extract_post_templates(md)

    if project.character:
        char = project.character
        char.name = name
        char.concept = concept
        char.writing_style = writing_style
        char.target_audience = target_audience
        char.divination_methods = divination_methods
        char.background_story = background_story
        char.concept_document_md = md
        char.profile_bio = profile_bio
        char.pinned_post_samples = pinned_post_samples
        char.save()
    else:
        char = AppraisalCharacter.objects.create(
            name=name,
            concept=concept,
            writing_style=writing_style,
            target_audience=target_audience,
            divination_methods=divination_methods,
            background_story=background_story,
            concept_document_md=md,
            profile_bio=profile_bio,
            pinned_post_samples=pinned_post_samples,
        )
        project.character = char
        project.save(update_fields=['character'])

    _sync_templates(char, md)

    logger.info('コンセプト保存完了: project=%s → character=%s', project.pk, char.pk)
    return char


def _extract_character_name(md: str, project) -> str:
    """MD からキャラクター名を抽出（候補の最初を使用）"""
    m = re.search(r'キャラクター名[（(]?候補[）)]?\s*[:：]\s*(.+)', md)
    if m:
        names = re.split(r'[、,/／]', m.group(1).strip())
        return names[0].strip().strip('「」')
    # プロジェクトタイトルにフォールバック
    return project.title or f'コンセプト #{project.pk}'


def _extract_section(md: str, heading: str) -> str:
    """指定された##見出しのセクション全体を取得"""
    pattern = rf'##\s*{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)'
    m = re.search(pattern, md, re.DOTALL)
    return m.group(1).strip() if m else ''


def _extract_field(md: str, field_name: str) -> str:
    """MD 中の「- フィールド名: 値」パターンを抽出"""
    pattern = rf'-\s*{re.escape(field_name)}[（(]?[^)）]*[）)]?\s*[:：]\s*(.+)'
    m = re.search(pattern, md)
    return m.group(1).strip() if m else ''


def _extract_divination(md: str) -> list:
    """占術情報をリストで抽出"""
    m = re.search(r'-\s*占術[（(]?[^)）]*[）)]?\s*[:：]\s*(.+)', md)
    if m:
        text = m.group(1).strip()
        return [d.strip() for d in re.split(r'[、,+＋/／]', text) if d.strip()]
    return []


def _extract_post_templates(md: str) -> list:
    """投稿テンプレートセクションからサンプルを抽出"""
    section = _extract_section(md, '投稿テンプレート')
    if not section:
        return []

    templates = []
    # ### で区切られたテンプレートを個別に取得
    parts = re.split(r'###\s+', section)
    for part in parts:
        part = part.strip()
        if part:
            templates.append(part)

    return templates[:3]  # 最大3本


def _extract_section_body(md: str, heading: str) -> str:
    return _extract_section(md, heading)


def _extract_price_hint(md: str) -> str:
    return _extract_field(md, '価格設定')


def _sync_templates(character, md: str):
    from social.models import AppraisalTemplate

    operation_plan = _extract_section_body(md, '運用計画')
    monetization = _extract_section_body(md, 'マネタイズ設計')
    check_items = _extract_section_body(md, '爆売れ7特徴チェック')
    pricing = _extract_price_hint(md)

    template_specs = [
        (
            AppraisalTemplate.Category.FREE,
            '無料鑑定テンプレート',
            0,
            500,
            800,
            '無料鑑定として、信頼獲得と有料導線の明確化を重視してください。',
        ),
        (
            AppraisalTemplate.Category.PAID_LOW,
            '有料鑑定テンプレート（低額）',
            1,
            700,
            1100,
            '低額有料鑑定として、満足度と次回アップセルの余地を両立してください。',
        ),
        (
            AppraisalTemplate.Category.PAID_MID,
            '有料鑑定テンプレート（中額）',
            2,
            900,
            1400,
            '中額有料鑑定として、具体策と教育要素を厚めに含めてください。',
        ),
        (
            AppraisalTemplate.Category.PAID_HIGH,
            '有料鑑定テンプレート（高額）',
            3,
            1200,
            1800,
            '高額有料鑑定として、背景解釈・打ち手・継続支援まで深く提示してください。',
        ),
        (
            AppraisalTemplate.Category.FOLLOWUP,
            'フォローアップテンプレート',
            4,
            400,
            700,
            '既存顧客向けのフォローアップとして、進捗確認と次の一歩を短く明確に提示してください。',
        ),
    ]

    common_system_prompt = "\n\n".join(
        part for part in [
            '## コンセプト設計書\n' + md.strip(),
            '## マネタイズ設計\n' + monetization if monetization else '',
            '## 運用計画\n' + operation_plan if operation_plan else '',
            '## 爆売れ7特徴チェック\n' + check_items if check_items else '',
            '## 価格ヒント\n' + pricing if pricing else '',
        ] if part
    )

    for category, name, sort_order, word_min, word_max, extra_prompt in template_specs:
        AppraisalTemplate.objects.update_or_create(
            character=character,
            category=category,
            defaults={
                'name': name,
                'sort_order': sort_order,
                'word_count_min': word_min,
                'word_count_max': word_max,
                'system_prompt': common_system_prompt + '\n\n## テンプレート用途\n' + extra_prompt,
                'user_prompt_template': '',
                'is_active': True,
            },
        )


def _apply_draft_overrides(md: str, *, profile_bio: str, pinned_post_samples: list[str]) -> str:
    updated = md

    if profile_bio:
        bio_pattern = re.compile(r'(^-\s*bio[（(]?[^)）]*[）)]?\s*[:：]\s*)(.+)$', re.MULTILINE)
        if bio_pattern.search(updated):
            updated = bio_pattern.sub(r'\1' + profile_bio, updated, count=1)

    cleaned_samples = [sample.strip() for sample in pinned_post_samples if sample and sample.strip()]
    if cleaned_samples:
        rebuilt_section = '## 投稿テンプレート（3本）\n' + '\n\n'.join(
            f'### サンプル{i + 1}\n{sample}' for i, sample in enumerate(cleaned_samples[:3])
        )
        section_pattern = re.compile(r'##\s*投稿テンプレート.*?(?=\n##\s|\Z)', re.DOTALL)
        if section_pattern.search(updated):
            updated = section_pattern.sub(rebuilt_section, updated, count=1)
        else:
            updated = updated.rstrip() + '\n\n' + rebuilt_section + '\n'

    return updated
