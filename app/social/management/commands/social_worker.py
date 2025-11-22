from __future__ import annotations

import time
from django.core.management.base import BaseCommand
from django.utils import timezone

from django.conf import settings

from ...models import Job, Platform
from ...services import ig_api, threads_api


class Command(BaseCommand):
    help = "Process social jobs"

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true')

    def handle(self, *args, **options):
        loop = options.get('loop')
        interval = getattr(settings, 'WORKER_INTERVAL_SEC', 5)
        while True:
            now = timezone.now()
            job = Job.objects.filter(status=Job.Status.PENDING, run_at__lte=now).order_by('run_at').first()
            if job:
                self.process_job(job)
            if not loop:
                break
            time.sleep(interval)

    def process_job(self, job: Job):
        job.status = Job.Status.RUNNING
        job.save(update_fields=['status'])
        try:
            if job.job_type == Job.Type.REPLY:
                text = job.args.get('text')
                if job.platform == Platform.INSTAGRAM:
                    ig_api.send_dm(job.args.get('access_token', ''), job.args.get('recipient_id', ''), text)
                elif job.platform == Platform.THREADS:
                    threads_api.reply_to_post(job.args.get('post_id', ''), job.args.get('account_token', ''), text)
            job.status = Job.Status.DONE
            job.save(update_fields=['status'])
        except Exception as exc:  # pragma: no cover - network failures
            job.status = Job.Status.FAILED
            job.last_error = str(exc)
            job.save(update_fields=['status', 'last_error'])
