# -*- coding: utf-8 -*-
"""
予約されたバズ検索ジョブを実行するコマンド
scheduler サービスから定期的に呼び出される。

使用例:
  python manage.py th_buzz_run_scheduled
"""
import json
import logging
from pathlib import Path
import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from th.models import THBuzzSearchJob

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "予約時刻に達したバズ検索ジョブを実行"

    def handle(self, *args, **opts):
        now = timezone.now()

        # 予約時刻が過ぎている PENDING ジョブを取得
        due_jobs = THBuzzSearchJob.objects.filter(
            status='PENDING',
            scheduled_at__isnull=False,
            scheduled_at__lte=now,
        ).order_by('scheduled_at')

        cnt = due_jobs.count()
        if not cnt:
            return

        self.stdout.write(f"予約ジョブ: {cnt}件")

        log_dir = Path(settings.BASE_DIR) / 'deploy'
        log_dir.mkdir(parents=True, exist_ok=True)

        for job in due_jobs:
            self.stdout.write(f"  実行開始: Job#{job.id} keywords={job.keywords}")
            cmd = [sys.executable, 'manage.py', 'th_buzz_search', '--job-id', str(job.id)]
            try:
                log_out = open(log_dir / 'buzz_search_stdout.log', 'a')
                log_err = open(log_dir / 'buzz_search_stderr.log', 'a')
                subprocess.Popen(
                    cmd,
                    cwd=str(settings.BASE_DIR),
                    stdout=log_out,
                    stderr=log_err,
                )
                job.status = 'RUNNING'
                job.started_at = now
                job.save(update_fields=['status', 'started_at'])
            except Exception as e:
                logger.exception("ジョブ起動失敗: Job#%d", job.id)
                job.status = 'FAILED'
                job.error_message = str(e)
                job.save(update_fields=['status', 'error_message'])
