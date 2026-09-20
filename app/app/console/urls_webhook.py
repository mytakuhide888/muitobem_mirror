# app/console/urls_webhook.py
from django.urls import path
from .views import webhooks as v

urlpatterns = [
    path("instagram/", v.meta_webhook, name="instagram_webhook"),
]
