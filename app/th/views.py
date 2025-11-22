import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def placeholder(request, *args, **kwargs):
    return HttpResponse('OK')


def posts(request):
    return HttpResponse('TH posts')


def posts_import(request):
    logger.info('TH posts import')
    return HttpResponse('imported')


def posts_sync(request):
    logger.info('TH posts sync')
    return HttpResponse('synced')


def scheduled(request):
    return HttpResponse('scheduled')


def scheduled_approve(request, pk):
    logger.info('TH scheduled approve %s', pk)
    return HttpResponse('approved')
