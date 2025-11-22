# app/console/urls_webhook.py
from django.urls import path
from .views import webhook as v

urlpatterns = [
    path("instagram/", v.instagram_webhook, name="instagram_webhook"),
]
