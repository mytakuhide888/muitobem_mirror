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
    profile_pic_url = models.URLField('プロフィール画像URL', max_length=500, blank=True, default='')
    raw_json = models.JSONField('取得時の生データ', default=dict, blank=True)
    first_scraped_at = models.DateTimeField('初回取得日時', auto_now_add=True)
    updated_at = models.DateTimeField('最終更新', auto_now=True)

    # ─── 成長指標フィールド ───
    total_post_count = models.IntegerField('総投稿数', null=True, blank=True)
    earliest_post_at = models.DateTimeField('最古の投稿日時', null=True, blank=True)
    latest_post_at = models.DateTimeField('最新の投稿日時', null=True, blank=True)
    avg_likes = models.FloatField('平均いいね数', null=True, blank=True)
    avg_replies = models.FloatField('平均リプライ数', null=True, blank=True)
    growth_score = models.FloatField('急成長スコア', null=True, blank=True)
    account_age_days = models.IntegerField('推定アカウント日数', null=True, blank=True)
    followers_per_day = models.FloatField('1日あたりフォロワー増', null=True, blank=True)
    category_tags = models.CharField('カテゴリタグ', max_length=500, blank=True, default='')
    memo = models.TextField('メモ', blank=True, default='')
    is_favorited = models.BooleanField('お気に入り', default=False)
    is_concept_candidate = models.BooleanField('コンセプト候補', default=False)
    is_excluded = models.BooleanField('対象外', default=False)

    # ─── 品質指標フィールド ───
    quality_score = models.FloatField('品質スコア', null=True, blank=True)
    is_quality_account = models.BooleanField('優良アカウント', default=False)
    good_post_ratio = models.FloatField('良い投稿の割合', null=True, blank=True)
    recent_post_count = models.IntegerField('直近30日の投稿数', null=True, blank=True)
    avg_post_interval_days = models.FloatField('平均投稿間隔(日)', null=True, blank=True)

    # ─── 占いリサーチ適合指標 ───
    fortune_relevance_score = models.FloatField('占い適合スコア', null=True, blank=True,
        help_text='ジャンル適合度 + マネタイズ度の加重スコア (0-100)')
    genre_tags = models.JSONField('ジャンルタグ', default=list, blank=True,
        help_text='自動検出: ["占い","タロット","スピリチュアル"...]')
    monetization_signals = models.JSONField('マネタイズシグナル', default=list, blank=True,
        help_text='検出: ["STORES","LINE","有料鑑定"...]')
    auto_excluded_reason = models.CharField('自動対象外理由', max_length=200, blank=True, default='')

    # ─── 自動巡回パイプライン ───
    is_attention_needed = models.BooleanField('要注目', default=False,
        help_text='自動巡回で成長スコア閾値超え + 占い適合のアカウント')
    attention_set_at = models.DateTimeField('要注目フラグ設定日時', null=True, blank=True)
    is_analyzed = models.BooleanField('分析済み', default=False,
        help_text='構造化分析メモが記入済み')
    deep_scan_fail_count = models.IntegerField('深堀スキャン連続失敗回数', default=0)
    deep_scan_last_error = models.TextField('深堀スキャン最終エラー', blank=True, default='')
    deep_scan_last_attempt_at = models.DateTimeField('深堀スキャン最終試行日時', null=True, blank=True)

    class Meta:
        db_table = 'meta_th_buzz_authors'
        verbose_name = 'Threadsバズ投稿者'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at'], name='bza_updated_at_desc'),
            models.Index(fields=['is_excluded'], name='bza_is_excluded'),
            models.Index(fields=['is_favorited'], name='bza_is_favorited'),
            models.Index(fields=['-growth_score'], name='bza_growth_score_desc'),
            models.Index(fields=['-quality_score'], name='bza_quality_score_desc'),
            models.Index(fields=['followers_count'], name='bza_followers_count'),
            models.Index(fields=['account_age_days'], name='bza_account_age_days'),
            models.Index(fields=['-fortune_relevance_score'], name='bza_fortune_score_desc'),
            models.Index(fields=['is_attention_needed'], name='bza_attention_needed'),
            models.Index(fields=['deep_scan_fail_count'], name='bza_deep_scan_fail_count'),
        ]

    def __str__(self):
        return f"@{self.username}" if self.username else self.display_name

    def _parse_joined_at(self):
        """raw_json.joined_at（例: '2025年2月', 'February 2025'）から datetime を返す"""
        from datetime import datetime, timezone as dt_timezone
        joined_str = (self.raw_json or {}).get('joined_at', '')
        if not joined_str:
            return None
        import re
        # 日本語: "2025年2月"
        m = re.match(r'(\d{4})年(\d{1,2})月', joined_str)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=dt_timezone.utc)
            except (ValueError, OverflowError):
                return None
        # 英語: "February 2025"
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
        }
        m = re.match(r'(\w+)\s+(\d{4})', joined_str)
        if m:
            month_num = months.get(m.group(1).lower())
            if month_num:
                try:
                    return datetime(int(m.group(2)), month_num, 1, tzinfo=dt_timezone.utc)
                except (ValueError, OverflowError):
                    return None
        return None

    def update_growth_stats(self):
        """DB 上の投稿データから成長指標を再計算して保存する"""
        from django.db.models import Avg, Count, Min, Max
        from django.utils import timezone as tz

        stats = self.buzz_posts.aggregate(
            count=Count('id'),
            avg_likes=Avg('like_count'),
            avg_replies=Avg('reply_count'),
            earliest=Min('posted_at'),
            latest=Max('posted_at'),
        )

        self.total_post_count = stats['count']
        self.avg_likes = round(stats['avg_likes'], 1) if stats['avg_likes'] else None
        self.avg_replies = round(stats['avg_replies'], 1) if stats['avg_replies'] else None
        self.earliest_post_at = stats['earliest']
        self.latest_post_at = stats['latest']

        # アカウント日数: joined_at（参加日）を優先、なければ最古投稿日から算出
        joined_dt = self._parse_joined_at()
        if joined_dt:
            delta = tz.now() - joined_dt
            self.account_age_days = max(delta.days, 1)
        elif self.earliest_post_at:
            delta = tz.now() - self.earliest_post_at
            self.account_age_days = max(delta.days, 1)
        else:
            self.account_age_days = None

        # 1日あたりフォロワー増加
        if self.account_age_days and self.followers_count:
            self.followers_per_day = round(
                self.followers_count / self.account_age_days, 1
            )
        else:
            self.followers_per_day = None

        # 急成長スコア = フォロワー密度 × エンゲージメント品質 × 信頼度
        self.growth_score = self._calc_growth_score()

        # コンセプト候補の自動判定
        self.is_concept_candidate = self._evaluate_concept_candidate()

        # 品質スコアの計算
        self._update_quality_stats()

        # ─── 占い属性分類 ───
        try:
            from th.services.fortune_classifier import update_author_fortune_classification
            update_author_fortune_classification(self)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'Fortune classification failed for @%s: %s', self.username, e
            )

        self.save(update_fields=[
            'total_post_count', 'earliest_post_at', 'latest_post_at',
            'avg_likes', 'avg_replies', 'account_age_days',
            'followers_per_day', 'growth_score', 'is_concept_candidate',
            'quality_score', 'is_quality_account', 'good_post_ratio',
            'recent_post_count', 'avg_post_interval_days',
            'fortune_relevance_score', 'genre_tags', 'monetization_signals',
            'auto_excluded_reason',
        ])

    def _calc_growth_score(self):
        """
        急成長スコア算出:
          フォロワー密度 (followers / days)
          × エンゲージメント品質 ((avg_likes + avg_replies*2) / followers %)
          × 信頼度 (min(post_count / 5, 1.0))
        高スコア = 短期間でフォロワーが多く、エンゲージメントが高く、
                  十分な投稿データで裏付けられたアカウント
        """
        if not self.account_age_days or self.account_age_days < 1:
            return None
        if not self.followers_count or self.followers_count < 10:
            return None

        follower_density = self.followers_count / self.account_age_days

        # エンゲージメント品質: いいね + リプライ×2 をフォロワー比で評価
        avg_likes = self.avg_likes or 0
        avg_replies = self.avg_replies or 0
        eng_quality = 1.0
        if self.followers_count > 0:
            eng_quality = ((avg_likes + avg_replies * 2) / self.followers_count) * 100
            eng_quality = min(eng_quality, 50.0)

        # 信頼度係数: 投稿5件未満はスコアを割引
        post_count = self.total_post_count or 0
        confidence = min(post_count / 5, 1.0)
        if confidence < 0.2:
            confidence = 0.2  # 最低20%は付与（0投稿でなければ）
        if post_count == 0:
            confidence = 0

        return round(follower_density * eng_quality * confidence, 2)

    def _evaluate_concept_candidate(self):
        """
        コンセプト設計の参考になるアカウントかどうかを自動判定する。
        条件:
          - アカウント日数 7〜90日
          - フォロワー 500人以上
          - 1日あたりフォロワー増 10人以上
          - 成長スコアが算出済み（None でない）
        """
        age = self.account_age_days
        if not age or age < 7 or age > 90:
            return False
        if not self.followers_count or self.followers_count < 500:
            return False
        if not self.followers_per_day or self.followers_per_day < 10:
            return False
        if self.growth_score is None:
            return False
        return True

    # ─── 品質スコア関連メソッド ───

    def _update_quality_stats(self):
        """品質スコアを一括計算してフィールドにセットする（save は呼ばない）"""
        from django.utils import timezone as tz

        posts = list(self.buzz_posts.all())
        total = len(posts)

        if total == 0:
            self.quality_score = None
            self.is_quality_account = False
            self.good_post_ratio = None
            self.recent_post_count = None
            self.avg_post_interval_days = None
            return

        # 各サブスコア算出
        eng_quality = self._calc_engagement_quality(posts, total)
        recency = self._calc_recency_score(posts, tz.now())
        frequency = self._calc_frequency_score(posts, total)
        confidence = self._calc_confidence_score(total)

        self.quality_score = round(
            eng_quality * 0.40
            + recency * 0.25
            + frequency * 0.20
            + confidence * 0.15,
            1,
        )
        self.is_quality_account = (
            self.quality_score is not None and self.quality_score >= 50
        )

    def _calc_engagement_quality(self, posts, total):
        """エンゲージメント品質スコア（0〜100）"""
        followers = self.followers_count or 0

        def is_good_post(p):
            score = (p.like_count or 0) * 1.0 + (p.reply_count or 0) * 3.0 + (p.repost_count or 0) * 2.5
            er = ((p.like_count or 0) + (p.reply_count or 0) + (p.repost_count or 0)) / followers * 100 if followers > 0 else 0
            if followers <= 10000:
                return score >= 100 or er >= 2.0
            elif followers <= 100000:
                return score >= 500 or er >= 1.0
            elif followers > 100000:
                return score >= 2000 or er >= 0.5
            else:
                return score >= 200
        # フォロワー不明時
        if followers == 0:
            good_count = sum(
                1 for p in posts
                if ((p.like_count or 0) * 1.0 + (p.reply_count or 0) * 3.0 + (p.repost_count or 0) * 2.5) >= 200
            )
        else:
            good_count = sum(1 for p in posts if is_good_post(p))

        good_ratio = good_count / total if total > 0 else 0.0
        self.good_post_ratio = round(good_ratio, 3)

        if good_ratio >= 0.5:
            return 80 + (good_ratio - 0.5) * 40
        else:
            return good_ratio * 160

    def _calc_recency_score(self, posts, now):
        """直近活動度スコア（0〜100）"""
        from datetime import timedelta

        # 最新投稿からの経過日数 → freshness
        dated_posts = [p for p in posts if p.posted_at]
        if not dated_posts:
            self.recent_post_count = 0
            return 10

        latest = max(p.posted_at for p in dated_posts)
        days_since = (now - latest).days

        if days_since <= 3:
            freshness = 100
        elif days_since <= 7:
            freshness = 90
        elif days_since <= 14:
            freshness = 70
        elif days_since <= 30:
            freshness = 50
        elif days_since <= 60:
            freshness = 25
        else:
            freshness = 10

        # 直近30日の投稿数 → volume
        cutoff = now - timedelta(days=30)
        recent_count = sum(1 for p in dated_posts if p.posted_at >= cutoff)
        self.recent_post_count = recent_count

        if recent_count >= 10:
            volume = 100
        elif recent_count >= 5:
            volume = 80
        elif recent_count >= 3:
            volume = 60
        elif recent_count >= 1:
            volume = 40
        else:
            volume = 0

        return freshness * 0.6 + volume * 0.4

    def _calc_frequency_score(self, posts, total):
        """投稿頻度スコア（0〜100）"""
        if total < 2:
            self.avg_post_interval_days = None
            return 10

        dated_posts = [p for p in posts if p.posted_at]
        if len(dated_posts) < 2:
            self.avg_post_interval_days = None
            return 10

        sorted_dates = sorted(p.posted_at for p in dated_posts)
        span_days = (sorted_dates[-1] - sorted_dates[0]).days
        avg_interval = span_days / (len(sorted_dates) - 1) if len(sorted_dates) > 1 else 0
        self.avg_post_interval_days = round(avg_interval, 1)

        if avg_interval <= 1:
            return 100
        elif avg_interval <= 2:
            return 90
        elif avg_interval <= 3:
            return 80
        elif avg_interval <= 5:
            return 60
        elif avg_interval <= 7:
            return 45
        elif avg_interval <= 14:
            return 25
        else:
            return 10

    def _calc_confidence_score(self, total):
        """信頼度スコア（0〜100）"""
        if total >= 10:
            return 100
        elif total >= 7:
            return 85
        elif total >= 5:
            return 70
        elif total >= 3:
            return 50
        elif total >= 1:
            return 30
        else:
            return 0


