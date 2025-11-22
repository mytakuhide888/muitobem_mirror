# app/console/views/oauth.py
import json, secrets
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse
import json, datetime as dt, logging
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.signing import TimestampSigner
from django.contrib import messages

from sns_core.models import MetaUserToken
from ig.models import InstagramBusinessAccount
# ThreadsAccount も必要になったら import
from ..utils import meta as metaapi
from django.core import signing

STATE_COOKIE = "meta_oauth_state"
STATE_MAX_AGE = 600  # 10分

import logging
log = logging.getLogger(__name__)

IG_SCOPES = [
    "pages_show_list",
    "pages_manage_metadata",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_manage_messages",
    "instagram_content_publish",
    # 使うならコメント返信も:
    # "instagram_manage_comments",
]
THREADS_SCOPES = [
    "threads_basic",
    "threads_content_publish",
    "threads_manage_replies",
]

# 必要スコープ（最小セット）: 後述の P0-2 と共通辞書にしてもOK
SCOPES_MIN = [
    "public_profile",
    "email",
    "pages_show_list",
    "pages_manage_metadata",
    "instagram_basic",
    # 投稿系を使うなら:
    # "instagram_content_publish",
]

def _issue_state(request) -> str:
    state = "console:" + timezone.now().strftime("%Y%m%dT%H%M%S") + ":" + secrets.token_urlsafe(12)
    request.session["META_OAUTH_STATE"] = state
    request.session.modified = True
    return state

def _set_state_cookies(resp, state):
    signed = signing.dumps(state, salt="meta-oauth")
    resp.set_cookie(
        STATE_COOKIE, signed, max_age=STATE_MAX_AGE,
        secure=True, httponly=True, samesite="Lax",
        domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None),
        path="/",
    )

def _pop_state_from_request(request):
    # 1) セッション
    sess = request.session.pop("META_OAUTH_STATE", None)
    # 2) 署名付きクッキー
    cookie = request.COOKIES.get(STATE_COOKIE)
    val = None
    if cookie:
        try:
            val = signing.loads(cookie, salt="meta-oauth", max_age=STATE_MAX_AGE)
        except Exception:
            val = None
    return sess, val

def _redirect_uri(request):
    try:
        return request.build_absolute_uri(reverse("meta_public:meta_oauth_cb"))
    except Exception:
        return request.build_absolute_uri("/oauth/meta/callback/")
    
def _issue_state(request) -> str:
    state = "console:" + timezone.now().strftime("%Y%m%dT%H%M%S") + ":" + secrets.token_urlsafe(12)
    request.session["META_OAUTH_STATE"] = state
    request.session.modified = True
    return state

@staff_member_required
def meta_oauth_start(request):

    #log.info(
    #    "OAuth START called: path=%s ua=%s ip=%s referer=%s session_key=%s",
    #    request.path, request.META.get("HTTP_USER_AGENT"),
    #    request.META.get("REMOTE_ADDR"), request.META.get("HTTP_REFERER"),
    #    getattr(request.session, "session_key", None),
    #)
    want_threads = request.GET.get("threads") == "1"
    raw = request.GET.get("scopes")
    scopes = [s.strip() for s in raw.split(",") if s.strip()] if raw else IG_SCOPES + (THREADS_SCOPES if want_threads else [])

    state = _issue_state(request)
    url = metaapi.oauth_url(scopes, state=state, redirect_uri=_redirect_uri(request))

    # session に積んだ値を出しておく
    #log.info("Issued STATE=%s saved_in_session=%r", state, request.session.get("META_OAUTH_STATE"))

    # ★ ここで署名付き Cookie も返す（www あり/なし両対応のため domain はワイルドカード）
    resp = redirect(url)
    resp.set_signed_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=STATE_MAX_AGE,
        secure=True,
        httponly=True,
        samesite="Lax",
        domain=".muitobem.top",  # ← 重要（www あり/なし両方で送られる）
    )
    #log.info("Set signed cookie %s; will redirect to %s", STATE_COOKIE, url)

    return resp

@staff_member_required
def meta_connect(request):
    state = secrets.token_urlsafe(24)
    request.session["meta_oauth_state"] = state
    url = metaapi.oauth_url(SCOPES_MIN, state)
    return HttpResponseRedirect(url)

