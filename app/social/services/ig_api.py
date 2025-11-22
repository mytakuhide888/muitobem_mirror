"""Simplified Instagram Graph API wrapper.

All functions return the JSON body of the HTTP response and avoid any
side effects so that callers can decide how to persist data.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import requests
from django.conf import settings

BASE_URL = f"https://graph.facebook.com/{settings.DEFAULT_API_VERSION}"

GRAPH_BASE = "https://graph.facebook.com/v23.0"

def send_dm_flexible(*, access_token: str, psid: Optional[str] = None,
                     thread_key: Optional[str] = None, text: str) -> Dict:
    if not text:
        raise ValueError("text required")
    if not (psid or thread_key):
        raise ValueError("psid or thread_key required")

    payload = {
        "messaging_product": "instagram",
        "message": {"text": text},
        "access_token": access_token,
    }
    if thread_key:
        payload["recipient"] = {"thread_key": thread_key}
    else:
        payload["recipient"] = {"id": psid}

    return _post_json("me/messages", payload)

def _post(path: str, params: Dict) -> Dict:
    url = f"{BASE_URL}/{path}"
    res = requests.post(url, data=params)
    res.raise_for_status()
    return res.json()


def _get(path: str, params: Dict) -> Dict:
    url = f"{BASE_URL}/{path}"
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json()

def _post_json(path: str, payload: Dict) -> Dict:
    """JSON POST（失敗時は dict を投げる）"""
    url = f"{GRAPH_BASE}/{path}"
    r = requests.post(url, json=payload, timeout=20)
    try:
        j = r.json()
    except Exception:
        j = None

    if not r.ok:
        # ← ここを文字列ではなく dict で投げる
        raise RuntimeError({
            "status": r.status_code,
            "json": j if isinstance(j, dict) else None,
            "text": r.text,
            "url": url,
        })

    return j if isinstance(j, dict) else {"raw": r.text}

def send_dm(access_token: str, recipient_id: str, text: str) -> Dict:
    """
    Instagram Messaging の Send API。
    必須: messaging_product='instagram'
    """
    payload = {
        "messaging_product": "instagram",
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": access_token,
    }
    return _post_json("me/messages", payload)

def fetch_dms(access_token: str, since_ts: Optional[int] = None) -> Dict:
    params = {"access_token": access_token}
    if since_ts:
        params["since"] = since_ts
    return _get("me/conversations", params)


def fetch_comments(media_id: str, access_token: str) -> Dict:
    params = {"access_token": access_token, "fields": "id,text"}
    return _get(f"{media_id}/comments", params)


def reply_comment(comment_id: str, access_token: str, text: str) -> Dict:
    params = {"message": text, "access_token": access_token}
    return _post(f"{comment_id}/replies", params)


def hide_comment(comment_id: str, access_token: str, hide: bool) -> Dict:
    params = {"hidden": str(hide).lower(), "access_token": access_token}
    return _post(f"{comment_id}", params)


def create_media(ig_user_id: str, access_token: str, caption: str, **kwargs) -> Dict:
    params = {"caption": caption, "access_token": access_token}
    params.update(kwargs)
    return _post(f"{ig_user_id}/media", params)


def publish_media(creation_id: str, access_token: str) -> Dict:
    params = {"creation_id": creation_id, "access_token": access_token}
    return _post("me/media_publish", params)


def fetch_insights_ig_user(ig_user_id: str, access_token: str, metrics: List[str], period: str) -> Dict:
    params = {
        "metric": ",".join(metrics),
        "period": period,
        "access_token": access_token,
    }
    return _get(f"{ig_user_id}/insights", params)


def fetch_insights_media(media_id: str, access_token: str, metrics: List[str]) -> Dict:
    params = {"metric": ",".join(metrics), "access_token": access_token}
    return _get(f"{media_id}/insights", params)
