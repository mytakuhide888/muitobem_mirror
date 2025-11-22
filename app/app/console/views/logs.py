# -*- coding: utf-8 -*-
import os
import shlex
import subprocess
import logging
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

logger = logging.getLogger(__name__)

def _pick_log_path():
    """
    参照候補を上から順にチェックして最初に存在するものを使う。
    """
    candidates = []

    # settings で定義したファイルを最優先
    log_file = getattr(settings, "LOG_FILE", None)
    if log_file:
        candidates.append(str(log_file))

    # 互換の候補
    candidates.extend([
        "/app/deploy/app.log",
        "/app/deploy/django.log",
        "/proc/1/fd/1",
    ])

    for p in candidates:
        try:
            if p and os.path.exists(p):
                return p
        except Exception:
            pass
    return None

def _tail_file(path: str, n: int = 500) -> str:
    try:
        out = subprocess.check_output(
            ["bash", "-lc", f"tail -n {int(n)} {shlex.quote(path)}"],
            text=True,
            stderr=subprocess.STDOUT,
        )
        return out
    except Exception as e:
        return f"[tail失敗] {e.__class__.__name__}: {e}"

@staff_member_required
def logs_view(request):
    # アクセスログを1行残す（ファイル出力を確実化）
    logger.info("Console Logs viewed by user=%s", getattr(request.user, "username", "?"))

    # 行数パラメータ
    n = request.GET.get("n")
    try:
        n = int(n) if n is not None else 500
    except Exception:
        n = 500
    n = max(10, min(n, 5000))

    path = _pick_log_path()
    if not path:
        body = (
            "参照可能なログファイルが見つかりませんでした。\n"
            "settings.LOG_FILE や /app/deploy/app.log を作成後、再度お試しください。"
        )
    else:
        body = _tail_file(path, n=n)

    # 追加情報（サイズ等）
    size = None
    try:
        size = os.path.getsize(path) if path else None
    except Exception:
        pass

    return render(
        request,
        "admin/console/logs.html",
        {"log_path": path, "n": n, "body": body, "size": size},
    )
