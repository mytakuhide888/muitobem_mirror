# -*- coding: utf-8 -*-
from django.urls import path
from . import views
from .views import api_ig
from .views import accounts as acc, permissions as perm
from .views import buzz as buzz_views
from .views import buzz_compare as buzz_compare_views
from .views import content_gen as content_gen_views
from .views import scheduled_posts as sched_views

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

    # バズ投稿取得
    path("buzz-search/",                      buzz_views.buzz_search,            name="buzz_search"),
    path("buzz-author/<int:pk>/",             buzz_views.buzz_author_detail,     name="buzz_author_detail"),
    path("api/buzz/run-search/",              buzz_views.buzz_run_search,        name="buzz_run_search"),
    path("api/buzz/run-account-fetch/",       buzz_views.buzz_run_account_fetch,  name="buzz_run_account_fetch"),
    path("api/buzz/fetch-author-posts/",      buzz_views.buzz_fetch_author_posts, name="buzz_fetch_author_posts"),
    path("api/buzz/job-status/<int:pk>/",     buzz_views.buzz_job_status,        name="buzz_job_status"),
    path("api/buzz/author-favorite/<int:pk>/", buzz_views.buzz_toggle_favorite,   name="buzz_toggle_favorite"),
    path("api/buzz/author-exclude/<int:pk>/", buzz_views.buzz_toggle_excluded,   name="buzz_toggle_excluded"),
    path("api/buzz/author-memo/<int:pk>/",    buzz_views.buzz_save_memo,         name="buzz_save_memo"),
    path("api/buzz/bulk-exclude/",            buzz_views.buzz_bulk_exclude,       name="buzz_bulk_exclude"),

    # 急成長アカウント発見
    path("buzz-growth-ranking/",              buzz_views.buzz_growth_ranking,    name="buzz_growth_ranking"),
    path("buzz-keyword-scan/",                buzz_views.buzz_keyword_scan,      name="buzz_keyword_scan"),
    path("api/buzz/run-keyword-scan/",        buzz_views.buzz_run_keyword_scan,  name="buzz_run_keyword_scan"),
    path("api/buzz/recalc-er/",              buzz_views.buzz_recalc_er,         name="buzz_recalc_er"),
    path("api/buzz/run-deep-scan/",          buzz_views.buzz_run_deep_scan,     name="buzz_run_deep_scan"),
    path("api/buzz/media-proxy/",            buzz_views.buzz_media_proxy,       name="buzz_media_proxy"),

    # Googleトレンド分析
    path("buzz-trends/",                      buzz_views.buzz_trends,            name="buzz_trends"),
    path("api/buzz/trends/",                  buzz_views.buzz_trends_api,        name="buzz_trends_api"),

    # 類似アカウント発見
    path("api/buzz/find-similar/<int:pk>/", buzz_views.buzz_find_similar, name="buzz_find_similar"),

    # アカウント比較
    path("buzz-compare/", buzz_compare_views.buzz_compare, name="buzz_compare"),

    # NGワードチェッカー
    path("buzz-ng-checker/", buzz_views.buzz_ng_checker, name="buzz_ng_checker"),
    path("api/buzz/ng-check/", buzz_views.buzz_ng_check_api, name="buzz_ng_check_api"),

    # 構造化分析メモ・パイプライン
    path("api/buzz/author-analysis/<int:pk>/", buzz_views.buzz_save_analysis,    name="buzz_save_analysis"),
    path("api/buzz/run-pipeline/",            buzz_views.buzz_run_pipeline,      name="buzz_run_pipeline"),

    # Phase C: 投稿文AI生成
    path("content-generator/",               content_gen_views.content_generator,     name="content_generator"),
    path("api/content/generate/",            content_gen_views.content_generate_api,  name="content_generate_api"),
    path("api/content/schedule/",            content_gen_views.content_schedule_api,  name="content_schedule_api"),

    # Phase C: 予約投稿管理
    path("scheduled-posts/",                        sched_views.scheduled_posts,           name="scheduled_posts"),
    path("api/scheduled-posts/<int:pk>/action/",    sched_views.scheduled_post_action_api, name="scheduled_post_action"),
    path("api/scheduled-posts/create/",             sched_views.scheduled_post_create_api, name="scheduled_post_create"),
]
