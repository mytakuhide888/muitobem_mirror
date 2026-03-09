# -*- coding: utf-8 -*-
"""投稿パフォーマンス（インサイト）取得サービス"""
import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def fetch_post_insights(scheduled_post) -> dict:
    """ThreadsApiClient.get_media_insights() で
    impressions, likes, replies を取得し、モデルに保存する。

    Returns:
        {'impressions': int, 'likes': int, 'replies': int} or empty dict on error
    """
    from social.services.threads_api import ThreadsApiClient, ThreadsCredentials, ThreadsApiError

    if not scheduled_post.external_post_id:
        return {}

    account = scheduled_post.account
    user_id = getattr(account, 'threads_user_id', '') or getattr(account, 'external_id', '')
    token = getattr(account, 'access_token', '') or getattr(settings, 'THREADS_USER_ACCESS_TOKEN', '')

    if not user_id or not token:
        logger.warning('インサイト取得: user_id/token が不足 (post_id=%s)', scheduled_post.id)
        return {}

    client = ThreadsApiClient(ThreadsCredentials(user_id=user_id, access_token=token))

    try:
        data = client.get_media_insights(
            media_id=scheduled_post.external_post_id,
            metrics='views,likes,replies,reposts',
        )
    except ThreadsApiError as e:
        logger.warning('インサイトAPI エラー (post_id=%s): %s', scheduled_post.id, e)
        return {}

    # レスポンス解析: {"data": [{"name": "views", "values": [{"value": 123}]}, ...]}
    result = {}
    for item in data.get('data', []):
        name = item.get('name', '')
        values = item.get('values', [])
        value = values[0].get('value', 0) if values else 0
        result[name] = value

    impressions = result.get('views', 0) or result.get('impressions', 0)
    likes = result.get('likes', 0)
    replies = result.get('replies', 0)
    reposts = result.get('reposts', 0)

    scheduled_post.impressions = impressions
    scheduled_post.engagement = likes + replies + reposts
    scheduled_post.insights_updated_at = timezone.now()
    scheduled_post.save(update_fields=['impressions', 'engagement', 'insights_updated_at'])

    return {
        'impressions': impressions,
        'likes': likes,
        'replies': replies,
        'reposts': reposts,
    }


def bulk_fetch_insights(posts) -> int:
    """SENT状態の投稿のinsightsを一括更新。更新件数を返す。"""
    updated = 0
    for post in posts:
        if not post.external_post_id:
            continue
        try:
            result = fetch_post_insights(post)
            if result:
                updated += 1
        except Exception as e:
            logger.warning('インサイト一括更新エラー (post_id=%s): %s', post.id, e)
    return updated
