#!/usr/bin/env bash
# PreToolUse: Edit / Write / MultiEdit
# 機密ファイルへの編集を検出してログ出力。dry-run 中は遮断しない。
# 対象: .env / docker-compose.yml / Caddyfile / threads_session.json /
#       CLAUDE/ops/* / *.pem / *.key / *.credentials*

source "$(dirname "$0")/_lib.sh"
read_stdin_json

tool_name="$(json_get '.tool_name')"
file_path="$(json_get '.tool_input.file_path')"

if [[ -z "$file_path" ]]; then
  dry_run_exit
fi

detected=""
case "$file_path" in
  *.env|*/.env)                      detected=".env" ;;
  */docker-compose.yml)              detected="docker-compose.yml" ;;
  */Caddyfile)                       detected="Caddyfile" ;;
  */threads_session.json)            detected="threads_session" ;;
  */CLAUDE/ops/*)                    detected="CLAUDE/ops (機密含む)" ;;
  */docs/handover_summary.md)        detected="handover_summary (SSH 情報含む可能性)" ;;
  *.credentials*|*credentials.json)  detected="credentials" ;;
  *.pem|*.key)                       detected="key file" ;;
esac

if [[ -n "$detected" ]]; then
  log_event "pre-edit-secret-scan" "DETECT" \
    "tool=$tool_name kind=$detected path=$file_path"
  printf '[hook dry-run] secret-scan: %s への編集を検出 (kind=%s)\n' \
    "$file_path" "$detected" >&2
fi

dry_run_exit
