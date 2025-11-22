from django import template
register = template.Library()

@register.filter(name="length_is")
def length_is(value, arg):
    """Django<5 の length_is 互換: len(value) == int(arg)"""
    try:
        n = int(arg)
    except Exception:
        return False
    try:
        return len(value) == n
    except Exception:
        return False
