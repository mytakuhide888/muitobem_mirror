# app/app/console/utils/meta.py
# -*- coding: utf-8 -*-
import os
import json
import hmac
import hashlib
import logging
import time
from . import meta as metaapi
import os, requests, datetime as dt
from urllib.parse import urlencode

import requests
from django.conf import settings
from ig.models import InstagramBusinessAccount 

log = logging.getLogger(__name__)

# ===== 基本設定（settings優先 / なければ環境変数） =====
APP_ID     = getattr(settings, "META_APP_ID", None) or os.getenv("META_APP_ID")
APP_SECRET = getattr(settings, "META_APP_SECRET", None) or os.getenv("META_APP_SECRET")
SITE_BASE  = getattr(settings, "SITE_BASE", None) or os.getenv("SITE_BASE", "")
SITE_BASE  = SITE_BASE.rstrip("/")

VERIFY_TOKEN = getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", os.getenv("META_WEBHOOK_VERIFY_TOKEN", "dev-verify-token"))
GRAPH_VER  = "v23.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VER}"
GRAPH_BASE = "https://graph.facebook.com"
GRAPH_VERSION = "v23.0"   # ここは固定でOK。必要なら settings で切替

def api_get(path: str, params=None, access_token: str | None = None, version: str = GRAPH_VERSION, base: str = "graph"):
    """
    Graph API GETの薄いラッパ。既存の api_get がある場合はそれを使ってもOK。
    """
    params = dict(params or {})
    if access_token:
        params["access_token"] = access_token
    if base == "graph":
        url = f"{GRAPH_BASE}/{version}/{path.lstrip('/')}"
    else:
        url = f"{GRAPH_BASE}/{version}/{path.lstrip('/')}"

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def token_subject(access_token: str) -> tuple[str, str]:
    """
    トークンの種別を判定して ("user" or "page", id) を返す。
    重要: ユーザートークンで category は要求しない（User には無いフィールドのため）。
    """
    app_token = f"{APP_ID}|{APP_SECRET}"
    dbg = api_get(
        "debug_token",
        params={"input_token": access_token, "access_token": app_token},
    )
    data = dbg.get("data", dbg)  # どちらの形でも拾えるように
    ttype = data.get("type")  # "USER" or "PAGE"

    if ttype == "PAGE":
        me = api_get("me", params={"fields": "id,name,category"}, access_token=access_token)
        return "page", str(me["id"])
    else:
        me = api_get("me", params={"fields": "id,name"}, access_token=access_token)
        return "user", str(me["id"])

def _page_token_from_user_token(page_id: str, user_token: str) -> str:
    """
    ユーザートークンから対象ページのページトークンを引く。
    """
    accs = api_get(
        "me/accounts",
        params={"fields": "id,name,access_token"},
        access_token=user_token,
    )
    for p in accs.get("data", []):
        if str(p.get("id")) == str(page_id):
            return p.get("access_token")
    raise RuntimeError("the user token has no access to the page")

def _ensure_page_token(page_id: str, token: str) -> str:
    """
    渡された token がページトークンかどうかを判定し、
    ページトークンでなければユーザートークン→ページトークンに昇格して返す。
    """
    try:
        # ページトークンなら /me?fields=id,name,category が通る
        api_get("me", params={"fields": "id,name,category"}, access_token=token)
        return token
    except Exception:
        # ユーザートークンとしてページトークンを引く
        return _page_token_from_user_token(page_id, token)

def import_page(page_id: str, token: str) -> dict:
    """
    指定の page_id とトークンから Instagram Business Account を取り込み、DBへ保存/更新。
    ユーザートークン/ページトークンどちらでも動作する。
    戻り値: {"ok": True, "saved": [ig_id], "created": bool, "errors": []}
    """
    page_token = _ensure_page_token(page_id, token)

    page = api_get(
        str(page_id),
        params={"fields": "name,instagram_business_account{id,username}"},
        access_token=page_token,
    )

    ig = page.get("instagram_business_account") or {}
    ig_id = ig.get("id")
    if not ig_id:
        raise RuntimeError("no instagram_business_account on the page")

    obj, created = InstagramBusinessAccount.objects.update_or_create(
        ig_business_id=str(ig_id),
        defaults=dict(
            username=ig.get("username") or "",
            fb_page_id=str(page_id),
            display_name=page.get("name") or "",
            access_token=page_token,
        ),
    )

    log.info("import_page: saved ig_business_id=%s username=%s page=%s", obj.ig_business_id, obj.username, page_id)
    return {"ok": True, "saved": [str(obj.ig_business_id)], "created": created, "errors": []}


# ===== 安全系ユーティリティ =====
def _appsecret_proof(token: str) -> str:
    """appsecret_proof を作成"""
    return hmac.new(APP_SECRET.encode(), msg=token.encode(), digestmod=hashlib.sha256).hexdigest()

