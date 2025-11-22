# -*- coding: utf-8 -*-
import traceback
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.shortcuts import render

@staff_member_required
def connection_test(request):
    """
    最小限の健全性チェック（DB接続・主要モデル存在）をサーバー側で実行。
    将来的にAPI疎通などを拡張予定。
    """
    checks = []

    # 1) DB疎通
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks.append(("データベース接続", True, "OK"))
    except Exception as e:
        checks.append(("データベース接続", False, f"{e.__class__.__name__}: {e}"))

    # 2) 主要モデルの存在確認と件数
    def count_or_error(label, dotted_model):
        try:
            module, name = dotted_model.rsplit(".", 1)
            m = __import__(module, fromlist=[name])
            Model = getattr(m, name)
            return (label, True, f"{Model.objects.count()} 件")
        except Exception as e:
            return (label, False, f"{e.__class__.__name__}: {e}")

    checks.append(count_or_error("Instagramビジネスアカウント", "ig.models.InstagramBusinessAccount"))
    checks.append(count_or_error("Threadsアカウント", "th.models.ThreadsAccount"))

    return render(request, "admin/console/connection_test.html", {"checks": checks})
