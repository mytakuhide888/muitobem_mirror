# app/console/permissions_map.py
REQUIRED = {
  "ig_read_basic": {"scopes": {"instagram_basic", "pages_show_list"}},
  "ig_publish":    {"scopes": {"instagram_basic", "instagram_content_publish", "pages_show_list", "pages_manage_metadata"}},
  "ig_webhook":    {"scopes": {"pages_manage_metadata"}},
  # 例: DM 取得など
  "ig_messages":   {"scopes": {"instagram_manage_messages", "pages_show_list"}},
}
