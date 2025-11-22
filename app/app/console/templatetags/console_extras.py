# /srv/muitobem/app/app/console/templatetags/console_extras.py
import re
import json
from django import template
from django.utils.safestring import mark_safe
from app.console.utils.tpl_render import render_with_vars

register = template.Library()

@register.filter
def regex_find(value, pattern):
    """value から regex pattern に最初にマッチした文字列を返す（無ければ空）"""
    try:
        m = re.search(pattern, value or "")
        return m.group(0) if m else ""
    except re.error:
        return ""

@register.filter
def regex_replace(value, args):
    """
    置換フィルタ。args は "pattern|||replacement" という区切りで渡す。
    例: {{ text|regex_replace:"\\s+||| " }}
    """
    s = value or ""
    try:
        pattern, repl = args.split("|||", 1)
    except ValueError:
        return s
    try:
        return re.sub(pattern, repl, s)
    except re.error:
        return s

@register.filter
def human_json(value):
    """
    dict/list/JSON文字列を <pre> で整形表示する簡易フィルタ。
    """
    try:
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            text = json.dumps(json.loads(value), ensure_ascii=False, indent=2)
    except Exception:
        text = str(value)
    return mark_safe("<pre>" + text + "</pre>")

@register.filter
def tpl_render(text, ctx):
    """{{ text|tpl_render:ctx }} で差し込み済み文字列を得る"""
    try:
        return render_with_vars(text, ctx or {})
    except Exception:
        return text
