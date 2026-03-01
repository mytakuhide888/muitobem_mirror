from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Platform(models.TextChoices):
    THREADS = 'THREADS', 'Threads'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'


class FacebookAccount(models.Model):
    name = models.CharField('名前', max_length=255)
    facebook_user_id = models.CharField('FacebookユーザーID', max_length=100, unique=True)
    app_id = models.CharField('アプリID', max_length=100, null=True, blank=True)
    app_secret = models.TextField('アプリシークレット', blank=True, null=True)
    access_token = models.TextField('アクセストークン', blank=True, null=True)
    access_token_expires_at = models.DateTimeField('アクセストークン有効期限', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.name


class ThreadsApp(models.Model):
    name = models.CharField('名前', max_length=255)
    threads_app_id = models.CharField('ThreadsアプリID', max_length=100)
    threads_app_secret = models.TextField('Threadsアプリシークレット')
    callback_url = models.URLField('コールバックURL')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.name


class ThreadsAccount(models.Model):
    display_name = models.CharField('表示名', max_length=255)
    threads_user_id = models.CharField('ThreadsユーザーID', max_length=100, unique=True)
    username = models.CharField('ユーザー名', max_length=255)
    linked_facebook = models.ForeignKey(FacebookAccount, verbose_name='紐付けFacebook', on_delete=models.SET_NULL, null=True, blank=True)
    default_app = models.ForeignKey(ThreadsApp, verbose_name='デフォルトアプリ', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.display_name


class InstagramAccount(models.Model):
    display_name = models.CharField('表示名', max_length=255)
    instagram_user_id = models.CharField('InstagramユーザーID', max_length=100, unique=True)
    username = models.CharField('ユーザー名', max_length=255)
    linked_facebook = models.ForeignKey(FacebookAccount, verbose_name='紐付けFacebook', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.display_name


class ScheduledPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', '下書き'
        APPROVED = 'APPROVED', '承認済み'
        SENT = 'SENT', '送信済み'
        FAILED = 'FAILED', '失敗'

    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    account = GenericForeignKey('content_type', 'object_id')
    title = models.CharField('タイトル', max_length=255)
    topic = models.CharField('トピック', max_length=255)
    body = models.TextField('本文')
    scheduled_at = models.DateTimeField('投稿予定時刻')
    status = models.CharField('ステータス', max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='作成者', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.title


class Post(models.Model):
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    account = GenericForeignKey('content_type', 'object_id')
    external_post_id = models.CharField('外部投稿ID', max_length=100, unique=True)
    posted_at = models.DateTimeField('投稿時間')
    content = models.TextField('内容')
    like_count = models.IntegerField('いいね数', default=0)
    view_count = models.IntegerField('閲覧数', null=True, blank=True)
    raw_json = models.JSONField('取得JSON', default=dict)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return f"{self.platform}:{self.external_post_id}"


class DMMessage(models.Model):
    class Direction(models.TextChoices):
        IN = 'IN', 'In'
        OUT = 'OUT', 'Out'

    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    account = GenericForeignKey('content_type', 'object_id')
    user_id = models.CharField('ユーザーID', max_length=100)
    text = models.TextField('本文')
    direction = models.CharField('方向', max_length=3, choices=Direction.choices, default=Direction.IN)
    sent_at = models.DateTimeField('送受信時間')
    external_ids = models.JSONField('外部ID', default=dict, blank=True)
    raw_json = models.JSONField('受信JSON', default=dict)

    def __str__(self):
        return f"{self.user_id}"


class DMReplyTemplate(models.Model):
    name = models.CharField('名称', max_length=100)
    reply_text = models.TextField('返信本文')

    def __str__(self):
        return self.name


class AutoReplyRule(models.Model):
    name = models.CharField('名称', max_length=100)
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    account = GenericForeignKey('content_type', 'object_id')
    keywords = models.TextField('キーワード')
    delay_minutes = models.IntegerField('遅延分', default=0)
    reply_template = models.ForeignKey(DMReplyTemplate, verbose_name='返信テンプレート', on_delete=models.CASCADE)
    enabled = models.BooleanField('有効', default=True)

    def __str__(self):
        return self.name


class WebhookEvent(models.Model):
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    field = models.CharField('フィールド', max_length=100, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    account = GenericForeignKey('content_type', 'object_id')
    payload = models.JSONField('ペイロード', default=dict)
    signature_valid = models.BooleanField('署名検証', default=True)
    received_at = models.DateTimeField('受信時間', auto_now_add=True)

    def __str__(self):
        return f"{self.platform}:{self.field}"


class Job(models.Model):
    class Type(models.TextChoices):
        REPLY = 'REPLY', 'Reply'
        PUBLISH = 'PUBLISH', 'Publish'
        INSIGHT = 'INSIGHT', 'Insight'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RUNNING = 'RUNNING', 'Running'
        DONE = 'DONE', 'Done'
        FAILED = 'FAILED', 'Failed'

    job_type = models.CharField('ジョブ種別', max_length=20, choices=Type.choices)
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    account = GenericForeignKey('content_type', 'object_id')
    args = models.JSONField('引数', default=dict, blank=True)
    run_at = models.DateTimeField('実行予定時刻')
    status = models.CharField('ステータス', max_length=20, choices=Status.choices, default=Status.PENDING)
    retries = models.IntegerField('リトライ回数', default=0)
    last_error = models.TextField('最終エラー', blank=True, null=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    def __str__(self):
        return f"{self.job_type}:{self.platform}"


class DMContact(models.Model):
    ig_user_id = models.CharField(max_length=64, db_index=True)  # ページ側の IG User ID
    psid       = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    thread_key = models.CharField(max_length=128, null=True, blank=True)
    username   = models.CharField(max_length=255, null=True, blank=True)
    last_event_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("ig_user_id", "psid"),)


# ── AI鑑定文生成システム v2 ──

class AppraisalCharacter(models.Model):
    """占い師キャラクター"""
    name = models.CharField('キャラクター名', max_length=100)
    concept = models.TextField('世界観・設定', blank=True)
    writing_style = models.TextField('口調・文体', blank=True)
    target_audience = models.TextField('ターゲット層', blank=True)
    divination_methods = models.JSONField('使用占術リスト', default=list, blank=True)
    background_story = models.TextField('経歴設定', blank=True)
    ig_account = models.ForeignKey(
        'ig.InstagramBusinessAccount', verbose_name='IGアカウント',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='appraisal_characters',
    )
    th_account = models.ForeignKey(
        ThreadsAccount, verbose_name='THアカウント',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='appraisal_characters',
    )
    concept_document_md = models.TextField('コンセプト設計書（MD形式）', blank=True, default='')
    profile_bio = models.TextField('プロフィールbio', blank=True, default='')
    pinned_post_samples = models.JSONField('固定投稿サンプル', default=list, blank=True)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '鑑定キャラクター'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class AppraisalTemplate(models.Model):
    """鑑定テンプレート"""
    class Category(models.TextChoices):
        FREE = 'FREE', '無料鑑定'
        PAID_LOW = 'PAID_LOW', '有料（低額）'
        PAID_MID = 'PAID_MID', '有料（中額）'
        PAID_HIGH = 'PAID_HIGH', '有料（高額）'
        FOLLOWUP = 'FOLLOWUP', 'フォローアップ'

    character = models.ForeignKey(
        AppraisalCharacter, verbose_name='キャラクター',
        on_delete=models.CASCADE, related_name='templates',
    )
    name = models.CharField('テンプレート名', max_length=100)
    category = models.CharField('カテゴリ', max_length=20, choices=Category.choices, default=Category.FREE)
    system_prompt = models.TextField('システムプロンプト（MD形式）', blank=True)
    user_prompt_template = models.TextField('ユーザープロンプトテンプレート', blank=True)
    word_count_min = models.IntegerField('最小文字数', default=600)
    word_count_max = models.IntegerField('最大文字数', default=1000)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '鑑定テンプレート'
        verbose_name_plural = verbose_name
        ordering = ['character', 'sort_order', 'name']

    def __str__(self):
        return f'{self.character.name} / {self.name}'


class AppraisalCustomer(models.Model):
    """鑑定顧客"""
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    platform_user_id = models.CharField('プラットフォームユーザーID', max_length=100)
    username = models.CharField('ユーザー名', max_length=255, blank=True)
    display_name = models.CharField('表示名', max_length=255, blank=True)
    birthdate = models.CharField('生年月日', max_length=20, blank=True)
    profile_summary = models.TextField('プロフィール要約', blank=True)
    personality_analysis = models.TextField('AI性格分析', blank=True)
    posts_fetched_at = models.DateTimeField('投稿取得日時', null=True, blank=True)
    memo = models.TextField('メモ', blank=True)

    class Meta:
        verbose_name = '鑑定顧客'
        verbose_name_plural = verbose_name
        unique_together = (('platform', 'platform_user_id'),)

    def __str__(self):
        return f'{self.username or self.platform_user_id} ({self.platform})'


class AppraisalCustomerPost(models.Model):
    """顧客投稿キャッシュ"""
    customer = models.ForeignKey(
        AppraisalCustomer, verbose_name='顧客',
        on_delete=models.CASCADE, related_name='posts',
    )
    post_url = models.URLField('投稿URL', max_length=500, blank=True)
    text_content = models.TextField('投稿内容', blank=True)
    posted_at = models.DateTimeField('投稿日時', null=True, blank=True)
    like_count = models.IntegerField('いいね数', default=0)
    reply_count = models.IntegerField('リプライ数', default=0)
    raw_json = models.JSONField('生データ', default=dict, blank=True)

    class Meta:
        verbose_name = '顧客投稿キャッシュ'
        verbose_name_plural = verbose_name
        ordering = ['-posted_at']

    def __str__(self):
        return f'{self.customer} - {self.posted_at}'


class AppraisalHistory(models.Model):
    """鑑定履歴"""
    character = models.ForeignKey(
        AppraisalCharacter, verbose_name='キャラクター',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='histories',
    )
    template = models.ForeignKey(
        AppraisalTemplate, verbose_name='テンプレート',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='histories',
    )
    customer = models.ForeignKey(
        AppraisalCustomer, verbose_name='顧客',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='histories',
    )
    birthdate = models.CharField('生年月日', max_length=20, blank=True)
    concern = models.TextField('相談内容', blank=True)
    divination = models.CharField('占術', max_length=50, blank=True)
    generated_text = models.TextField('生成テキスト', blank=True)
    sent_text = models.TextField('送信テキスト', blank=True)
    system_prompt_used = models.TextField('使用システムプロンプト', blank=True)
    user_prompt_used = models.TextField('使用ユーザープロンプト', blank=True)
    dm_sent = models.BooleanField('DM送信済み', default=False)
    dm_sent_at = models.DateTimeField('DM送信日時', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        verbose_name = '鑑定履歴'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'鑑定 #{self.pk} ({self.created_at:%Y-%m-%d %H:%M})'