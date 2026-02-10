from django.contrib import admin
from social_core.admin_mixins import TimeStampedAdminMixin
from .models import (
    ThreadsAccount, THPost, THScheduledPost,
    THBroadcast, THDMThread, THDMMessage,
    THAutoReplyTemplate, THAutoReplyRule, THWebhookEvent,
    THBuzzAuthor, THBuzzPost, THBuzzSearchJob,
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
        'growth_score', 'followers_per_day', 'account_age_days',
        'avg_likes', 'is_verified', 'updated_at',
    )
    search_fields = ('username', 'display_name', 'category_tags')
    list_filter = ('is_verified', 'category_tags')
    readonly_fields = (
        'first_scraped_at', 'updated_at',
        'growth_score', 'followers_per_day', 'account_age_days',
        'total_post_count', 'earliest_post_at', 'latest_post_at',
        'avg_likes', 'avg_replies',
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
    list_display = ('keywords_short', 'status', 'result_count', 'scheduled_at', 'started_at', 'completed_at')
    list_filter = ('status',)
    readonly_fields = ('created_at',)

    @admin.display(description='キーワード')
    def keywords_short(self, obj):
        return obj.keywords[:50] + '...' if len(obj.keywords) > 50 else obj.keywords
