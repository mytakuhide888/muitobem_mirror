"""Threads API クライアントのスタブ"""
"""Threads API wrapper stubs.

The real Threads API is not publicly documented, so these functions act
as placeholders that mirror the behaviour expected by the rest of the
application.  They perform no persistence and simply return dictionaries
that resemble successful API responses.
"""

from datetime import datetime
from typing import Dict, List, Optional


def fetch_posts(access_token: str, user_id: str, since: datetime | None = None) -> List[Dict]:
    """Fetch public posts for a user (stub)."""
    dummy = {
        "id": "thr1",
        "content": "Threadsテスト投稿",
        "like_count": 1,
        "view_count": 10,
        "posted_at": datetime.now().isoformat(),
    }
    return [dummy]


def post_thread(access_token: str, user_id: str, text: str) -> Dict:
    """Create a text post (stub)."""
    return {"id": "posted", "text": text}


# ---- Additional helper functions required by the tasks ----


def create_post(account_token: str, kind: str, payload: Dict) -> Dict:
    """Create a Threads post.

    Parameters mirror the expected API: ``kind`` can be ``text``,
    ``image`` or ``video``.  ``payload`` contains the media details.
    """
    return {"kind": kind, "payload": payload, "access_token": account_token}


def fetch_replies(post_id: str, account_token: str, since_ts: Optional[int] = None) -> Dict:
    return {"post_id": post_id, "since": since_ts, "access_token": account_token}


def reply_to_post(post_id: str, account_token: str, text: str) -> Dict:
    return {"post_id": post_id, "text": text, "access_token": account_token}


def hide_reply(reply_id: str, account_token: str, hide: bool) -> Dict:
    return {"reply_id": reply_id, "hidden": hide, "access_token": account_token}


def fetch_public_profile(identifier: str) -> Dict:
    return {"user": identifier}


def fetch_public_posts(user_id: str, since_ts: Optional[int] = None) -> Dict:
    return {"user_id": user_id, "since": since_ts}


def fetch_insights_media(media_id: str, account_token: str, metrics: List[str]) -> Dict:
    return {"media_id": media_id, "metrics": metrics, "access_token": account_token}
