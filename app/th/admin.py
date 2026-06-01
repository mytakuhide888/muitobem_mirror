from django.contrib import admin
from social_core.admin_mixins import TimeStampedAdminMixin
from .models import (
    ThreadsAccount, THPost, THScheduledPost,
    THBroadcast, THDMThread, THDMMessage,
    THAutoReplyTemplate, THAutoReplyRule, THWebhookEvent,
    THBuzzAuthor, THBuzzPost, THBuzzSearchJob,
    ConceptProject, ConceptProjectAuthor,
    ResearchAccount, ScraperEventLog, ScraperNotificationConfig,
)


@admin.register(ThreadsAccount)
class ThreadsAccountAdmin(TimeStampedAdminMixin):
    list_display = ('display_name', 'username', 'external_id', 'is_active')
    search_fields = ('display_name', 'username', 'external_id')


@admin.register(THPost)
class THPostAdmin(TimeStampedAdminMixin):
    list_display = ('external_post_id', 'account', 'posted_at', 'like_count')
    search_fields = ('external_post_id', 'caption')
    list_filter = ('posted_at',)


@admin.register(THScheduledPost)
class THScheduledPostAdmin(TimeStampedAdminMixin):
    list_display = ('title', 'account', 'scheduled_at', 'status')
    list_filter = ('status',)


@admin.register(THWebhookEvent)
class THWebhookEventAdmin(TimeStampedAdminMixin):
    list_display = ('event_type', 'account', 'received_at', 'processed')
    list_filter = ('processed',)


