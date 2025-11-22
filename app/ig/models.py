from django.db import models
from django.conf import settings
from social_core.models import (
    BaseSocialAccount, BasePost, BaseScheduledPost,
    BaseBroadcast, BaseDMThread, BaseDMMessage,
    BaseAutoReplyTemplate, BaseAutoReplyRule, BaseWebhookEvent,
)


class InstagramBusinessAccount(BaseSocialAccount):
    ig_business_id = models.CharField('IGビジネスID', max_length=32, unique=True, db_index=True)
    fb_page_id = models.CharField('FacebookページID', max_length=32, blank=True, null=True, db_index=True)
    webhook_verify_token = models.CharField('Webhook検証トークン', max_length=128, blank=True, default='')
    permissions = models.JSONField(default=dict, blank=True)  # {"granted":[...], "declined":[...]}
    webhook_subscribed = models.BooleanField(default=False)
    webhook_subscribed_at = models.DateTimeField(null=True, blank=True)

    # 自動更新の起点になる 60日ユーザートークン（人間の長期トークン）
    long_lived_user_token = models.TextField(
        blank=True, null=True,
        verbose_name="長期ユーザートークン（User）",
        help_text="Graph API Explorerで生成→60日に延長したユーザートークン。自動更新の起点になります。",
    )
    # 自動更新で作られるページトークン（送信用）。空でも運用可（毎回その場で生成されるため）
    page_access_token = models.TextField(
        blank=True, null=True,
        verbose_name="ページアクセストークン（自動更新で上書き）",
        help_text="ensure_fresh_page_token により上書きされます。空でも可。",
    )
    # ページトークンの失効日時（任意。表示・確認用）
    token_expires_at = models.DateTimeField(
        blank=True, null=True,
        verbose_name="ページトークン期限",
        help_text="表示用。自動更新の必須ではありません。",
    )

    # 補助: 返信時に使う“最良のトークン”を返す（ページが優先、無ければ BaseSocialAccount.access_token）
    @property
    def best_send_token(self) -> str | None:
        return self.page_access_token or getattr(self, "access_token", None)

    # 補助: IGビジネスID → FBページIDの候補を返す（未設定時の保険）
    def candidate_page_id(self) -> str | None:
        return self.fb_page_id or None
    
    class Meta:
        db_table = 'meta_ig_accounts'
        verbose_name = 'Instagramビジネスアカウント'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['ig_business_id']),
            models.Index(fields=['fb_page_id']),
        ]

    def save(self, *args, **kwargs):
        # external_id は常時 ig_business_id に揃える（ユニークキーの一元化）
        if self.ig_business_id and self.external_id != self.ig_business_id:
            self.external_id = self.ig_business_id
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.username

class IGPost(BasePost):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='posts')

    class Meta:
        db_table = 'meta_ig_posts'
        verbose_name = 'Instagram投稿'
        verbose_name_plural = verbose_name


class IGScheduledPost(BaseScheduledPost):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='scheduled_posts')

    class Meta:
        db_table = 'meta_ig_scheduled_posts'
        verbose_name = 'Instagram予約投稿'
        verbose_name_plural = verbose_name


class IGBroadcast(BaseBroadcast):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='broadcasts', null=True, blank=True)

    class Meta:
        db_table = 'meta_ig_broadcasts'
        verbose_name = 'Instagram時間指定配信'
        verbose_name_plural = verbose_name


class IGDMThread(BaseDMThread):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='dm_threads')

    class Meta:
        db_table = 'meta_ig_dm_threads'
        verbose_name = 'InstagramDMスレッド'
        verbose_name_plural = verbose_name


class IGDMMessage(BaseDMMessage):
    thread = models.ForeignKey(IGDMThread, on_delete=models.CASCADE, related_name='messages')

    class Meta:
        db_table = 'meta_ig_dm_messages'
        verbose_name = 'InstagramDMメッセージ'
        verbose_name_plural = verbose_name


class IGAutoReplyTemplate(BaseAutoReplyTemplate):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='auto_reply_templates')

    class Meta:
        db_table = 'meta_ig_auto_reply_templates'
        verbose_name = 'Instagram自動返信テンプレート'
        verbose_name_plural = verbose_name


class IGAutoReplyRule(BaseAutoReplyRule):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='auto_reply_rules')
    template = models.ForeignKey(IGAutoReplyTemplate, on_delete=models.CASCADE, related_name='rules')

    class Meta:
        db_table = 'meta_ig_auto_reply_rules'
        verbose_name = 'Instagram自動返信ルール'
        verbose_name_plural = verbose_name


class IGWebhookEvent(BaseWebhookEvent):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_events')

    class Meta:
        db_table = 'meta_ig_webhook_events'
        verbose_name = 'InstagramWebhookイベント'
        verbose_name_plural = verbose_name

class IGDMReplyLog(models.Model):
    dm = models.ForeignKey('social.DMMessage', on_delete=models.CASCADE, related_name='ig_reply_logs')
    recipient_id = models.CharField(max_length=64)
    biz_ig_id = models.CharField(max_length=64, blank=True, default="")
    text = models.TextField()
    ok = models.BooleanField(default=False)
    http_status = models.IntegerField(null=True, blank=True)
    response = models.JSONField(default=dict, blank=True)  # Graphの成功/失敗レスポンスをそのまま
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['dm', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'IGDMReplyLog(dm={self.dm_id}, ok={self.ok}, status={self.http_status})'
    