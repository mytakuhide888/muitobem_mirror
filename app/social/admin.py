from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from .models import (
    FacebookAccount, ThreadsApp, ThreadsAccount, InstagramAccount,
    ScheduledPost, Post, DMMessage, DMReplyTemplate, AutoReplyRule, WebhookEvent,
    Job, DMContact, Platform
)
from ig.models import InstagramBusinessAccount
from social.services import ig_api  


class PerPageAdminMixin:
    def changelist_view(self, request, extra_context=None):
        per_page = request.GET.get('per_page')
        if per_page in ('50', '100'):
            self.list_per_page = int(per_page)
        extra_context = extra_context or {}
        extra_context['per_page'] = per_page or self.list_per_page
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(FacebookAccount)
class FacebookAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'facebook_user_id')
    search_fields = ('name', 'facebook_user_id')


@admin.register(ThreadsApp)
class ThreadsAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'threads_app_id')
    search_fields = ('name', 'threads_app_id')


@admin.register(ThreadsAccount)
class ThreadsAccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'threads_user_id', 'username')
    search_fields = ('display_name', 'threads_user_id', 'username')


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'instagram_user_id', 'username')
    search_fields = ('display_name', 'instagram_user_id', 'username')


@admin.register(ScheduledPost)
class ScheduledPostAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('status', 'platform', 'account', 'scheduled_at', 'title', 'topic')
    search_fields = ('title', 'body')
    list_filter = ('status', 'platform')
    ordering = ('-scheduled_at',)
    change_list_template = 'admin/social/change_list.html'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('approve/<int:pk>/', self.admin_site.admin_view(self.approve_view), name='social_scheduledpost_approve'),
        ]
        return custom + urls

    def approve_view(self, request, pk):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        obj = get_object_or_404(ScheduledPost, pk=pk)
        if obj.status == ScheduledPost.Status.DRAFT:
            obj.status = ScheduledPost.Status.APPROVED
            obj.save()
            messages.success(request, '承認しました。')
        return redirect('admin:social_scheduledpost_change', obj.pk)


@admin.register(Post)
class PostAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'account', 'posted_at', 'content', 'like_count', 'view_count')
    search_fields = ('content',)
    list_filter = ('platform',)
    ordering = ('-posted_at',)
    change_list_template = 'admin/social/post/change_list.html'

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse
        extra_context = extra_context or {}
        extra_context['import_url'] = reverse('social:post-import')
        extra_context['sync_url'] = reverse('social:post-sync')
        return super().changelist_view(request, extra_context=extra_context)

    class Media:
        css = {'all': ['admin/css/changelist.css']}


@admin.action(description="biz_ig_id から Instagram アカウントを自動リンク")
def link_account_from_biz_id(self, request, queryset):
    from django.db import transaction
    updated = 0
    with transaction.atomic():
        for obj in queryset.select_for_update():
            if getattr(obj, 'account_id', None):
                continue
            biz_id = getattr(obj, 'biz_ig_id', None) or getattr(obj, 'ig_biz_id', None)
            if not biz_id:
                continue
            iba = InstagramBusinessAccount.objects.filter(
                Q(external_id=str(biz_id)) | Q(external_id=biz_id)
            ).first()
            if iba:
                obj.account = iba
                obj.save(update_fields=['account'])
                updated += 1
    self.message_user(request, f"{updated} 件をリンクしました。")

