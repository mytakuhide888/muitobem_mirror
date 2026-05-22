# -*- coding: utf-8 -*-
"""
Phase G スクレイパイベント通知層。

- ScraperEventLog にイベントを記録
- ScraperNotificationConfig に従い Gmail SMTP でメール送信
- 同種イベントの集約（既定: 30 分以内に 3 件以上で 1 通にまとめる）
- SUSPENSION_DETECTED 時に ResearchAccount を SUSPENDED に倒す
"""
import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


LEVEL_ORDER = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3, 'CRITICAL': 4}


_EVENT_DEFAULT_LEVEL = {
    'LOGIN_SUCCESS': 'INFO',
    'LOGIN_FAILED': 'WARN',
    'RATE_LIMIT_HIT': 'WARN',
    'HTTP_403': 'WARN',
    'HTTP_429': 'WARN',
    'SUSPENSION_DETECTED': 'CRITICAL',
    'JOB_START': 'INFO',
    'JOB_COMPLETE': 'INFO',
    'JOB_FAILED': 'ERROR',
    'DAILY_LIMIT_REACHED': 'INFO',
    'QUIET_HOURS_ENTER': 'DEBUG',
    'PROXY_ERROR': 'ERROR',
    'WARMUP_PROMOTED': 'INFO',
}


def log_event(event_type: str, account=None, message: str = '',
              payload: Optional[dict] = None, level: Optional[str] = None):
    """ScraperEventLog にイベント記録し、通知判定を行う統一 API。

    Args:
        event_type: ScraperEventLog.EVENT_CHOICES に定義された文字列
        account:    ResearchAccount インスタンス（任意）
        message:    自由記述メッセージ
        payload:    JSON 化される付加データ
        level:      未指定なら EVENT_DEFAULT_LEVEL から推測

    Returns:
        ScraperEventLog インスタンス
    """
    from th.models import ScraperEventLog, ScraperNotificationConfig, ResearchAccount

    if level is None:
        level = _EVENT_DEFAULT_LEVEL.get(event_type, 'INFO')

    event = ScraperEventLog.objects.create(
        account=account,
        event_type=event_type,
        level=level,
        message=(message or '')[:1000],
        payload=payload or {},
    )

    config = ScraperNotificationConfig.load()

    # SUSPENSION_DETECTED の自動停止
    if event_type == 'SUSPENSION_DETECTED' and config.auto_stop_on_suspension and account is not None:
        try:
            account.status = ResearchAccount.STATUS_SUSPENDED
            account.suspended_at = timezone.now()
            account.suspended_reason = (message or '凍結検知（自動停止）')[:2000]
            account.save(update_fields=[
                'status', 'suspended_at', 'suspended_reason', 'updated_at',
            ])
            logger.warning(
                'SUSPENSION_DETECTED: ResearchAccount[%s] を自動停止しました',
                account.name,
            )
        except Exception as e:
            logger.error('ResearchAccount 自動停止失敗: %s', e)

    # メール通知判定
    try:
        _maybe_send_notification(event, config)
    except Exception as e:
        logger.error('通知メール送信失敗: %s', e)

    return event


def _maybe_send_notification(event, config) -> None:
    """通知条件を判定し、必要なら _send_mail を呼ぶ"""
    if not config.enabled:
        return
    if not (config.recipient_emails or '').strip():
        return
    if event.event_type not in (config.notify_events or []):
        return
    if LEVEL_ORDER.get(event.level, 1) < LEVEL_ORDER.get(config.min_level, 2):
        return

    # 集約：同種イベントが N 分以内に既に通知済みで、まだ集約閾値に達してないならスキップ
    from th.models import ScraperEventLog
    window_start = timezone.now() - timedelta(minutes=config.aggregate_window_min)
    recent_qs = ScraperEventLog.objects.filter(
        event_type=event.event_type,
        created_at__gte=window_start,
    )
    recent_count = recent_qs.count()
    already_notified = recent_qs.filter(notified=True).exclude(pk=event.pk).exists()
    if already_notified and recent_count < config.aggregate_threshold:
        # 既に通知済み、まだ閾値未満 → 抑制
        return

    _send_mail(event, recent_count, config)
    event.notified = True
    event.save(update_fields=['notified'])


def _send_mail(event, recent_count: int, config) -> None:
    from django.conf import settings
    from django.core.mail import send_mail

    recipients = [e.strip() for e in (config.recipient_emails or '').split(',') if e.strip()]
    if not recipients:
        return

    subject = f'[muitobem scraper] {event.level} {event.event_type}'
    if recent_count > 1:
        subject += f' (直近{recent_count}件)'

    account_str = event.account.name if event.account else '-'
    local_dt = timezone.localtime(event.created_at)

    body = (
        'スクレイパイベント通知\n'
        '\n'
        f'種別: {event.event_type} ({event.level})\n'
        f'発生時刻: {local_dt:%Y-%m-%d %H:%M:%S %z}\n'
        f'対象アカウント: {account_str}\n'
        f'メッセージ: {event.message}\n'
        f'直近 {config.aggregate_window_min} 分以内の同種件数: {recent_count}\n'
        '\n'
        '管理画面: https://muitobem.top/admin/th/scrapereventlog/\n'
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or getattr(settings, 'EMAIL_HOST_USER', '')
    send_mail(
        subject=subject,
        message=body,
        from_email=from_email or None,
        recipient_list=recipients,
        fail_silently=False,
    )
    logger.info('通知メール送信: %s → %s', event.event_type, recipients)
