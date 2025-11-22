from django.apps import AppConfig

class ConsoleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.console"
    verbose_name = "SNS運用"

    def ready(self):
        from django.contrib import admin
        admin.site.site_header = "SNS運用管理画面"
        admin.site.site_title = "SNS運用管理画面"
        admin.site.index_title = "メニュー"
