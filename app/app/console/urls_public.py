from django.urls import path
from .views import oauth as v
from .views import webhooks as w

app_name = "meta_public"

urlpatterns = [
    path("start/",    v.meta_oauth_start, name="meta_oauth_start"),
    path("callback/", v.meta_oauth_cb,    name="meta_oauth_cb"),
    path("import/",   v.meta_import,      name="meta_import"),
    # Webhook は1本にまとめる（GET検証/POST受信）
    path("webhook/",  w.meta_webhook,     name="meta_webhook"),
    path("disconnect/", v.meta_disconnect, name="meta_disconnect"),
]
