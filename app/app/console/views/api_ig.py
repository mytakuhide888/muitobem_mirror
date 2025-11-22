# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpRequest
from django.utils.timezone import now

from ig.models import InstagramBusinessAccount
from social.models import DMContact
from social.services import ig_api

log = logging.getLogger(__name__)


def _get_page_token(aid: int | str) -> str:
    """
    InstagramBusinessAccount の access_token（ページトークン）を取り出す。
    aid は DB の pk か ig_business_id どちらでも可。
    """
    try:
        qs = InstagramBusinessAccount.objects
        if isinstance(aid, int) or str(aid).isdigit():
            acc = qs.get(pk=int(aid))
        else:
            acc = qs.get(ig_business_id=str(aid))
    except InstagramBusinessAccount.DoesNotExist:
        raise ValueError("account not found")
    if not acc.access_token:
        raise ValueError("account has no access_token")
    return acc.access_token


@staff_member_required
@require_POST
@csrf_protect
def ig_comment_reply(request: HttpRequest):
    """
    JSON: { "account_id": <pk or ig_business_id>, "comment_id": "...", "message": "..." }
    """
    try:
        j = request.JSON if hasattr(request, "JSON") else None
    except Exception:
        j = None
    if j is None:
        # 通常の POST(form) でも動くように
        j = {
            "account_id": request.POST.get("account_id"),
            "comment_id": request.POST.get("comment_id"),
            "message": request.POST.get("message"),
        }

    account_id = j.get("account_id")
    comment_id = j.get("comment_id")
    message    = j.get("message")

    if not (account_id and comment_id and message):
        return JsonResponse({"ok": False, "error": "account_id, comment_id, message are required"}, status=400)

    try:
        token = _get_page_token(account_id)
        res = ig_api.reply_comment(comment_id=comment_id, access_token=token, text=message)
        return JsonResponse({"ok": True, "result": res})
    except Exception as e:
        log.exception("ig_comment_reply failed")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@staff_member_required
@require_POST
@csrf_protect
def ig_dm_reply(request: HttpRequest):
    """
    JSON:
      { "account_id": <pk or ig_business_id>, "ig_user_id": "<ページ側IGユーザID>", "text": "..." }
    もしくは
      { "account_id": ..., "psid": "...", "text": "..." }
      { "account_id": ..., "thread_key": "...", "text": "..." }

    優先順: thread_key > psid > ig_user_id(+照合).
    """
    try:
        j = request.JSON if hasattr(request, "JSON") else None
    except Exception:
        j = None
    if j is None:
        j = {
            "account_id": request.POST.get("account_id"),
            "ig_user_id": request.POST.get("ig_user_id"),
            "psid":       request.POST.get("psid"),
            "thread_key": request.POST.get("thread_key"),
            "text":       request.POST.get("text"),
        }

    account_id = j.get("account_id")
    text       = j.get("text") or ""
    psid       = j.get("psid")
    thread_key = j.get("thread_key")
    ig_user_id = j.get("ig_user_id")

    if not (account_id and text):
        return JsonResponse({"ok": False, "error": "account_id and text are required"}, status=400)

    try:
        token = _get_page_token(account_id)

        # 宛先の解決
        if not (psid or thread_key):
            if not ig_user_id:
                return JsonResponse({"ok": False, "error": "recipient not resolved (need psid/thread_key/ig_user_id)"}, status=400)
            contact = DMContact.objects.filter(ig_user_id=str(ig_user_id)).order_by("-last_event_at").first()
            if contact:
                psid = contact.psid or psid
                thread_key = contact.thread_key or thread_key

        # 送信（thread_key > psid の優先）
        if thread_key:
            res = ig_api.send_dm_flexible(access_token=token, thread_key=thread_key, text=text)
        elif psid:
            res = ig_api.send_dm_flexible(access_token=token, psid=psid, text=text)
        else:
            return JsonResponse({"ok": False, "error": "no psid/thread_key found for recipient"}, status=400)

        return JsonResponse({"ok": True, "result": res})
    except Exception as e:
        log.exception("ig_dm_reply failed")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
