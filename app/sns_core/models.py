from django.db import models
from django.conf import settings

# Create your models here.
# sns_core/models.py

class InstagramAccount(models.Model):
    username = models.CharField(max_length=100, unique=True)
    user_id = models.CharField(max_length=100, unique=True)
    access_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 管理者 or 利用者との紐付けも後々追加可

class ThreadsAccount(models.Model):
    instagram_account = models.OneToOneField(InstagramAccount, on_delete=models.CASCADE)
    threads_user_id = models.CharField(max_length=100, unique=True)
    # 必要ならトークンや認証関連
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ThreadsPost(models.Model):
    threads_account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE)
    post_id = models.CharField(max_length=100, unique=True)
    text = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

class ThreadsFollowerHistory(models.Model):
    threads_account = models.ForeignKey(ThreadsAccount, on_delete=models.CASCADE)
    follower_count = models.IntegerField()
    date = models.DateField()  # 日時単位で集計

class InstagramDM(models.Model):
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE)
    dm_id = models.CharField(max_length=100, unique=True)
    sender_id = models.CharField(max_length=100)
    recipient_id = models.CharField(max_length=100)
    message = models.TextField()
    sent_at = models.DateTimeField()

class DMReplyTemplate(models.Model):
    keyword = models.CharField(max_length=100)
    reply_text = models.TextField()
    is_active = models.BooleanField(default=True)
    lag_seconds = models.IntegerField(default=0)

class ScheduledPost(models.Model):
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE)
    text = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    scheduled_at = models.DateTimeField()
    posted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class MetaUserToken(models.Model):
    """Metaのユーザアクセストークン（連携オーナー単位）"""
    user_id = models.CharField(max_length=64)  # graph user id
    access_token = models.TextField()          # 必要なら暗号化に差し替え可
    expires_at = models.DateTimeField(null=True, blank=True)
    granted_scopes = models.JSONField(default=list, blank=True)
    declined_scopes = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meta_user_tokens'
        verbose_name = 'Metaユーザトークン'
