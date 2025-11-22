from django.contrib import admin
from social_core.admin_mixins import TimeStampedAdminMixin
from .models import (
    ThreadsAccount, THPost, THScheduledPost,
    THBroadcast, THDMThread, THDMMessage,
    THAutoReplyTemplate, THAutoReplyRule, THWebhookEvent,
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
