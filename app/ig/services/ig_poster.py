# -*- coding: utf-8 -*-
"""Instagram Graph API 投稿サービス"""
import logging

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from ig.models import InstagramBusinessAccount, IGPost
from social.services.ig_api import create_media, publish_media

GRAPH_BASE = f"https://graph.facebook.com/{getattr(settings, 'DEFAULT_API_VERSION', 'v23.0')}"
logger = logging.getLogger(__name__)


def _get_token(account: InstagramBusinessAccount) -> str:
    token = account.best_send_token
    if not token:
        raise ValueError(f"アクセストークンが設定されていません (account_id={account.pk})")
    return token


def post_image(account: InstagramBusinessAccount, caption: str, image_url: str) -> IGPost:
    """画像をInstagramに投稿してIGPostを返す"""
    token = _get_token(account)
    ig_user_id = account.ig_business_id

    container = create_media(ig_user_id, token, caption, image_url=image_url, media_type="IMAGE")
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError(f"media作成失敗: {container}")

    result = publish_media(creation_id, token)
    post_id = result.get("id")
    if not post_id:
        raise RuntimeError(f"media_publish失敗: {result}")

    return IGPost.objects.create(
        account=account,
        external_post_id=post_id,
        caption=caption,
        media_type="IMAGE",
        media_url=image_url,
        posted_at=timezone.now(),
        raw_json=result,
    )


def post_reel(account: InstagramBusinessAccount, caption: str, video_url: str) -> IGPost:
    """リールをInstagramに投稿してIGPostを返す"""
    token = _get_token(account)
    ig_user_id = account.ig_business_id

    container = create_media(ig_user_id, token, caption, video_url=video_url, media_type="REELS")
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError(f"media作成失敗: {container}")

    result = publish_media(creation_id, token)
    post_id = result.get("id")
    if not post_id:
        raise RuntimeError(f"media_publish失敗: {result}")

    return IGPost.objects.create(
        account=account,
        external_post_id=post_id,
        caption=caption,
        media_type="REELS",
        media_url=video_url,
        posted_at=timezone.now(),
        raw_json=result,
    )


def sync_posts(account: InstagramBusinessAccount) -> int:
    """IGからメディア一覧を取得してDBに同期。戻り値: 新規保存件数"""
    token = _get_token(account)
    ig_user_id = account.ig_business_id

    url = f"{GRAPH_BASE}/{ig_user_id}/media"
    params = {
        "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
        "access_token": token,
        "limit": 50,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])

    created_count = 0
    for item in data:
        post_id = item.get("id")
        if not post_id:
            continue
        if IGPost.objects.filter(external_post_id=post_id).exists():
            continue

        ts_str = item.get("timestamp", "")
        posted_at = parse_datetime(ts_str) if ts_str else None
        if not posted_at:
            posted_at = timezone.now()

        IGPost.objects.create(
            account=account,
            external_post_id=post_id,
            caption=item.get("caption", ""),
            media_type=item.get("media_type", ""),
            media_url=item.get("media_url") or None,
            like_count=item.get("like_count", 0),
            posted_at=posted_at,
            raw_json=item,
        )
        created_count += 1

    return created_count
