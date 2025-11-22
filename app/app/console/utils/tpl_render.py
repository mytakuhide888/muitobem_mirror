# app/console/utils/tpl_render.py
import re
from typing import Any, Mapping

_var = re.compile(r"\{\{\s*([a-zA-Z_][\w\.]*)\s*\}\}")

def _dig(obj: Mapping[str, Any], key: str, default: str = "") -> str:
    cur: Any = obj
    for part in key.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return "" if cur is None else str(cur)

def render_with_vars(text: str, ctx: Mapping[str, Any]) -> str:
    """DBに保存した本文内の {{ key }} を ctx で置換（Djangoテンプレとは無関係の軽量置換）"""
    if not text:
        return ""
    return _var.sub(lambda m: _dig(ctx, m.group(1), ""), text)
