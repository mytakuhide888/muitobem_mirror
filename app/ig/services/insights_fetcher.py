# -*- coding: utf-8 -*-
"""Instagram インサイト取得サービス"""
import logging

from ig.models import IGPost, IGPostInsight, InstagramBusinessAccount
from social.services.ig_api import fetch_insights_media, fetch_insights_ig_user

logger = logging.getLogger(__name__)

# 投稿インサイト取得指標（メディア種別によって取得可能なものが異なる）
POST_METRICS = ["impressions", "reach", "likes", "comments", "shares", "saved"]
ACCOUNT_METRICS = ["impressions", "reach", "profile_views", "follower_count"]


def fetch_post_insights(post: IGPost) -> IGPostInsight | None:
    """1件のIGPostのインサイトを取得してIGPostInsightに保存"""
    account = post.account
    token = account.best_send_token
    if not token:
        logger.warning("トークンなし: account_id=%s", account.pk)
        return None

    try:
        data = fetch_insights_media(post.external_post_id, token, POST_METRICS)
    except Exception as e:
        logger.warning("インサイト取得失敗 post_id=%s: %s", post.external_post_id, e)
        return None

    values = {}
    for item in data.get("data", []):
        name = item.get("name")
        val = item.get("values", [{}])[0].get("value") if item.get("values") else item.get("value")
        if name in POST_METRICS:
            values[name] = val

    return IGPostInsight.objects.create(
        post=post,
        impressions=values.get("impressions"),
        reach=values.get("reach"),
        likes=values.get("likes"),
        comments=values.get("comments"),
        shares=values.get("shares"),
        saved=values.get("saved"),
    )


def fetch_account_insights(account: InstagramBusinessAccount, period: str = "day") -> dict:
    """アカウント全体のインサイトを取得（表示用、DB保存なし）"""
    token = account.best_send_token
    if not token:
        return {}

    try:
        data = fetch_insights_ig_user(account.ig_business_id, token, ACCOUNT_METRICS, period)
        return data
    except Exception as e:
        logger.warning("アカウントインサイト取得失敗: %s", e)
        return {}


def refresh_all_post_insights(account: InstagramBusinessAccount, limit: int = 20) -> int:
    """アカウントの最新N件のIGPostのインサイトを一括更新。戻り値: 成功件数"""
    posts = IGPost.objects.filter(account=account).order_by("-posted_at")[:limit]
    success = 0
    for post in posts:
        insight = fetch_post_insights(post)
        if insight:
            success += 1
    return success
