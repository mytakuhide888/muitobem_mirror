from __future__ import annotations

"""Utility helpers for resolving access tokens and credentials.

These functions are deliberately side effect free; they merely return
information based on the provided account objects and environment.  The
caller is responsible for persisting any refreshed tokens etc.
"""
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Union

from django.utils import timezone

from ..models import FacebookAccount, InstagramAccount, ThreadsAccount, ThreadsApp

TOKEN_EXPIRY_THRESHOLD = timedelta(hours=72)


def _token_json(token: str | None, expires_at) -> Dict:
    return {"access_token": token or "", "expires_at": expires_at}


def get_page_access_token(account: FacebookAccount) -> str:
    """Return the page access token for the given FacebookAccount."""
    token_json = _token_json(account.access_token, account.access_token_expires_at)
    if is_token_expiring(token_json):
        # In real implementation we would refresh the token.  For this
        # exercise we simply return the current token.
        pass
    return account.access_token or ""


def get_ig_creds(account: Union[InstagramAccount, FacebookAccount]) -> Dict[str, str]:
    """Resolve IG credentials via linked facebook page.

    Returns a dict with keys: page_id, ig_user_id, access_token.
    """
    if isinstance(account, InstagramAccount):
        fb = account.linked_facebook
    else:
        fb = account
    return {
        "page_id": fb.facebook_user_id if fb else "",
        "ig_user_id": getattr(account, "instagram_user_id", ""),
        "access_token": fb.access_token if fb else "",
    }


def get_threads_token(account: Union[ThreadsAccount, FacebookAccount, ThreadsApp]) -> Dict[str, str]:
    """Return Threads access token information.

    The lookup order roughly follows: explicit ThreadsApp -> linked
    Facebook account -> default app.
    """
    if isinstance(account, ThreadsApp):
        return {"access_token": "", "app_id": account.threads_app_id}

    if isinstance(account, ThreadsAccount):
        if account.linked_facebook:
            return {
                "access_token": account.linked_facebook.access_token or "",
                "app_id": account.linked_facebook.app_id or "",
            }
        if account.default_app:
            return {"access_token": "", "app_id": account.default_app.threads_app_id}
    if isinstance(account, FacebookAccount):
        return {
            "access_token": account.access_token or "",
            "app_id": account.app_id or "",
        }
    return {"access_token": "", "app_id": ""}


def is_token_expiring(token_json: Dict) -> bool:
    """Return True if the token expires within the threshold."""
    expires_at = token_json.get("expires_at")
    if not expires_at:
        return False
    return expires_at - timezone.now() < TOKEN_EXPIRY_THRESHOLD
