from django.db import models

class MessageTemplate(models.Model):
    SERVICE_CHOICES = [
        ('common', '共通'),
        ('ig', 'Instagram'),
        ('th', 'Threads'),
    ]
    service = models.CharField(max_length=16, choices=SERVICE_CHOICES, default='common')
    name = models.CharField(max_length=100)
    key = models.SlugField(max_length=100, unique=True, help_text="英数字とハイフン。ルール等から参照できます。")
    description = models.TextField(blank=True, default='')
    content = models.TextField(help_text="本文。{{ user_name }} のような差し込みが使えます。")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'console_message_templates'
        ordering = ['-updated_at']
        verbose_name = '返信テンプレート'
        verbose_name_plural = '返信テンプレート'

    def __str__(self):
        return f"[{self.get_service_display()}] {self.name}"