@require_http_methods(["GET"])
def meta_callback(request):
    st = request.GET.get("state")
    if st != request.session.get("meta_oauth_state"):
        return HttpResponseBadRequest("state mismatch")
    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("no code")

    token, user_id, scopes, exp_at = metaapi.exchange_code(code)
    granted, declined = metaapi.me_permissions(token)

    # 保存
    MetaUserToken.objects.update_or_create(
        user_id=user_id,
        defaults=dict(
            access_token=token,
            expires_at=exp_at,
            granted_scopes=granted,
            declined_scopes=declined,
            created_by=request.user if request.user.is_authenticated else None,
        )
    )
    request.session["meta_user_id"] = user_id
    return redirect("console:accounts")  # 取り込み画面へ


@csrf_exempt
def meta_import(request):
    """
    POST JSON: {"page_id":"<FB_PAGE_ID>", "access_token":"<USER_OR_PAGE_TOKEN>"}
    ユーザートークンでもページトークンでもOK。DBに IBA を保存/更新。
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    # JSON パース
    try:
        body = request.body.decode("utf-8")
        payload = json.loads(body)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"invalid json: {e}"})

    page_id = str(payload.get("page_id") or "").strip()
    token   = str(payload.get("access_token") or "").strip()

    if not page_id or not token:
        return JsonResponse({"ok": False, "error": "page_id and access_token required"})

    try:
        result = metaapi.import_page(page_id, token)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

def meta_oauth_cb(request):
    err = request.GET.get("error")
    if err:
        return render(request, "admin/console/oauth_done.html", {"ok": False, "error": err})

    code  = request.GET.get("code")
    state = request.GET.get("state")
    if not code:
        return HttpResponseBadRequest("missing code")

    # 期待値は「セッション or 署名Cookie」のどちらか一致でOKとする
    expected_sess = request.session.pop("META_OAUTH_STATE", None)
    expected_cookie = None
    try:
        expected_cookie = request.get_signed_cookie(STATE_COOKIE)
    except Exception:
        pass
    # 使い終わったので Cookie は消す
    resp_bad = HttpResponseBadRequest("state mismatch")
    resp_bad.delete_cookie(STATE_COOKIE, domain=".muitobem.top", samesite="Lax")

    if not ((expected_sess and state == expected_sess) or (expected_cookie and state == expected_cookie)):
        # ログに残す（あなたのログ書式に合わせて）
        log.warning("OAuth state mismatch: expected(sess)=%r expected(cookie)=%r got=%r",
                    expected_sess, expected_cookie, state)
        return resp_bad

    token, user_id, scopes, expires_at = metaapi.exchange_code(
        code, redirect_uri=_redirect_uri(request)
    )
    granted, declined = metaapi.me_permissions(token)
    pages = metaapi.list_pages(token)

    # ★ DB に保存（ここが無かった）
    MetaUserToken.objects.update_or_create(
        user_id=user_id,
        defaults=dict(
            access_token=token,
            expires_at=expires_at,
            granted_scopes=granted,
            declined_scopes=declined,
            created_by=request.user if request.user.is_authenticated else None,
        )
    )
    # ★ /console/accounts/ が参照するセッションキー
    request.session["meta_user_id"] = user_id
    request.session.modified = True

    request.session["META_TOKEN"]   = token
    request.session["META_PAGES"]   = pages
    request.session["META_GRANTED"] = granted
    request.session["META_DECLINED"]= declined

    resp_ok = render(request, "admin/console/oauth_done.html", {
        "ok": True, "user_id": user_id,
        "granted": granted, "declined": declined, "pages": pages,
        "expires_at": expires_at,
    })
    resp_ok.delete_cookie(STATE_COOKIE, domain=".muitobem.top", samesite="Lax")
    return resp_ok

@staff_member_required
@require_POST
def meta_disconnect(request):
    user_id = request.session.get("meta_user_id")
    if user_id:
        MetaUserToken.objects.filter(user_id=user_id).delete()
    for k in ["META_TOKEN","META_PAGES","META_GRANTED","META_DECLINED",
              "META_OAUTH_STATE","meta_user_id"]:
        request.session.pop(k, None)
    messages.success(request, "Meta連携を解除しました。再度『Metaアカウントを連携』から実行できます。")
    return redirect("console:accounts")