from django import template
from django.contrib import admin

register = template.Library()

@register.simple_tag(takes_context=True)
def get_app_list(context):
    """
    使い方: {% get_app_list as app_list %}
    """
    request = context['request']
    return admin.site.get_app_list(request)
