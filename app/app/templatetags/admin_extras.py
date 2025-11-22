from django import template
from django.contrib import admin

register = template.Library()

@register.simple_tag(takes_context=True)
def get_app_list(context):
    """
    AdminSite.get_app_list(request) を呼び出して app_list を返す。
    テンプレートでは `{% get_app_list as app_list %}` として使う。
    """
    request = context['request']
    return admin.site.get_app_list(request)
