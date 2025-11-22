from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from social.models import WebhookEvent, DMMessage, Platform


def _save_event(platform):
    payload = {'dummy': True}
    WebhookEvent.objects.create(platform=platform, event_type='dummy', payload=payload)
    DMMessage.objects.create(platform=platform, sender_external_user_id='user', text='テスト', received_at=timezone.now(), raw_json=payload)


@csrf_exempt
def threads_webhook(request):
    _save_event(Platform.THREADS)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def instagram_webhook(request):
    _save_event(Platform.INSTAGRAM)
    return JsonResponse({'status': 'ok'})
