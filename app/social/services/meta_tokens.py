# app/social/services/meta_tokens.py
from __future__ import annotations
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings
from ig.models import InstagramBusinessAccount  # IGアカウントに Page ID 等が入っている前提

GRAPH = f"https://graph.facebook.com/{getattr(settings, 'DEFAULT_API_VERSION', 'v23.0')}"

def _raise(r: requests.Response):
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text}
    if not r.ok:
        raise RuntimeError(f"{r.request.method} {r.url} -> {r.status_code}: {j}")
    return j

def debug_token(input_token: str) -> Dict:
    # アプリトークン = app_id|app_secret
    app_token = f"{settings.META_APP_ID}|{settings.META_APP_SECRET}"
    r = requests.get(
        f"{GRAPH}/debug_token",
        params={"input_token": input_token, "access_token": app_token},
        timeout=20,
    )
    return _raise(r)

def exchange_long_lived_user_token(user_token: str) -> str:
    # 60日トークンへ更新（fb_exchange_token）
    r = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": user_token,
        },
        timeout=20,
    )
    j = _raise(r)
    return j["access_token"]

def fetch_pages(user_token: str) -> Dict:
    # {data:[{id,name,access_token},...]}
    r = requests.get(
        f"{GRAPH}/me/accounts",
        params={"fields": "id,name,access_token", "access_token": user_token},
        timeout=20,
    )
    return _raise(r)

def ensure_fresh_page_token_by_igbiz(ig_business_id: str) -> Tuple[str, Optional[str]]:
    """
    IGビジネスIDに紐づくFBページの Page Access Token を取得/更新して返す。
    戻り値: (page_access_token, page_id)
    - 前提: InstagramBusinessAccount に fb_page_id か ig_business_id が保存されている
    - 仕組み:
        1) 既存の token を debug_token → 失効/期限間近なら更新
        2) 更新は「ユーザー長期トークン → /me/accounts → Pageトークン」手順
    """
    # 1) IGアカウント解決
    acc = (
        InstagramBusinessAccount.objects
        .filter(ig_business_id=str(ig_business_id))
        .order_by("-updated_at")
        .first()
    )
    if not acc:
        raise RuntimeError(f"IG account not found for ig_business_id={ig_business_id}")

    page_id = getattr(acc, "fb_page_id", None)
    page_token = None

    # 候補となる既存トークン（acc.access_token / token / page_access_token / 関連account.access_token）
    candidates = []
    for attr in ("access_token", "token", "page_access_token"):
        val = getattr(acc, attr, None)
        if val: candidates.append(val)
    for rel in ("account", "social_account", "base_account"):
        rel_obj = getattr(acc, rel, None)
        if rel_obj:
            val = getattr(rel_obj, "access_token", None)
            if val: candidates.append(val)

    # 2) 既存トークンが有効ならそれを使う
    for t in candidates:
        try:
            info = debug_token(t)
            data = info.get("data", {})
            is_valid = bool(data.get("is_valid"))
            exp = int(data.get("expires_at") or 0)
            # 期限が7日未満なら更新対象にする
            import time
            near = (exp and (exp - int(time.time()) < 7*24*3600))
            if is_valid and not near:
                page_token = t
                break
        except Exception:
            pass  # 無効なら次

    if page_token:
        return page_token, page_id

    # 3) ユーザー長期トークン→ページトークンを再取得
    #    どのフィールドに保持しているか環境ごとに異なるため、
    #    関連/自分の account に user_token があればそれを使う（なければ例外）
    user_token = None
    # a) acc に user_token フィールドがある場合
    for attr in ("user_access_token", "long_lived_user_token"):
        if hasattr(acc, attr):
            user_token = getattr(acc, attr) or user_token
    # b) 関連側が持っている場合
    for rel in ("account", "social_account", "base_account"):
        rel_obj = getattr(acc, rel, None)
        if rel_obj:
            for attr in ("user_access_token", "long_lived_user_token"):
                if hasattr(rel_obj, attr):
                    user_token = getattr(rel_obj, attr) or user_token

    if not user_token:
        raise RuntimeError("長期ユーザートークンが見つかりません（自動更新の起点になるトークン）")

    # ユーザー長期トークンを延長（冪等）
    try:
        user_token = exchange_long_lived_user_token(user_token)
    except Exception:
        # ここは再発行できない場合もあるので握りつぶして続行
        pass

    pages = fetch_pages(user_token).get("data", [])
    if page_id:
        # 指定ページのtoken
        for p in pages:
            if str(p.get("id")) == str(page_id) and p.get("access_token"):
                page_token = p["access_token"]
                break
    else:
        # ひも付く IG を解決して一致するページを採用
        # （page?fields=instagram_business_account で特定するのが堅い）
        for p in pages:
            pid = p.get("id")
            if not pid: continue
            r = requests.get(
                f"{GRAPH}/{pid}",
                params={"fields": "instagram_business_account{id}", "access_token": user_token},
                timeout=20,
            )
            j = _raise(r)
            igbiz = (j.get("instagram_business_account") or {}).get("id")
            if str(igbiz) == str(ig_business_id) and p.get("access_token"):
                page_token = p["access_token"]
                page_id = pid
                break

    if not page_token:
        raise RuntimeError("ページアクセストークンの再取得に失敗しました（ユーザー・ページのひも付けを確認）")

    # 保存（可能なら）
    # acc に保存できる代表フィールドへ反映
    for attr in ("access_token", "token", "page_access_token"):
        if hasattr(acc, attr):
            setattr(acc, attr, page_token)
            try:
                acc.save(update_fields=[attr, "updated_at"])
            except Exception:
                acc.save()

    return page_token, page_id
