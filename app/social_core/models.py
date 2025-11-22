from django.db import models
from django.conf import settings


class BaseSocialAccount(models.Model):
    """共通SNSアカウント"""
    display_name = models.CharField('表示名', max_length=255)
    username = models.CharField('ユーザー名', max_length=255)
    external_id = models.CharField('外部ID', max_length=100, unique=True)
    access_token = models.TextField('アクセストークン', blank=True, null=True)
    token_expires_at = models.DateTimeField('トークン期限', null=True, blank=True)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True


class BasePost(models.Model):
    """投稿共通"""
    account = models.ForeignKey('self', on_delete=models.CASCADE)
    external_post_id = models.CharField('外部投稿ID', max_length=100, unique=True)
    posted_at = models.DateTimeField('投稿時間')
    caption = models.TextField('本文', blank=True, null=True)
    media_type = models.CharField('メディアタイプ', max_length=50, blank=True)
    media_url = models.URLField('メディアURL', blank=True, null=True)
    like_count = models.IntegerField('いいね数', default=0)
    view_count = models.IntegerField('閲覧数', null=True, blank=True)
    impressions = models.IntegerField('インプレッション', null=True, blank=True)
    raw_json = models.JSONField('取得JSON', default=dict)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-posted_at']


class BaseScheduledPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', '下書き'
        APPROVED = 'APPROVED', '承認済み'
        SENT = 'SENT', '送信済み'
        FAILED = 'FAILED', '失敗'

    account = models.ForeignKey('self', on_delete=models.CASCADE)
    title = models.CharField('タイトル', max_length=255)
    topic = models.CharField('トピック', max_length=255)
    body = models.TextField('本文')
    media_url = models.URLField('メディアURL', blank=True, null=True)
    scheduled_at = models.DateTimeField('予約日時')
    status = models.CharField('ステータス', max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='作成者', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-scheduled_at']


class BaseBroadcast(models.Model):
    account = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField('名称', max_length=255)
    segment = models.JSONField('セグメント', default=dict, blank=True)
    body = models.TextField('本文')
    send_at = models.DateTimeField('送信日時')
    status = models.CharField('ステータス', max_length=20, default='DRAFT')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        abstract = True


class BaseDMThread(models.Model):
    account = models.ForeignKey('self', on_delete=models.CASCADE)
    external_thread_id = models.CharField('スレッドID', max_length=100)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        abstract = True


class BaseDMMessage(models.Model):
    class Direction(models.TextChoices):
        IN = 'IN', '受信'
        OUT = 'OUT', '送信'

    thread = models.ForeignKey('self', on_delete=models.CASCADE)
    direction = models.CharField('方向', max_length=3, choices=Direction.choices)
    text = models.TextField('本文')
    sent_at = models.DateTimeField('送信時間')
    raw_json = models.JSONField('RAW', default=dict, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True
        ordering = ['sent_at']


class BaseAutoReplyTemplate(models.Model):
    name = models.CharField('名称', max_length=100)
    body = models.TextField('本文')

    class Meta:
        abstract = True


class BaseAutoReplyRule(models.Model):
    account = models.ForeignKey('self', on_delete=models.CASCADE)
    name = models.CharField('名称', max_length=100)
    keywords = models.TextField('キーワード')
    delay_minutes = models.IntegerField('遅延分', default=0)
    enabled = models.BooleanField('有効', default=True)
    template = models.ForeignKey('self', on_delete=models.CASCADE)

    class Meta:
        abstract = True


class BaseWebhookEvent(models.Model):
    account = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField('イベント種別', max_length=100)
    received_at = models.DateTimeField('受信日時', auto_now_add=True)
    payload = models.JSONField('ペイロード', default=dict)
    processed = models.BooleanField('処理済', default=False)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-received_at']
