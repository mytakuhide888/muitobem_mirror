from django.db import models
from social_core.models import (
    BaseSocialAccount, BasePost, BaseScheduledPost,
    BaseBroadcast, BaseDMThread, BaseDMMessage,
    BaseAutoReplyTemplate, BaseAutoReplyRule, BaseWebhookEvent,
)


class ThreadsAccount(BaseSocialAccount):
    threads_user_id = models.CharField('ThreadsユーザーID', max_length=100)
    access_token = models.TextField('アクセストークン', blank=True, default='')
    webhook_verify_token = models.CharField('Webhook検証トークン', max_length=100, blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    permissions = models.JSONField(default=dict, blank=True)  # {"granted":[...], "declined":[...]}
    webhook_subscribed = models.BooleanField(default=False)
    webhook_subscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'meta_th_accounts'
        verbose_name = 'Threadsアカウント'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.display_name


class THPost(BasePost):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE, related_name='posts')

    class Meta:
        db_table = 'meta_th_posts'
        verbose_name = 'Threads投稿'
        verbose_name_plural = verbose_name


class THScheduledPost(BaseScheduledPost):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE, related_name='scheduled_posts')

    class Meta:
        db_table = 'meta_th_scheduled_posts'
        verbose_name = 'Threads予約投稿'
        verbose_name_plural = verbose_name


class THBroadcast(BaseBroadcast):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE, related_name='broadcasts', null=True, blank=True)

    class Meta:
        db_table = 'meta_th_broadcasts'
        verbose_name = 'Threads時間指定配信'
        verbose_name_plural = verbose_name


class THDMThread(BaseDMThread):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE, related_name='dm_threads')

    class Meta:
        db_table = 'meta_th_dm_threads'
        verbose_name = 'ThreadsDMスレッド'
        verbose_name_plural = verbose_name


class THDMMessage(BaseDMMessage):
    thread = models.ForeignKey(THDMThread, on_delete=models.CASCADE, related_name='messages')

    class Meta:
        db_table = 'meta_th_dm_messages'
        verbose_name = 'ThreadsDMメッセージ'
        verbose_name_plural = verbose_name


class THAutoReplyTemplate(BaseAutoReplyTemplate):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE, related_name='auto_reply_templates')

    class Meta:
        db_table = 'meta_th_auto_reply_templates'
        verbose_name = 'Threads自動返信テンプレート'
        verbose_name_plural = verbose_name


class THAutoReplyRule(BaseAutoReplyRule):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE, related_name='auto_reply_rules')
    template = models.ForeignKey(THAutoReplyTemplate, on_delete=models.CASCADE, related_name='rules')

    class Meta:
        db_table = 'meta_th_auto_reply_rules'
        verbose_name = 'Threads自動返信ルール'
        verbose_name_plural = verbose_name


class THWebhookEvent(BaseWebhookEvent):
    account = models.ForeignKey(ThreadsAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_events')

    class Meta:
        db_table = 'meta_th_webhook_events'
        verbose_name = 'ThreadsWebhookイベント'
        verbose_name_plural = verbose_name