class THBuzzAuthorAnalysis(models.Model):
    """投稿者の構造化分析メモ（メイト氏Step2: 伸びている要因のピックアップ）"""
    author = models.OneToOneField(
        THBuzzAuthor, on_delete=models.CASCADE,
        related_name='analysis', verbose_name='投稿者',
    )
    # ─── 伸びている要因チェックリスト ───
    factor_profile = models.TextField('プロフィール/表示名の工夫', blank=True, default='')
    factor_concept = models.TextField('コンセプト（何者か、ギャップ）', blank=True, default='')
    factor_content = models.TextField('投稿内容の傾向', blank=True, default='')
    factor_format = models.TextField('投稿形式の使い分け', blank=True, default='')
    factor_frequency = models.TextField('投稿頻度・タイミング', blank=True, default='')
    factor_engagement = models.TextField('エンゲージメントの取り方', blank=True, default='')
    factor_funnel = models.TextField('導線設計（bio→LINE→鑑定等）', blank=True, default='')
    factor_other = models.TextField('その他の要因', blank=True, default='')
    # ─── メタ情報 ───
    overall_assessment = models.TextField('総合評価', blank=True, default='')
    concept_inspiration = models.TextField('この垢から得たコンセプトのヒント', blank=True, default='')
    differentiation_idea = models.TextField('ずらしのアイデア', blank=True, default='')
    analyzed_at = models.DateTimeField('分析日時', auto_now=True)

    class Meta:
        db_table = 'meta_th_buzz_author_analysis'
        verbose_name = '投稿者分析メモ'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"分析: @{self.author.username}"

    def has_content(self):
        """いずれかのフィールドに記入があるか"""
        fields = [
            self.factor_profile, self.factor_concept, self.factor_content,
            self.factor_format, self.factor_frequency, self.factor_engagement,
            self.factor_funnel, self.factor_other,
            self.overall_assessment, self.concept_inspiration, self.differentiation_idea,
        ]
        return any(f.strip() for f in fields)


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
    media_type = models.CharField(
        'メディア種別', max_length=20, blank=True, default='',
        help_text='text/image/video/carousel',
    )
    media_urls = models.JSONField(
        'メディアURL一覧', default=list, blank=True,
        help_text='画像/動画URLの配列 [{\"type\":\"image\",\"url\":\"...\",\"width\":0,\"height\":0}, ...]',
    )

    class Meta:
        db_table = 'meta_th_buzz_posts'
        verbose_name = 'Threadsバズ投稿'
        verbose_name_plural = verbose_name
        ordering = ['-scraped_at']
        indexes = [
            models.Index(fields=['-scraped_at'], name='bzp_scraped_at_desc'),
            models.Index(fields=['author', '-scraped_at'], name='bzp_author_scraped'),
            models.Index(fields=['-posted_at'], name='bzp_posted_at_desc'),
            models.Index(fields=['search_keyword'], name='bzp_search_keyword'),
            models.Index(fields=['is_viral'], name='bzp_is_viral'),
            models.Index(fields=['-like_count'], name='bzp_like_count_desc'),
            models.Index(fields=['-engagement_score'], name='bzp_eng_score_desc'),
            models.Index(fields=['-engagement_rate'], name='bzp_eng_rate_desc'),
        ]

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
    JOB_TYPE_CHOICES = [
        ('keyword', 'キーワード検索'),
        ('account', 'アカウント取得'),
    ]
    job_type = models.CharField(
        'ジョブ種別', max_length=20,
        choices=JOB_TYPE_CHOICES, default='keyword',
    )
    keywords = models.TextField('検索キーワード', help_text='JSON配列形式 例: ["AI", "副業"]')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    scheduled_at = models.DateTimeField('予約実行日時', null=True, blank=True)
    started_at = models.DateTimeField('開始日時', null=True, blank=True)
    completed_at = models.DateTimeField('完了日時', null=True, blank=True)
    result_count = models.IntegerField('取得件数', default=0)
    error_message = models.TextField('エラーメッセージ', blank=True, default='')
    error_traceback = models.TextField('エラートレースバック', blank=True, default='')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        db_table = 'meta_th_buzz_search_jobs'
        verbose_name = 'バズ検索ジョブ'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.keywords[:50]}"


