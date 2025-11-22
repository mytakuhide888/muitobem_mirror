# app/ig/admin.py

from __future__ import annotations

import json, re
from django.contrib import admin, messages
from django.contrib.admin.sites import NotRegistered
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from social_core.admin_mixins import TimeStampedAdminMixin
from social.services.meta_tokens import ensure_fresh_page_token_by_igbiz
from datetime import timedelta
import ig.models as ig_models

# ig 側モデル
from .models import (
    InstagramBusinessAccount,
    IGPost,
    IGScheduledPost,
    IGBroadcast,
    IGDMThread,
    IGDMMessage,
    IGAutoReplyTemplate,
    IGAutoReplyRule,
    IGWebhookEvent,
    IGDMReplyLog,
)

# social 側
from social.models import DMMessage, Platform
import social.admin as social_admin

# 送信API
from social.services.ig_api import send_dm  # send_dm(access_token, recipient_id, text) -> Dict


# ===== 既存 ig.* の登録 =====

@admin.register(InstagramBusinessAccount)
class InstagramBusinessAccountAdmin(admin.ModelAdmin):
    list_display = ("display_name", "username", "ig_business_id", "fb_page_id", "webhook_subscribed", "updated_at")
    search_fields = ("display_name", "username", "ig_business_id", "fb_page_id")
    list_filter = ("webhook_subscribed",)
    fieldsets = (
        (None, {
            "fields": (
                "display_name", "username",
                "ig_business_id", "fb_page_id",
                "access_token",
                "page_access_token",
                "token_expires_at",
                "long_lived_user_token",
                "webhook_subscribed",
            )
        }),
    )

@admin.register(IGPost)
class IGPostAdmin(TimeStampedAdminMixin):
    list_display = ("external_post_id", "account", "posted_at", "like_count")
    search_fields = ("external_post_id", "caption")
    list_filter = ("posted_at",)


@admin.register(IGScheduledPost)
class IGScheduledPostAdmin(TimeStampedAdminMixin):
    list_display = ("title", "account", "scheduled_at", "status")
    list_filter = ("status",)


@admin.register(IGWebhookEvent)
class IGWebhookEventAdmin(TimeStampedAdminMixin):
    list_display = ("event_type", "account", "received_at", "processed")
    list_filter = ("processed",)


# ===== DMMessage の管理画面を差し替え =====

BaseDMAdmin = getattr(social_admin, "DMMessageAdmin", admin.ModelAdmin)


def _get_ig_access_token(ig_business_id: str) -> str:
    """InstagramBusinessAccount からアクセストークンを取得（直接属性→関連順に探索）。"""
    acc = (
        InstagramBusinessAccount.objects
        .filter(ig_business_id=str(ig_business_id))
        .order_by("-updated_at")
        .first()
    )
    if not acc:
        raise RuntimeError(f"IG account not found for ig_business_id={ig_business_id}")

    for attr in ("access_token", "token", "page_access_token"):
        val = getattr(acc, attr, None)
        if val:
            return val

    for rel in ("account", "social_account", "base_account"):
        rel_obj = getattr(acc, rel, None)
        if rel_obj:
            val = getattr(rel_obj, "access_token", None)
            if val:
                return val

    raise RuntimeError("access token not found on InstagramBusinessAccount or related account")


def _resolve_dm_recipient(dm: DMMessage) -> str:
    """返信先ユーザーID（sender.id → dm.user_id の順でフォールバック）。"""
    raw = dm.raw_json or {}
    sender = (raw.get("sender") or {}).get("id")
    return str(sender or dm.user_id or "")


def _resolve_biz_ig_id(dm: DMMessage) -> str:
    """送信元（ビジネスIG）= raw_json.recipient.id。"""
    raw = dm.raw_json or {}
    return str((raw.get("recipient") or {}).get("id") or "")


