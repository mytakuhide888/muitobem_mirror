import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def placeholder(request, *args, **kwargs):
    return HttpResponse('OK')


def posts(request):
    return HttpResponse('IG posts')


def posts_import(request):
    logger.info('IG posts import')
    return HttpResponse('imported')


def posts_sync(request):
    logger.info('IG posts sync')
    return HttpResponse('synced')


def scheduled(request):
    return HttpResponse('scheduled')


def scheduled_approve(request, pk):
    logger.info('IG scheduled approve %s', pk)
    return HttpResponse('approved')