def _ensure_conf():
    if not os.getenv("META_APP_ID") or not os.getenv("META_APP_SECRET"):
        raise RuntimeError("META_APP_ID / META_APP_SECRET が未設定です")

# ===== 共通リクエスト（appsecret_proof自動付与） =====
def api_get(path:str, params:dict|None=None, access_token:str|None=None):
    from hashlib import sha256
    import hmac, logging, requests
    log = logging.getLogger(__name__)
    params = params or {}
    if access_token:
        params["access_token"] = access_token
        # appsecret_proof
        if APP_SECRET:
            digest = hmac.new(APP_SECRET.encode("utf-8"), access_token.encode("utf-8"), sha256).hexdigest()
            params["appsecret_proof"] = digest
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=15)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            log.error("Graph GET %s %s -> %s (%s): %s",
                      path, params, r.status_code, err.get("code"), err.get("message"))
        except Exception:
            log.error("Graph GET %s %s -> %s body=%r", path, params, r.status_code, r.text[:300])
        r.raise_for_status()
    return r.json()

def api_post(path: str, data=None, access_token: str | None = None):
    _ensure_conf()
    data = dict(data or {})
    if access_token:
        data["access_token"] = access_token
        data["appsecret_proof"] = _appsecret_proof(access_token)
    r = requests.post(f"{GRAPH}/{path.lstrip('/')}", data=data, timeout=15)
    r.raise_for_status()
    return r.json()

# ===== OAuth URL 作成 =====
def _default_redirect_uri():
    """META_OAUTH_REDIRECT_URI があれば最優先。無ければ SITE_BASE から組み立て。"""
    ru = os.getenv("META_OAUTH_REDIRECT_URI")
    if ru:
        return ru
    base = (os.getenv("SITE_BASE") or "").rstrip("/")
    if base:
        return f"{base}/oauth/meta/callback/"
    raise RuntimeError("META_OAUTH_REDIRECT_URI か SITE_BASE を設定してください")

def oauth_url(scopes:list, state:str, redirect_uri:str|None=None):
    """外から渡された redirect_uri をそのまま使う。未指定なら .env から決める。"""
    _ensure_conf()
    app_id = os.getenv("META_APP_ID")
    ru = redirect_uri or _default_redirect_uri()
    params = {
        "client_id": app_id,
        "redirect_uri": ru,
        "scope": ",".join([s.strip() for s in scopes if s.strip()]),
        "response_type": "code",
        "state": state,
    }
    return f"https://www.facebook.com/{GRAPH_VER}/dialog/oauth?{urlencode(params)}"

# ===== code -> user access token =====
def exchange_code(code:str, redirect_uri:str|None=None):
    """トークン交換時も同じ redirect_uri を使う必要がある。"""
    _ensure_conf()
    app_id     = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    ru = redirect_uri or _default_redirect_uri()

    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": ru,
        "code": code,
    }, timeout=15)
    r.raise_for_status()
    j = r.json()
    token = j["access_token"]

    dbg = requests.get(f"{GRAPH}/debug_token", params={
        "input_token": token,
        "access_token": f"{app_id}|{app_secret}",
    }, timeout=15).json()
    data = dbg.get("data", {})
    user_id = data.get("user_id")
    scopes  = data.get("scopes", [])
    exp     = data.get("expires_at")
    expires_at = dt.datetime.fromtimestamp(exp, tz=dt.timezone.utc) if exp else None
    return token, user_id, scopes, expires_at

