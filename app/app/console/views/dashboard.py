# -*- coding: utf-8 -*-
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

@staff_member_required
def dashboard(request):
    """
    MVP用のシンプルなダッシュボード。
    ここから「接続テスト」「直近ログ」に飛べる導線だけ用意。
    """
    return render(request, "admin/console/dashboard.html")