@admin.register(DMMessage)
class DMMessageAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ("platform", 'account_display', "user_id", "direction", "sent_at", "reply_action")
    search_fields = ('user_id', 'text')
    list_filter = ('platform', 'direction')
    ordering = ('-sent_at',)
    actions = [link_account_from_biz_id]
    #change_list_template = 'admin/social/change_list.html'

    @admin.display(description='Account')
    def account_display(self, obj):
        # 1) すでに FK があればそれを表示
        acct = getattr(obj, 'account', None)
        if acct:
            return getattr(acct, 'display_name', None) or getattr(acct, 'username', None) or '-'

        # 2) biz_ig_id（または候補名）を拾う
        biz_id = None
        for name in ('biz_ig_id', 'ig_biz_id', 'ig_business_id', 'ig_business_account_id'):
            v = getattr(obj, name, None)
            if v:
                biz_id = str(v)
                break
        if not biz_id:
            return '-'

        # 3) 数値/文字列どちらでも当たるようにして検索
        candidates = [biz_id]
        if biz_id.isdigit():
            try:
                candidates.append(int(biz_id))
            except Exception:
                pass

        iba = InstagramBusinessAccount.objects.filter(
            Q(external_id__in=candidates) | Q(ig_business_id__in=candidates)
        ).only('username', 'display_name').first()

        return (getattr(iba, 'display_name', None) or getattr(iba, 'username', None) or '-') if iba else '-'

    def get_urls(self):
        urls = super().get_urls()
        my = [
            path("<int:pk>/reply/", self.admin_site.admin_view(self.reply_view),
                 name="social_dmmessage_reply"),
        ]
        # 自前URLを先頭に（競合回避）
        return my + urls

    def reply_action(self, obj: DMMessage):
        """
        一覧の右端に出す「返信」ボタン
        """
        if obj.platform != Platform.INSTAGRAM:
            return "-"
        url = reverse("admin:social_dmmessage_reply", args=[obj.pk])
        return format_html('<a class="button" href="{}">返信</a>', url)
    reply_action.short_description = "返信"

    # 返信フォーム + POST処理
    def reply_view(self, request, pk: int):
        obj = get_object_or_404(DMMessage, pk=pk)
        if obj.platform != Platform.INSTAGRAM:
            messages.error(request, "InstagramのDMにのみ対応しています。")
            return redirect("admin:social_dmmessage_changelist")

        # 候補アカウント（ページトークン所持）
        ig_accounts = InstagramBusinessAccount.objects.filter(is_active=True).order_by("id")
        initial_ig_id = None

        # 1) 受信者の解決（thread_key > psid > ig_user_id）
        ext = obj.raw_json or {}
        exids = (obj.external_ids or {}) if hasattr(obj, "external_ids") else {}
        ig_user_id = exids.get("ig_user_id") or str(obj.user_id or "")
        thread_key = exids.get("thread_key") or ext.get("thread_key")
        psid = exids.get("psid") or ext.get("psid")

        if not (thread_key or psid):
            c = DMContact.objects.filter(ig_user_id=str(ig_user_id)).order_by("-last_event_at").first()
            if c:
                thread_key = thread_key or c.thread_key
                psid = psid or c.psid

        # 2) 既定の送信元アカウント（候補が1件ならそれ）
        if ig_accounts.count() == 1:
            initial_ig_id = ig_accounts.first().pk

        if request.method == "POST":
            text = (request.POST.get("text") or "").strip()
            ig_pk = request.POST.get("ig_account")
            if not text:
                messages.error(request, "本文を入力してください。")
            elif not (thread_key or psid or ig_user_id):
                messages.error(request, "宛先が解決できません（thread_key/psid/ig_user_id のいずれかが必要）。")
            else:
                try:
                    # アカウント決定
                    if ig_pk:
                        igba = InstagramBusinessAccount.objects.get(pk=int(ig_pk))
                    else:
                        igba = ig_accounts.first()
                    if not (igba and igba.access_token):
                        raise RuntimeError("有効な送信元アカウント（アクセストークン付き）が必要です。")

                    # 最終的に thread_key > psid の順で送信
                    res = None
                    if thread_key:
                        res = ig_api.send_dm_flexible(access_token=igba.access_token,
                                                      thread_key=thread_key, text=text)
                    elif psid:
                        res = ig_api.send_dm_flexible(access_token=igba.access_token,
                                                      psid=psid, text=text)
                    else:
                        # thread_key/psid が無ければ、DMContact 経由で再解決
                        c = DMContact.objects.filter(ig_user_id=str(ig_user_id)).order_by("-last_event_at").first()
                        if c and (c.thread_key or c.psid):
                            res = ig_api.send_dm_flexible(access_token=igba.access_token,
                                                          thread_key=c.thread_key, psid=c.psid, text=text)
                        else:
                            raise RuntimeError("受信者の thread_key / psid が見つかりません。")

                    messages.success(request, f"送信しました: {res}")
                    # 一覧へ戻す
                    return redirect("admin:social_dmmessage_changelist")
                except Exception as e:
                    messages.error(request, f"送信失敗: {e}")

        context = dict(
            self.admin_site.each_context(request),
            title="DMに返信",
            opts=self.model._meta,
            object=obj,
            ig_accounts=ig_accounts,
            initial_ig_id=initial_ig_id,
            ig_user_id=ig_user_id,
            thread_key=thread_key,
            psid=psid,
        )
        return render(request, "admin/social/dmmessage/reply_form.html", context)


@admin.register(DMReplyTemplate)
class DMReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'enabled')
    search_fields = ('name', 'keywords')
    list_filter = ('platform', 'enabled')


@admin.register(WebhookEvent)
class WebhookEventAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'field', 'received_at', 'signature_valid')
    list_filter = ('platform', 'signature_valid')
    ordering = ('-received_at',)
    change_list_template = 'admin/social/change_list.html'


@admin.register(Job)
class JobAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('job_type', 'platform', 'run_at', 'status', 'retries', 'last_error')
    list_filter = ('platform', 'status', 'job_type')
    ordering = ('-run_at',)
    actions = ['run_now']

    def run_now(self, request, queryset):
        queryset.update(run_at=timezone.now(), status=Job.Status.PENDING)
    run_now.short_description = '今すぐ実行'
