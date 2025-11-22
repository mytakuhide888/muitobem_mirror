# app/console/views/webhooks.py  ← 完全置き換え版

from __future__ import annotations

import os
import json
import logging
import hashlib
import hmac
from datetime import datetime
from typing import Optional, Dict, Any

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt


log = logging.getLogger(__name__)

# === env (起動時に読み込む) ===
APP_SECRET: str = os.getenv("META_APP_SECRET", "")                   # 恒久運用で使うアプリの App Secret
IG_SECRET: str = os.getenv("META_IG_APP_SECRET", "")                 # （診断/暫定用）IG側 Secret
ALLOW_IG: bool = (os.getenv("META_WEBHOOK_ALLOW_IG_SECRET_FOR_TEST", "0") == "1")
VERIFY_TOKEN: str = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
DEBUG_DUMP: bool = str(getattr(settings, "DEBUG_WEBHOOK_DUMP", os.getenv("DEBUG_WEBHOOK_DUMP", "0"))) == "1"

DUMP_DIR = "/app/var/webhook_dumps"


# ---------- helpers ----------
def _norm_sig(v: Optional[str]) -> Optional[str]:
    """'sha256=...' / 'sha1=...' → ハッシュ本体だけに正規化"""
    if not v:
        return None
    return v.split("=", 1)[-1].strip()


def _calc(hmac_key: str, raw: bytes, alg: str) -> str:
    """HMAC 計算（sha256 / sha1）"""
    if alg == "sha1":
        return hmac.new(hmac_key.encode("utf-8"), raw, hashlib.sha1).hexdigest()
    return hmac.new(hmac_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _dump_preverify(raw: bytes, headers: Dict[str, str]) -> str:
    """署名検証前のダンプ（json + raw）。返り値はベース名（タイムスタンプ_ハッシュ）"""
    if not DEBUG_DUMP:
        return ""
    os.makedirs(DUMP_DIR, exist_ok=True)
    hh = hashlib.sha256(raw).hexdigest()[:16]
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    base = f"{ts}_{hh}"
    # 1) JSON
    try:
        with open(os.path.join(DUMP_DIR, f"{base}_preverify.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"phase": "preverify", "headers": dict(headers), "body": json.loads(raw.decode("utf-8") or "{}")},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        # JSON化に失敗しても raw は必ず残す
        pass
    # 2) RAW
    try:
        with open(os.path.join(DUMP_DIR, f"{base}.raw"), "wb") as fr:
            fr.write(raw)
    except Exception:
        pass
    return base


def _dump_verified(raw: bytes, headers: Dict[str, str], via: str) -> None:
    """署名検証 OK 後のダンプ"""
    if not DEBUG_DUMP:
        return
    try:
        os.makedirs(DUMP_DIR, exist_ok=True)
        hh = hashlib.sha256(raw).hexdigest()[:16]
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        with open(os.path.join(DUMP_DIR, f"{ts}_{hh}_verified.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "phase": "verified",
                    "verified_via": via,  # "app" or "ig"
                    "headers": dict(headers),
                    "body": json.loads(raw.decode("utf-8") or "{}"),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass


# ---------- main endpoint ----------
@csrf_exempt
def meta_webhook(request):
    """
    Unified webhook endpoint for Facebook/Instagram products.

    - GET:  hub.challenge を VERIFY_TOKEN で検証
    - POST: X-Hub-Signature-256 / X-Hub-Signature を検証
            まず APP_SECRET で検証。許可設定(ALLOW_IG)が有効なら IG_SECRET の一致も OK。
    """
    # --- GET verification ---
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token and token == (VERIFY_TOKEN or ""):
            return HttpResponse(challenge or "")
        return HttpResponse(status=403)

    # --- POST ---
    raw: bytes = request.body or b""

    # preverify dump（診断用。必ず先に残す）
    _dump_preverify(raw, request.headers)

    hdr256 = request.headers.get("X-Hub-Signature-256")  # 'sha256=HEX'
    hdr1 = request.headers.get("X-Hub-Signature")        # 'sha1=HEX'
    got256 = _norm_sig(hdr256)
    got1 = _norm_sig(hdr1)

    # 署名検証：APP → IG（診断のため両方計算）
    used = None  # "app" or "ig"
    ok = False
    calc_dbg = ""

    if got256:  # sha256 署名
        calc_app = _calc(APP_SECRET, raw, "sha256") if APP_SECRET else ""
        calc_ig = _calc(IG_SECRET, raw, "sha256") if IG_SECRET else ""
        if APP_SECRET and got256 == calc_app:
            ok, used = True, "app"
        elif IG_SECRET and got256 == calc_ig:
            ok, used = (ALLOW_IG is True), "ig"
        calc_dbg = f"app={calc_app} ig={calc_ig}"
    elif got1:  # sha1 署名（古い互換）
        calc_app = _calc(APP_SECRET, raw, "sha1") if APP_SECRET else ""
        calc_ig = _calc(IG_SECRET, raw, "sha1") if IG_SECRET else ""
        if APP_SECRET and got1 == calc_app:
            ok, used = True, "app"
        elif IG_SECRET and got1 == calc_ig:
            ok, used = (ALLOW_IG is True), "ig"
        calc_dbg = f"app={calc_app} ig={calc_ig}"

    if not ok:
        log.warning(
            "webhook signature invalid; got=%s calc(%s) allow_ig=%s",
            hdr256 or hdr1,
            calc_dbg,
            ALLOW_IG,
        )
        return HttpResponse(status=403)

    log.info("webhook signature OK via=%s", used)
    _dump_verified(raw, request.headers, used or "")

    # --- parse payload ---
    try:
        payload: Dict[str, Any] = json.loads(raw.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid json")

    log.info("meta webhook payload ok: %s", payload)

    # --- Instagram: DM/コメントの保存（冪等化） ---
    try:
        if isinstance(payload, dict) and payload.get("object") == "instagram":
            from ig.services.webhook_handlers import ingest_instagram_messaging
            created = ingest_instagram_messaging(payload)
            log.info("instagram webhook ingested: created=%s", created)
    except Exception as e:
        log.exception("instagram webhook ingest failed: %s", e)

    return JsonResponse({"ok": True})