# ===== ユーザー短期 -> 長期トークン交換 =====
def exchange_long_lived(user_token: str) -> dict:
    """
    戻り値: {access_token, token_type, expires_in}
    """
    _ensure_conf()
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": user_token,
    }
    r = requests.get(f"{GRAPH}/oauth/access_token", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

# ===== 権限 / ページ / IGBA 取得 =====
def me_permissions(token: str):
    """
    (granted, declined) を返す簡易版
    """
    r = api_get("me/permissions", access_token=token)
    items = r.get("data", []) or []
    granted = [i["permission"] for i in items if i.get("status") == "granted"]
    declined = [i["permission"] for i in items if i.get("status") != "granted"]
    return granted, declined

def me_accounts(token: str) -> dict:
    """所有ページ一覧（name,id,access_token,perms など）"""
    return api_get(
        "me/accounts",
        params={"fields": "name,id,access_token,tasks"},
        access_token=token,
    )

def list_pages(token: str):
    """後方互換：従来の返し（data配列）"""
    return me_accounts(token).get("data", [])

def page_ig_business(page_id: str, page_token: str):
    """ページに紐づく InstagramBusinessAccount を取得"""
    r = api_get(
        f"{page_id}",
        params={"fields": "instagram_business_account{id,username}"},
        access_token=page_token,
    )
    return r.get("instagram_business_account")

# エイリアス（後方互換）
page_to_ig = page_ig_business

# ===== Webhook購読作成（アプリ単位） =====
def subscribe_webhooks(callback_url: str, verify_token: str | None = None, *, objects=("instagram", "page")) -> dict:
    """
    /{app-id}/subscriptions に対して購読を作成/更新
    アクセストークンは app access token (app_id|app_secret) を使用
    """
    _ensure_conf()
    verify_token = verify_token or VERIFY_TOKEN
    app_token = f"{APP_ID}|{APP_SECRET}"
    fields_map = {
        "instagram": "comments,mentions,messages",
        "page": "feed,conversations",
    }
    results = {}
    for obj in objects:
        fields = fields_map.get(obj)
        if not fields:
            continue
        res = api_post(
            f"{APP_ID}/subscriptions",
            data={"object": obj, "callback_url": callback_url, "verify_token": verify_token, "fields": fields},
            access_token=app_token,
        )
        results[obj] = res
    return results

def token_subject(access_token: str) -> tuple[str, str]:
    """
    return ("user", user_id) or ("page", page_id)
    """
    # まず debug_token で種別判定
    app_token = f"{APP_ID}|{APP_SECRET}"
    dbg = api_get(
        "debug_token",
        params={"input_token": access_token, "access_token": app_token},
        base="graph"  # 自前の api_get で base 切替してるなら
    )["data"]
    ttype = dbg.get("type")  # "USER" or "PAGE"
    if ttype == "PAGE":
        # ページトークン → /me は Page
        me = api_get("me", params={"fields": "id,name,category"}, access_token=access_token)
        return "page", me["id"]
    else:
        # ユーザートークン → /me は User（category は無い）
        me = api_get("me", params={"fields": "id,name"}, access_token=access_token)
        return "user", me["id"]

def import_page(page_id: str, token: str):
    saved = []

    def fetch_with(page_token):
        page = api_get(
            page_id,
            params={"fields": "name,instagram_business_account{id,username}"},
            access_token=page_token
        )
        ig = (page.get("instagram_business_account") or {})
        if not ig.get("id"):
            raise RuntimeError("no ig_business_account on page")
        # --- 保存 ---
        obj, created = InstagramBusinessAccount.objects.update_or_create(
            ig_business_id=ig["id"],
            defaults=dict(
                username=ig.get("username") or "",
                fb_page_id=page_id,
                display_name=page.get("name") or "",
                access_token=page_token,
            ),
        )
        saved.append(ig["id"])
        return created

    # まず「ページトークン前提」で試す
    try:
        created = fetch_with(token)
        return {"ok": True, "saved": saved, "created": created, "errors": []}
    except Exception:
        pass

    # ダメならユーザートークンとしてページトークンを引く
    me_accounts = api_get(
        "me/accounts",
        params={"fields": "id,name,access_token"},
        access_token=token
    )["data"]
    page = next((p for p in me_accounts if p["id"] == page_id), None)
    if not page:
        return {"ok": False, "error": "the user token has no access to the page"}

    created = fetch_with(page["access_token"])
    return {"ok": True, "saved": saved, "created": created, "errors": []}

def page_access_token_from_user(page_id: str, user_token: str) -> str | None:
    r = requests.get(f"{GRAPH}/me/accounts", params={
        "fields": "id,name,access_token",
        "access_token": user_token
    }, timeout=15)
    r.raise_for_status()
    for p in r.json().get("data", []):
        if p.get("id") == page_id:
            return p.get("access_token")
    return None

def page_to_ig_with(page_id: str, token: str):
    """与えた token でページ→IG解決"""
    r = requests.get(f"{GRAPH}/{page_id}", params={
        "fields": "instagram_business_account{id,username}",
        "access_token": token
    }, timeout=15)
    r.raise_for_status()
    return r.json().get("instagram_business_account")

def api_post_retry(path: str, *, params=None, json=None, form=None, tries=2):
    """
    Meta Graph API POST ラッパ（429時に1回だけ待って再試行）
    form は x-www-form-urlencoded、json は application/json
    """
    last_exc = None
    for i in range(tries):
        try:
            if json is not None:
                return metaapi.api_post(path, json=json, params=params)
            return metaapi.api_post(path, data=form, params=params)
        except Exception as e:
            last_exc = e
            msg = str(e)
            # 超簡易判定：429 あるいは rate/limit を含むときは軽く待って1回だけリトライ
            if i == tries - 1 or ("429" not in msg and "rate" not in msg.lower()):
                break
            time.sleep(2.0 * (i + 1))
    log.exception("meta api post failed: path=%s params=%s json=%s form=%s", path, params, json, form)
    raise last_exc

# ===== デバッグ補助 =====
def debug_token(token: str) -> dict:
    _ensure_conf()
    r = requests.get(
        f"{GRAPH}/debug_token",
        params={"input_token": token, "access_token": f"{APP_ID}|{APP_SECRET}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

__all__ = [
    "GRAPH", "oauth_url", "exchange_code", "exchange_long_lived",
    "me_permissions", "me_accounts", "list_pages", "page_ig_business", "page_to_ig",
    "api_get", "api_post", "subscribe_webhooks", "debug_token",
]
