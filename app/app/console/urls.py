# -*- coding: utf-8 -*-
from django.urls import path
from . import views
from .views import api_ig
from .views import accounts as acc, permissions as perm

app_name = "console"

urlpatterns = [
    path("", views.dashboard, name="index"),
    path("connection-test/", views.connection_test, name="connection_test"),
    path("logs/", views.logs, name="logs"), 
    path("integration/", views.integration, name="integration"),
    path("webhook-test/", views.webhook_test, name="webhook_test"),
    path("webhook-events/", views.webhook_events, name="webhook_events"),
    path("webhook/setup/", views.webhook_test, name="webhook_setup"),
    path("webhook-replay/<str:src>/<int:pk>/", views.webhook_replay, name="webhook_replay"),
    path("help/", views.help_guide, name="help"),
    path("setup/", views.setup_env, name="setup_env"),
    path("setup/templates/", views.setup_templates, name="setup_templates"),
    path("setup/rules/", views.setup_rules, name="setup_rules"),
    path("templates/", views.tpl_list, name="tpl_list"),
    path("templates/new/", views.tpl_new, name="tpl_new"),
    path("templates/<int:pk>/", views.tpl_edit, name="tpl_edit"),
    path("templates/<int:pk>/delete/", views.tpl_delete, name="tpl_delete"),
    path("templates/export/", views.tpl_export, name="tpl_export"),
    path("templates/import/", views.tpl_import, name="tpl_import"),
    path("templates/preview/", views.tpl_preview_api, name="tpl_preview_api"),
    path("accounts/",    acc.accounts_list, name="accounts"),
    path("permissions/", perm.permissions_check, name="permissions"),
    path("api/ig/comment-reply/", api_ig.ig_comment_reply, name="api_ig_comment_reply"),
    path("api/ig/dm-reply/",      api_ig.ig_dm_reply,      name="api_ig_dm_reply"),
]
