"""Threads Graph API client."""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ThreadsApiError(Exception):
    """Raised when Threads API returns non-2xx or malformed response."""


@dataclasses.dataclass
class ThreadsCredentials:
    user_id: str
    access_token: str


def verify_signature(raw_body: bytes, signature_header: str | None, secret: str) -> bool:
    """Verify X-Hub-Signature-256 header with given secret."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received = signature_header.split("=", 1)[1]
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, expected)


class ThreadsApiClient:
    def __init__(self, credentials: ThreadsCredentials):
        self.base_url = getattr(settings, "THREADS_API_BASE_URL", "https://graph.threads.net/v1.0").rstrip("/")
        self.credentials = credentials

    # -------- internal --------
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        params = dict(params or {})
        params.setdefault("access_token", self.credentials.access_token)

        resp = requests.request(method, url, params=params, json=json, timeout=10)
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if not resp.ok:
            # 不用意にトークンをログに出さない
            redacted = {k: ("***" if "token" in k else v) for k, v in data.items()} if isinstance(data, dict) else data
            logger.warning("Threads API error %s %s -> %s", method, url, redacted)
            raise ThreadsApiError(f"{resp.status_code}: {redacted}")
        return data if isinstance(data, dict) else {"data": data}

    # -------- publish --------
    def create_text_container(
        self,
        text: str,
        reply_to_id: Optional[str] = None,
        quote_post_id: Optional[str] = None,
        link_attachment: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {"media_type": "TEXT", "text": text}
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        if quote_post_id:
            payload["quote_post_id"] = quote_post_id
        if link_attachment:
            payload["link_attachment"] = link_attachment
        data = self._request("POST", f"{self.credentials.user_id}/threads", json=payload)
        return str(data.get("id", ""))

    def publish_container(self, creation_id: str) -> str:
        data = self._request(
            "POST",
            f"{self.credentials.user_id}/threads_publish",
            json={"creation_id": creation_id},
        )
        return str(data.get("id", ""))

    def post_text(self, text: str) -> str:
        cid = self.create_text_container(text=text)
        return self.publish_container(creation_id=cid)

    def post_reply(self, reply_to_id: str, text: str) -> str:
        cid = self.create_text_container(text=text, reply_to_id=reply_to_id)
        return self.publish_container(creation_id=cid)

    # -------- fetch --------
    def get_profile(
        self,
        fields: str = "id,username,threads_biography,threads_profile_picture_url",
    ) -> Dict[str, Any]:
        return self._request("GET", self.credentials.user_id, params={"fields": fields})

    def get_threads(
        self,
        limit: int = 25,
        after: Optional[str] = None,
        before: Optional[str] = None,
        fields: str = "id,username,text,timestamp,children,has_replies,is_reply,root_post,replied_to",
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit, "fields": fields}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._request("GET", f"{self.credentials.user_id}/threads", params=params)

    def get_replies(
        self,
        media_id: str,
        limit: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "limit": limit,
            "reverse": True,
            "fields": "id,username,text,timestamp,is_reply,root_post,replied_to,hide_status",
        }
        if after:
            params["after"] = after
        return self._request("GET", f"{media_id}/replies", params=params)

    def get_media(self, media_id: str, fields: str) -> Dict[str, Any]:
        return self._request("GET", f"{media_id}", params={"fields": fields})

    def get_media_insights(self, media_id: str, metrics: str) -> Dict[str, Any]:
        return self._request("GET", f"{media_id}/insights", params={"metric": metrics})

    def get_user_insights(self, metrics: str, since: Optional[int] = None, until: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"metric": metrics}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self._request("GET", f"{self.credentials.user_id}/threads_insights", params=params)


# ---- Backward compatibility stubs (old signatures) ----
def _resolve_creds(access_token: str, user_id: str) -> ThreadsCredentials:
    token = access_token or getattr(settings, "THREADS_USER_ACCESS_TOKEN", "")
    uid = user_id or getattr(settings, "INSTAGRAM_PROFESSIONAL_ID", "")  # best-effort fallback
    return ThreadsCredentials(user_id=uid, access_token=token)


def fetch_posts(access_token: str, user_id: str, since=None):
    """
    Old stub signature used by post_importer. Returns a list of dicts.
    """
    creds = _resolve_creds(access_token, user_id)
    if not creds.user_id or not creds.access_token:
        logger.warning("fetch_posts: missing user_id or access_token")
        return []
    try:
        client = ThreadsApiClient(creds)
        data = client.get_threads(limit=25)
        items = data.get("data") or []
        results = []
        for it in items:
            results.append({
                "id": str(it.get("id", "")),
                "content": it.get("text", ""),
                "like_count": it.get("like_count", 0) or 0,
                "view_count": it.get("view_count"),
                "posted_at": it.get("timestamp") or "",
                "raw": it,
            })
        return results
    except Exception as e:
        logger.warning("fetch_posts failed: %s", e)
        return []


def post_thread(access_token: str, user_id: str, text: str):
    """
    Old stub signature used by scheduler. Returns dict with id/text.
    """
    creds = _resolve_creds(access_token, user_id)
    if not creds.user_id or not creds.access_token:
        logger.warning("post_thread: missing user_id or access_token")
        return {"error": "missing credentials"}
    try:
        client = ThreadsApiClient(creds)
        pid = client.post_text(text)
        return {"id": pid, "text": text}
    except Exception as e:
        logger.warning("post_thread failed: %s", e)
        return {"error": str(e)}
