# app/context_processors.py
from django.contrib import admin

def admin_nav_sidebar(request):
    """
    Admin テンプレートに左サイドバー用の値を常時供給する。
    - is_nav_sidebar_enabled: 左サイドバーの描画ガード（True で常に描画）
    - available_apps: nav_sidebar.html のグルーピング元
    """
    # AdminSite.each_context と同等の値を自前でも用意しておく
    try:
        app_list = admin.site.get_app_list(request)
    except Exception:
        app_list = []

    return {
        "is_nav_sidebar_enabled": True,
        "available_apps": app_list,
    }