class PatchedDMMessageAdmin(BaseDMAdmin):
    """既存 DMMessageAdmin を拡張：返信ボタン／即返信アクション／返信フォームを提供。"""

    # 既存の列を保持しつつ、追加入れる
    def get_list_display(self, request):
        base = list(super().get_list_display(request))
        if "is_echo_flag" not in base:
            base.append("is_echo_flag")
        if "biz_id_preview" not in base:
            base.append("biz_id_preview")
        if "reply_link" not in base:
            base.append("reply_link")
        return tuple(base)

    def _reply_url(self, obj_pk: int) -> str:
        """この管理画面の返信フォームURLを返す（例: admin/social/dmmessage/<id>/reply/）"""
        return reverse("admin:social_dmmessage_reply", args=[obj_pk])

    actions = getattr(BaseDMAdmin, "actions", []) or []
    if "reply_selected_messages" not in actions:
        actions = list(actions) + ["reply_selected_messages"]

    # === 追加列 ===
    def is_echo_flag(self, obj: DMMessage):
        try:
            return bool((obj.raw_json or {}).get("message", {}).get("is_echo"))
        except Exception:
            return False
    is_echo_flag.short_description = "is_echo"

    def biz_id_preview(self, obj: DMMessage):
        try:
            raw = obj.raw_json or {}
            return (raw.get("recipient") or {}).get("id") or ""
        except Exception:
            return ""
    biz_id_preview.short_description = "biz_ig_id"

    def reply_link(self, obj: DMMessage):
        url = reverse("admin:social_dmmessage_reply", args=[obj.pk])
        return f'<a class="button" href="{url}">返信</a>'
    reply_link.allow_tags = True  # 古いテンプレ互換
    reply_link.short_description = "返信"

    # === 即返信アクション（固定文） ===
    @admin.action(description="選択したDMに即返信（固定文『Thanks!』）")
    def reply_selected_messages(self, request, queryset):
        ok = skipped = failed = 0
        for dm in queryset:
            try:
                if dm.platform != Platform.INSTAGRAM:
                    skipped += 1
                    continue
                if (dm.raw_json or {}).get("message", {}).get("is_echo"):
                    skipped += 1
                    continue

                recipient_user_id = _resolve_dm_recipient(dm)
                biz_ig_id = _resolve_biz_ig_id(dm)
                if not recipient_user_id or not biz_ig_id:
                    failed += 1
                    continue

                token = _get_ig_access_token(biz_ig_id)
                send_dm(access_token=token, recipient_id=recipient_user_id, text="Thanks!")
                ok += 1
            except Exception:
                failed += 1
        if ok:
            self.message_user(request, f"送信成功: {ok} 件", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"スキップ（is_echo/他PF）: {skipped} 件", level=messages.WARNING)
        if failed:
            self.message_user(request, f"送信失敗: {failed} 件（トークン未設定/APIエラー等）", level=messages.ERROR)

    # === 返信フォーム URL 追加 ===
    def get_urls(self):
        urls = super().get_urls()
        my = [
            path(
                "<path:object_id>/reply/",
                self.admin_site.admin_view(self.reply_form_view),
                name="social_dmmessage_reply",
            )
        ]
        return my + urls

    # === 返信フォーム本体（テンプレート使用） ===
    def reply_form_view(self, request, object_id: str, *args, **kwargs):
        dm = get_object_or_404(DMMessage, pk=object_id)

        last_inbound_at = dm.sent_at  # このDMが「相手→自分」なら十分。会話全体で見たければ同ユーザーの最新受信で置換
        now = timezone.now()
        window = timedelta(hours=24)
        remain = (last_inbound_at + window) - now
        expired = remain.total_seconds() <= 0

        # 自分発（is_echo）は返信不可
        if bool((dm.raw_json or {}).get("message", {}).get("is_echo")):
            self.message_user(request, "自分発のメッセージ（is_echo=True）には返信できません。", level=messages.WARNING)
            return redirect("admin:social_dmmessage_change", object_id)

        accounts = list(
            ig_models.InstagramBusinessAccount.objects.all().values("id", "ig_business_id", "username", "display_name")
        )

        if request.method == "POST":
            if expired:
                messages.error(request, "送信失敗: 24時間の返信可能時間を過ぎています（ユーザー起点から24h）。")
                return redirect(request.path)
            biz_pk = request.POST.get("biz_pk")
            text = (request.POST.get("text") or "").strip()

            recipient_user_id = _resolve_dm_recipient(dm)
            biz_ig_id = _resolve_biz_ig_id(dm)

            if not recipient_user_id:
                messages.error(request, "送信失敗: 受信者の user_id（sender.id）が解決できません。")
                return redirect(request.path)

            token = None
            if biz_pk:
                acc = get_object_or_404(ig_models.InstagramBusinessAccount, pk=biz_pk)
                for attr in ("access_token", "token", "page_access_token"):
                    token = token or getattr(acc, attr, None)
                if not token:
                    for rel in ("account", "social_account", "base_account"):
                        rel_obj = getattr(acc, rel, None)
                        token = token or (getattr(rel_obj, "access_token", None) if rel_obj else None)
            else:
                if biz_ig_id:
                    token = _get_ig_access_token(biz_ig_id)

            if not token:
                messages.error(request, "送信失敗: 送信元Instagramビジネスアカウントのトークンが見つかりません。")
                return redirect(request.path)

            if not text:
                messages.error(request, "送信失敗: 返信本文が空です。")
                return redirect(request.path)

            try:
                # まずは現在の token で送信
                resp = send_dm(access_token=token, recipient_id=recipient_user_id, text=text)
                IGDMReplyLog.objects.create(dm=dm, recipient_id=recipient_user_id, biz_ig_id=biz_ig_id,
                                            text=text, ok=True, http_status=200, response=resp)
                self.message_user(request, "送信しました。", level=messages.SUCCESS)
                return redirect("admin:social_dmmessage_change", object_id)
            except Exception as e:
                import json, re, traceback

                # --- 例外から HTTP/JSON を素直に取り出す ---
                status = None
                err_payload = {}
                args = getattr(e, "args", ())
                if args:
                    last = args[-1]
                    if isinstance(last, dict):
                        status = last.get("status")
                        if isinstance(last.get("json"), dict):
                            err_payload = last["json"]
                        elif isinstance(last.get("body"), dict):
                            err_payload = last["body"]
                        else:
                            # 何もなければ text を JSON 解析トライ
                            txt = last.get("text") or ""
                            try:
                                maybe = json.loads(txt)
                                if isinstance(maybe, dict):
                                    err_payload = maybe
                            except Exception:
                                pass
                    elif isinstance(last, (str, bytes)):
                        s = last.decode("utf-8", "ignore") if isinstance(last, bytes) else last
                        try:
                            maybe = json.loads(s)
                            if isinstance(maybe, dict):
                                err_payload = maybe
                        except Exception:
                            m = re.search(r'(\{.*\})', s, flags=re.DOTALL)
                            if m:
                                try:
                                    err_payload = json.loads(m.group(1))
                                except Exception:
                                    err_payload = {}
                # フォールバック
                if not isinstance(err_payload, dict):
                    err_payload = {}

                err = (err_payload.get("error") or {})
                code = err.get("code")
                sub  = err.get("error_subcode")
                fbtr = err.get("fbtrace_id")
                msg  = (err.get("message") or str(e)).strip()

                # 人間向けメッセージ
                if code == 200 and sub in (2534048,):
                    msg_human = (
                        "送信失敗: 権限不足（instagram_manage_messages の Advanced Access 未承認 "
                        "または宛先IGユーザーがアプリのロール外）。\n"
                        "対処: Meta Dev で 1) テスターに宛先を追加＆承諾、2) instagram_manage_messages を Advanced に。\n"
                        f"[code={code} sub={sub} fbtrace_id={fbtr}] {msg}"
                    )
                else:
                    msg_human = f"送信失敗: {msg} (code={code}, sub={sub}, fbtrace_id={fbtr})"

                # 画面のフラッシュメッセージに “そのまま” 出す
                messages.error(request, msg_human)

                # 送信履歴にも JSON で残す（HTTP ステータス含む）
                try:
                    IGDMReplyLog.objects.create(
                        dm=dm,
                        recipient_id=recipient_user_id,
                        biz_ig_id=biz_ig_id,
                        text=text,
                        ok=False,
                        http_status=(status or 0),
                        response=err_payload if err_payload else {"error": msg},
                    )
                except Exception:
                    pass

                # イベント（任意）— 解析材料として保存
                try:
                    ig_models.IGWebhookEvent.objects.create(
                        event_type="DM_REPLY_ERROR",
                        account=ig_models.InstagramBusinessAccount.objects.filter(ig_business_id=biz_ig_id).first(),
                        payload={"request": {"to": recipient_user_id, "text": text}, "error": err_payload or {"message": msg}},
                        processed=False,
                    )
                except Exception:
                    pass

                # 同ページへ（テンプレ残し・履歴欄も更新される）
                return redirect(request.path)

        ctx = {
            "opts": self.model._meta,
            "original": dm,
            "object_id": object_id,
            "recipient_user_id": _resolve_dm_recipient(dm),
            "biz_ig_id": _resolve_biz_ig_id(dm),
            "accounts": accounts,
            "title": "DMに返信",
            "logs": list(IGDMReplyLog.objects.filter(dm=dm).order_by("-created_at")[:10]),
            "expire_seconds": max(0, int(remain.total_seconds())),
            "expired": expired,
        }
        return render(request, "admin/social/dmmessage/reply.html", ctx)


@admin.register(IGDMReplyLog)
class IGDMReplyLogAdmin(admin.ModelAdmin):
    list_display = ("dm", "ok", "http_status", "recipient_id", "biz_ig_id", "created_at")
    list_filter = ("ok", "http_status")
    search_fields = ("recipient_id", "biz_ig_id", "text")
    readonly_fields = ("dm","ok","http_status","recipient_id","biz_ig_id","text","response","created_at")

# 既存登録を差し替え
try:
    admin.site.unregister(DMMessage)
except NotRegistered:
    pass
admin.site.register(DMMessage, PatchedDMMessageAdmin)
