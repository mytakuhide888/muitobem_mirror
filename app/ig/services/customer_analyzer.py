# -*- coding: utf-8 -*-
"""顧客投稿取得・性格分析サービス"""
import logging
import os
from datetime import datetime

import anthropic
from django.utils import timezone

from ig.services.appraisal_rules import CUSTOMER_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


def fetch_customer_posts(username: str, platform: str = 'THREADS') -> list[dict]:
    """顧客の投稿を取得する。

    Threads の場合は buzz_scraper の fetch_author_posts() を流用。
    """
    if platform == 'THREADS':
        try:
            from th.services.buzz_scraper import ThreadsBuzzScraper as BuzzScraper
            scraper = BuzzScraper()
            posts = scraper.fetch_author_posts(username, max_scrolls=5)
            scraper.close()
            return posts
        except Exception as e:
            logger.exception('fetch_customer_posts: Threads投稿取得失敗 @%s', username)
            return []
    # Instagram は将来対応
    return []


def save_customer_posts(customer, posts: list[dict]):
    """取得した投稿を AppraisalCustomerPost に保存する。"""
    from social.models import AppraisalCustomerPost

    # 既存投稿をクリアして再取得
    customer.posts.all().delete()

    for p in posts:
        posted_at = None
        if p.get('posted_at'):
            try:
                posted_at = datetime.fromisoformat(str(p['posted_at']))
                if posted_at.tzinfo is None:
                    posted_at = timezone.make_aware(posted_at)
            except (ValueError, TypeError):
                pass

        AppraisalCustomerPost.objects.create(
            customer=customer,
            post_url=p.get('url', '')[:500],
            text_content=p.get('text', ''),
            posted_at=posted_at,
            like_count=p.get('like_count', 0) or 0,
            reply_count=p.get('reply_count', 0) or 0,
            raw_json=p,
        )

    customer.posts_fetched_at = timezone.now()
    customer.save(update_fields=['posts_fetched_at'])


def analyze_customer_personality(customer) -> str:
    """顧客の投稿履歴から性格分析を行い、personality_analysis に保存する。"""
    posts = customer.posts.all()[:30]
    if not posts:
        return ''

    posts_text = "\n---\n".join(
        f"[{p.posted_at:%Y-%m-%d %H:%M}] {p.text_content}" if p.posted_at
        else p.text_content
        for p in posts if p.text_content
    )

    if not posts_text.strip():
        return ''

    prompt = CUSTOMER_ANALYSIS_PROMPT.format(posts_text=posts_text)

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        logger.warning('analyze_customer_personality: ANTHROPIC_API_KEY 未設定')
        return ''

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt}],
        )
        analysis = message.content[0].text.strip()
        customer.personality_analysis = analysis
        customer.save(update_fields=['personality_analysis'])
        return analysis
    except Exception as e:
        logger.exception('analyze_customer_personality: 分析失敗')
        return ''


def get_customer_dm_history(user_id: str, platform: str, limit: int = 20) -> list[dict]:
    """DMMessage から該当ユーザーとの履歴を取得する。"""
    from social.models import DMMessage

    messages = (
        DMMessage.objects
        .filter(user_id=user_id, platform=platform)
        .order_by('-sent_at')[:limit]
    )

    return [
        {
            'direction': msg.direction,
            'text': msg.text,
            'sent_at': msg.sent_at.isoformat() if msg.sent_at else '',
        }
        for msg in reversed(messages)
    ]