# ─── コンセプト設計関連 ───

class ConceptProject(models.Model):
    """コンセプト設計プロジェクト"""
    STATUS_CHOICES = [
        ('DRAFT', '下書き'),
        ('ANALYZING', '分析中'),
        ('CONCEPTS_GENERATED', 'コンセプト案生成済み'),
        ('DETAILING', '詳細化中'),
        ('COMPLETED', '完了'),
    ]
    title = models.CharField('プロジェクト名', max_length=200, blank=True, default='')
    status = models.CharField('ステータス', max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    analysis_result = models.JSONField('AI分析結果（統合）', default=dict, blank=True)
    analysis_summary = models.TextField('分析まとめ', blank=True, default='')
    concept_proposals = models.JSONField('ずらしコンセプト案', default=list, blank=True)
    selected_proposal_index = models.IntegerField('選択した案番号', null=True, blank=True)
    detailed_concept_md = models.TextField('詳細化結果（MD形式）', blank=True, default='')
    user_feedback = models.TextField('ユーザー要望メモ', blank=True, default='')
    character = models.ForeignKey(
        'social.AppraisalCharacter', verbose_name='生成キャラクター',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='concept_projects',
    )
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        db_table = 'meta_th_concept_projects'
        verbose_name = 'コンセプト設計プロジェクト'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f"コンセプト #{self.pk}"


class ConceptProjectAuthor(models.Model):
    """コンセプト設計 — 参考アカウント中間テーブル"""
    project = models.ForeignKey(
        ConceptProject, on_delete=models.CASCADE,
        related_name='project_authors', verbose_name='プロジェクト',
    )
    author = models.ForeignKey(
        THBuzzAuthor, on_delete=models.CASCADE,
        related_name='concept_usages', verbose_name='参考アカウント',
    )
    ai_analysis = models.JSONField('AI分析結果', default=dict, blank=True)
    ai_summary = models.TextField('特徴まとめ', blank=True, default='')
    order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'meta_th_concept_project_authors'
        verbose_name = 'コンセプト参考アカウント'
        verbose_name_plural = verbose_name
        unique_together = [('project', 'author')]
        ordering = ['order']

    def __str__(self):
        return f"{self.project} — @{self.author.username}"
