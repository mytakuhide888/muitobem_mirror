import json
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from ig.models import IGWebhookEvent
from th.models import THWebhookEvent

logger = logging.getLogger(__name__)


@csrf_exempt
def instagram(request):
    if request.method == 'GET':
        if request.GET.get('hub.verify_token') == getattr(settings, 'VERIFY_TOKEN_IG', ''):
            return HttpResponse(request.GET.get('hub.challenge', ''))
        return HttpResponse('invalid', status=403)
    payload = json.loads(request.body.decode('utf-8') or '{}')
    IGWebhookEvent.objects.create(event_type='generic', payload=payload)
    logger.info('received instagram webhook')
    return HttpResponse('ok')


@csrf_exempt
def threads(request):
    if request.method == 'GET':
        if request.GET.get('hub.verify_token') == getattr(settings, 'VERIFY_TOKEN_TH', ''):
            return HttpResponse(request.GET.get('hub.challenge', ''))
        return HttpResponse('invalid', status=403)
    payload = json.loads(request.body.decode('utf-8') or '{}')
    THWebhookEvent.objects.create(event_type='generic', payload=payload)
    logger.info('received threads webhook')
    return HttpResponse('ok')
