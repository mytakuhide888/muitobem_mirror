from django.contrib import admin


class TimeStampedAdminMixin(admin.ModelAdmin):
    """作成/更新日時を読み取り専用にする共通Mixin"""
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