@admin.register(THBuzzAuthor)
class THBuzzAuthorAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'display_name', 'followers_count',
        'growth_score', 'quality_score', 'followers_per_day', 'account_age_days',
        'avg_likes', 'is_verified', 'is_concept_candidate', 'is_quality_account', 'is_excluded', 'updated_at',
    )
    search_fields = ('username', 'display_name', 'category_tags')
    list_filter = ('is_verified', 'is_concept_candidate', 'is_quality_account', 'is_excluded', 'category_tags')
    readonly_fields = (
        'first_scraped_at', 'updated_at',
        'growth_score', 'followers_per_day', 'account_age_days',
        'total_post_count', 'earliest_post_at', 'latest_post_at',
        'avg_likes', 'avg_replies', 'is_concept_candidate',
        'quality_score', 'is_quality_account', 'good_post_ratio',
        'recent_post_count', 'avg_post_interval_days',
    )
    fieldsets = (
        ('基本情報', {
            'fields': (
                'username', 'display_name', 'bio',
                'followers_count', 'following_count', 'is_verified',
                'profile_url',
            ),
        }),
        ('成長指標（自動計算）', {
            'fields': (
                'growth_score', 'followers_per_day', 'account_age_days',
                'total_post_count', 'avg_likes', 'avg_replies',
                'earliest_post_at', 'latest_post_at',
                'is_concept_candidate',
            ),
        }),
        ('品質指標（自動計算）', {
            'fields': (
                'quality_score', 'is_quality_account', 'good_post_ratio',
                'recent_post_count', 'avg_post_interval_days',
            ),
        }),
        ('分類・メモ', {
            'fields': ('category_tags', 'memo'),
        }),
        ('メタ情報', {
            'fields': ('raw_json', 'first_scraped_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(THBuzzPost)
class THBuzzPostAdmin(admin.ModelAdmin):
    list_display = ('author', 'text_content_short', 'like_count', 'reply_count', 'engagement_score', 'is_viral', 'scraped_at')
    search_fields = ('text_content', 'author__username', 'search_keyword')
    list_filter = ('is_viral', 'search_keyword', 'scraped_at')
    readonly_fields = ('scraped_at',)

    @admin.display(description='投稿文(抜粋)')
    def text_content_short(self, obj):
        return obj.text_content[:50] + '...' if len(obj.text_content) > 50 else obj.text_content


@admin.register(THBuzzSearchJob)
class THBuzzSearchJobAdmin(admin.ModelAdmin):
    list_display = ('keywords_short', 'job_type', 'status', 'result_count', 'scheduled_at', 'started_at', 'completed_at')
    list_filter = ('status', 'job_type')
    readonly_fields = ('created_at',)

    @admin.display(description='キーワード')
    def keywords_short(self, obj):
        return obj.keywords[:50] + '...' if len(obj.keywords) > 50 else obj.keywords


class ConceptProjectAuthorInline(admin.TabularInline):
    model = ConceptProjectAuthor
    extra = 0
    readonly_fields = ('ai_summary',)


@admin.register(ConceptProject)
class ConceptProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'character', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ConceptProjectAuthorInline]


# ─── Phase G: リサーチ用スクレイパ運用 ──────────────────────────────

@admin.register(ResearchAccount)
class ResearchAccountAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'threads_username', 'status', 'current_operation_mode',
        'warmup_started_at', 'warmup_duration_days',
        'daily_request_count', 'last_used_at', 'updated_at',
    )
    list_filter = ('status', 'current_operation_mode', 'auto_promote')
    search_fields = ('name', 'threads_username')
    readonly_fields = (
        'last_used_at', 'daily_request_count', 'daily_count_reset_at',
        'suspended_at', 'created_at', 'updated_at',
        'operation_mode_started_at', 'operation_mode_locked_until',
    )
    fieldsets = (
        ('基本', {
            'fields': ('name', 'threads_username', 'storage_state_path', 'status'),
        }),
        ('操作モード（VPS / MOBILE 排他、Phase 3-B）', {
            'fields': (
                'current_operation_mode',
                'operation_mode_started_at', 'operation_mode_locked_until',
            ),
            'description': (
                '同時刻に異なる位置から同一アカウントにアクセスすると '
                'Meta から「乗っ取り疑い」を持たれる。VPS と MOBILE は排他にし、'
                '切替時は 15 分の cooldown を強制する。IDLE への戻しは cooldown なし。'
            ),
        }),
        ('VPSウォームアップ', {
            'fields': ('warmup_started_at', 'warmup_duration_days', 'auto_promote'),
            'description': (
                'VPS スタートアップ時の安全運転期間。デフォルト14日が経過すると '
                'auto_promote=True の場合に ACTIVE へ自動昇格。'
            ),
        }),
        ('凍結／停止', {
            'fields': ('suspended_at', 'suspended_reason'),
        }),
        ('使用状況（自動更新）', {
            'fields': ('last_used_at', 'daily_request_count', 'daily_count_reset_at'),
            'classes': ('collapse',),
        }),
        ('メモ／メタ', {
            'fields': ('memo', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['action_promote_to_active', 'action_pause_warmup', 'action_resume_warmup']

    @admin.action(description='選択行を ACTIVE に昇格')
    def action_promote_to_active(self, request, queryset):
        n = queryset.update(status=ResearchAccount.STATUS_ACTIVE)
        self.message_user(request, f'{n} 件を ACTIVE に変更しました')

    @admin.action(description='選択行を VPS_WARMUP に戻す')
    def action_pause_warmup(self, request, queryset):
        from django.utils import timezone as _tz
        n = 0
        for ra in queryset:
            ra.status = ResearchAccount.STATUS_VPS_WARMUP
            if not ra.warmup_started_at:
                ra.warmup_started_at = _tz.now()
            ra.save(update_fields=['status', 'warmup_started_at', 'updated_at'])
            n += 1
        self.message_user(request, f'{n} 件を VPS_WARMUP に変更しました')

    @admin.action(description='SUSPENDED 解除（VPS_WARMUP で再開）')
    def action_resume_warmup(self, request, queryset):
        from django.utils import timezone as _tz
        n = 0
        for ra in queryset.filter(status=ResearchAccount.STATUS_SUSPENDED):
            ra.status = ResearchAccount.STATUS_VPS_WARMUP
            ra.warmup_started_at = _tz.now()
            ra.suspended_at = None
            ra.suspended_reason = ''
            ra.save(update_fields=[
                'status', 'warmup_started_at',
                'suspended_at', 'suspended_reason', 'updated_at',
            ])
            n += 1
        self.message_user(request, f'{n} 件を VPS_WARMUP に再開しました')


@admin.register(ScraperEventLog)
class ScraperEventLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'account', 'event_type', 'level', 'notified', 'message_short')
    list_filter = ('event_type', 'level', 'notified')
    search_fields = ('message',)
    readonly_fields = (
        'account', 'event_type', 'level', 'message',
        'payload', 'notified', 'created_at',
    )
    date_hierarchy = 'created_at'

    @admin.display(description='メッセージ抜粋')
    def message_short(self, obj):
        msg = obj.message or ''
        return msg[:80] + ('…' if len(msg) > 80 else '')

    def has_add_permission(self, request):
        # ログは自動記録のみ
        return False


@admin.register(ScraperNotificationConfig)
class ScraperNotificationConfigAdmin(admin.ModelAdmin):
    list_display = (
        'enabled', 'min_level', 'aggregate_window_min',
        'aggregate_threshold', 'auto_stop_on_suspension', 'updated_at',
    )
    fieldsets = (
        ('通知有効化', {
            'fields': ('enabled', 'recipient_emails'),
            'description': 'recipient_emails はカンマ区切りで複数指定可。',
        }),
        ('通知対象', {
            'fields': ('notify_events', 'min_level'),
            'description': (
                'notify_events は ScraperEventLog.event_type 文字列の JSON 配列。'
                '例: ["SUSPENSION_DETECTED", "HTTP_403", "JOB_FAILED"]'
            ),
        }),
        ('集約', {
            'fields': ('aggregate_window_min', 'aggregate_threshold'),
            'description': '同種イベントが N 分以内に閾値件数以上で 1 通にまとめる。',
        }),
        ('自動停止', {
            'fields': ('auto_stop_on_suspension',),
        }),
    )

    def has_add_permission(self, request):
        # シングルトン（pk=1）
        return not ScraperNotificationConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
