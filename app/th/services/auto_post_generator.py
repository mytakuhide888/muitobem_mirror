# -*- coding: utf-8 -*-
"""自動投稿ワークフロー — 参考投稿→AIリライト→スケジュール一括生成"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from th.services.ng_word_checker import check_ng_words

logger = logging.getLogger(__name__)


def fetch_reference_posts(author_username: str, since_hours: int = 72) -> list[dict]:
    """ThreadsBuzzScraper で参考アカウントの最新投稿を取得し、
    since_hours 以内の投稿のみフィルタ。

    スクレイピングは重いため、まずDBに保存済みの投稿を検索し、
    なければスクレイパーを起動する。
    """
    from th.models import THBuzzAuthor, THBuzzPost

    cutoff = timezone.now() - timedelta(hours=since_hours)

    # まずDBから取得を試みる
    try:
        author = THBuzzAuthor.objects.get(username=author_username)
        db_posts = THBuzzPost.objects.filter(
            author=author,
            posted_at__gte=cutoff,
        ).order_by('-posted_at')

        if db_posts.exists():
            return [
                {
                    'id': p.id,
                    'text_content': p.text_content,
                    'like_count': p.like_count,
                    'reply_count': p.reply_count,
                    'repost_count': p.repost_count,
                    'posted_at': p.posted_at.isoformat() if p.posted_at else '',
                    'post_url': p.post_url,
                    'engagement_score': p.engagement_score or 0,
                }
                for p in db_posts
            ]
    except THBuzzAuthor.DoesNotExist:
        pass

    # DBに十分な投稿がなければスクレイパーで取得
    try:
        from th.services.buzz_scraper import ThreadsBuzzScraper
        scraper = ThreadsBuzzScraper()
        raw_posts = scraper.fetch_author_posts(
            username=author_username,
            max_scrolls=3,
            exclude_replies=True,
        )
    except Exception as e:
        logger.warning('スクレイピング失敗 @%s: %s', author_username, e)
        return []

    # since_hours でフィルタ
    results = []
    for p in raw_posts:
        posted_at = p.get('posted_at')
        if posted_at and posted_at >= cutoff:
            results.append({
                'id': None,
                'text_content': p.get('text_content', ''),
                'like_count': p.get('like_count', 0),
                'reply_count': p.get('reply_count', 0),
                'repost_count': p.get('repost_count', 0),
                'posted_at': posted_at.isoformat() if posted_at else '',
                'post_url': p.get('post_url', ''),
                'engagement_score': p.get('engagement_score', 0),
            })

    # posted_at がない投稿も含める（時間フィルタ不可の場合）
    if not results:
        for p in raw_posts[:10]:
            results.append({
                'id': None,
                'text_content': p.get('text_content', ''),
                'like_count': p.get('like_count', 0),
                'reply_count': p.get('reply_count', 0),
                'repost_count': p.get('repost_count', 0),
                'posted_at': '',
                'post_url': p.get('post_url', ''),
                'engagement_score': p.get('engagement_score', 0),
            })

    return results


def rewrite_post_with_concept(
    original_text: str,
    character,
    style_hint: str = '',
) -> str:
    """Claude API (Sonnet) で参考投稿をキャラクターのコンセプト・口調でリライト。

    Args:
        original_text: リライト元の投稿文
        character: AppraisalCharacter インスタンス
        style_hint: 追加のスタイル指示（任意）

    Returns:
        リライト後の投稿文（500文字以内、ハッシュタグ3-5個）
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY が設定されていません')

    import anthropic

    # キャラクター情報の組み立て
    char_info_parts = []
    if character.name:
        char_info_parts.append(f"キャラクター名: {character.name}")
    if character.concept:
        char_info_parts.append(f"コンセプト: {character.concept}")
    if character.writing_style:
        char_info_parts.append(f"文体: {character.writing_style}")
    if character.target_audience:
        char_info_parts.append(f"ターゲット層: {character.target_audience}")
    if character.divination_methods:
        methods = character.divination_methods
        if isinstance(methods, list):
            methods = '、'.join(methods)
        char_info_parts.append(f"占術: {methods}")

    char_info = '\n'.join(char_info_parts)

    # コンセプト設計書があればプロンプトに含める（長すぎる場合は冒頭のみ）
    concept_doc = ''
    if character.concept_document_md:
        doc = character.concept_document_md
        if len(doc) > 2000:
            doc = doc[:2000] + '\n...(省略)'
        concept_doc = f"\n\n【コンセプト設計書】\n{doc}"

    system_prompt = (
        "あなたは占い師のSNS投稿リライターです。\n"
        "参考投稿の「構成」「フック」「情報の切り口」を参考にしつつ、\n"
        "指定されたキャラクターの口調・世界観で完全にリライトしてください。\n\n"
        "【必須ルール】\n"
        "- 500文字以内に収める\n"
        "- 冒頭1行で読者の注意を引くフックを入れる\n"
        "- ハッシュタグは末尾に3〜5個\n"
        "- 参考投稿の文章をそのままコピーしない（構成やアイデアの参考のみ）\n"
        "- 霊感商法・薬機法・景表法に抵触する表現は絶対に使わない\n"
        "- 「確実に」「絶対に」「必ず」などの断定表現を避ける\n"
        "- 投稿文のみを出力し、説明や前置きは不要\n"
    )

    user_prompt_parts = [
        f"【キャラクター設定】\n{char_info}",
    ]
    if concept_doc:
        user_prompt_parts.append(concept_doc)
    if style_hint:
        user_prompt_parts.append(f"\n【追加スタイル指示】\n{style_hint}")
    user_prompt_parts.append(f"\n【参考投稿（リライト元）】\n{original_text}")
    user_prompt_parts.append(
        "\n上記の参考投稿を、キャラクターの口調・世界観で完全にリライトしてください。"
    )

    user_prompt = '\n'.join(user_prompt_parts)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1024,
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    rewritten = message.content[0].text.strip()
    return rewritten


