from django.apps import AppConfig
from django.contrib import admin

class SnsCoreConfig(AppConfig):
    name = "sns_core"
    verbose_name = "SNS運用コンソール"

    def ready(self):
        admin.site.site_header = "SNS運用 管理画面"
        admin.site.site_title = "SNS運用 管理画面"
        admin.site.index_title = "メニュー"
