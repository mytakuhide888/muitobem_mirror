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


# ─── バズ投稿リサーチ関連 ───

class THBuzzAuthor(models.Model):
    """Threads 投稿者プロフィール"""
    username = models.CharField('アカウント名', max_length=255, unique=True)
    display_name = models.CharField('表示名', max_length=255, blank=True, default='')
    bio = models.TextField('自己紹介', blank=True, default='')
    followers_count = models.IntegerField('フォロワー数', null=True, blank=True)
    following_count = models.IntegerField('フォロー数', null=True, blank=True)
    is_verified = models.BooleanField('認証バッジ', default=False)
    profile_url = models.URLField('プロフィールURL', blank=True, default='')
    raw_json = models.JSONField('取得時の生データ', default=dict, blank=True)
    first_scraped_at = models.DateTimeField('初回取得日時', auto_now_add=True)
    updated_at = models.DateTimeField('最終更新', auto_now=True)

    class Meta:
        db_table = 'meta_th_buzz_authors'
        verbose_name = 'Threadsバズ投稿者'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return f"@{self.username}" if self.username else self.display_name


class THBuzzPost(models.Model):
    """Threads バズ投稿"""
    author = models.ForeignKey(THBuzzAuthor, on_delete=models.CASCADE, related_name='buzz_posts', verbose_name='投稿者')
    post_url = models.URLField('投稿URL', blank=True, default='')
    text_content = models.TextField('投稿文面', blank=True, default='')
    like_count = models.IntegerField('いいね数', default=0)
    reply_count = models.IntegerField('リプライ数', default=0)
    repost_count = models.IntegerField('リポスト数', default=0)
    impressions = models.IntegerField('インプレッション数', null=True, blank=True)
    engagement_rate = models.FloatField('エンゲージメント率(%)', null=True, blank=True)
    engagement_score = models.FloatField('バズスコア', null=True, blank=True)
    is_viral = models.BooleanField('バズ判定', default=False)
    search_keyword = models.CharField('検索キーワード', max_length=255, blank=True, default='')
    posted_at = models.DateTimeField('投稿日時', null=True, blank=True)
    scraped_at = models.DateTimeField('取得日時', auto_now_add=True)
    raw_json = models.JSONField('取得時の生データ', default=dict, blank=True)

    class Meta:
        db_table = 'meta_th_buzz_posts'
        verbose_name = 'Threadsバズ投稿'
        verbose_name_plural = verbose_name
        ordering = ['-scraped_at']

    def __str__(self):
        return f"{self.author} - {self.text_content[:30]}"


class THBuzzSearchJob(models.Model):
    """バズ投稿検索ジョブ"""
    STATUS_CHOICES = [
        ('PENDING', '待機中'),
        ('RUNNING', '実行中'),
        ('COMPLETED', '完了'),
        ('FAILED', '失敗'),
    ]
    keywords = models.TextField('検索キーワード', help_text='JSON配列形式 例: ["AI", "副業"]')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    scheduled_at = models.DateTimeField('予約実行日時', null=True, blank=True)
    started_at = models.DateTimeField('開始日時', null=True, blank=True)
    completed_at = models.DateTimeField('完了日時', null=True, blank=True)
    result_count = models.IntegerField('取得件数', default=0)
    error_message = models.TextField('エラーメッセージ', blank=True, default='')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        db_table = 'meta_th_buzz_search_jobs'
        verbose_name = 'バズ検索ジョブ'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.keywords[:50]}"