def generate_scheduled_posts(
    project_id: int,
    author_username: str,
    account,
    character,
    interval_hours: int = 8,
    max_posts: int = 5,
    style_hint: str = '',
) -> list:
    """参考投稿取得→リライト→THScheduledPost(DRAFT)を一括生成。

    Args:
        project_id: ConceptProject の PK
        author_username: 参考アカウントの username
        account: ThreadsAccount インスタンス
        character: AppraisalCharacter インスタンス
        interval_hours: 投稿間隔（時間）
        max_posts: 最大生成数
        style_hint: 追加スタイル指示

    Returns:
        生成された THScheduledPost のリスト
    """
    from th.models import THScheduledPost, THBuzzPost, ConceptProject

    # 参考投稿を取得
    ref_posts = fetch_reference_posts(author_username, since_hours=168)  # 1週間
    if not ref_posts:
        raise ValueError(f'@{author_username} の参考投稿が見つかりません')

    # engagement_score 上位から max_posts 件選択
    ref_posts.sort(key=lambda x: x.get('engagement_score', 0), reverse=True)
    selected = ref_posts[:max_posts]

    project = ConceptProject.objects.get(pk=project_id)
    now = timezone.now()
    created_posts = []

    for i, ref in enumerate(selected):
        original_text = ref.get('text_content', '')
        if not original_text or len(original_text) < 10:
            continue

        try:
            rewritten = rewrite_post_with_concept(
                original_text=original_text,
                character=character,
                style_hint=style_hint,
            )
        except Exception as e:
            logger.warning('リライト失敗 (ref=%s): %s', ref.get('post_url', ''), e)
            continue

        # NGワードチェック
        ng_result = check_ng_words(rewritten)
        if ng_result.get('critical_count', 0) > 0:
            logger.warning('NGワード(critical)検出: %s', rewritten[:50])
            continue

        # スケジュール日時を interval_hours 間隔で設定
        scheduled_at = now + timedelta(hours=interval_hours * (i + 1))

        # source_buzz_post のリンク（DBに存在する場合のみ）
        source_buzz = None
        if ref.get('id'):
            try:
                source_buzz = THBuzzPost.objects.get(pk=ref['id'])
            except THBuzzPost.DoesNotExist:
                pass

        post = THScheduledPost.objects.create(
            account=account,
            title=f'自動生成: @{author_username} リライト',
            topic='auto_rewrite',
            body=rewritten,
            scheduled_at=scheduled_at,
            status=THScheduledPost.Status.DRAFT,
            source_buzz_post=source_buzz,
            concept_project=project,
        )
        created_posts.append(post)

    return created_posts
