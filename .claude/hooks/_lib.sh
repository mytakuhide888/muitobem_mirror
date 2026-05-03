#!/usr/bin/env bash
# 共通ライブラリ — hooks スクリプトから source して使う
# dry-run 期間中は exit 0 で常に進行許可。検出結果は log ファイルへ追記する。

set -uo pipefail

HOOK_LOG_DIR="${CLAUDE_PROJECT_DIR:-/home/niiya/muitobem_mirror}/.claude/hooks/log"
mkdir -p "$HOOK_LOG_DIR" 2>/dev/null || true

# 標準入力の JSON を読み取って変数に格納（jq が無くても動く軽量パース）
read_stdin_json() {
  HOOK_INPUT="$(cat)"
  export HOOK_INPUT
}

# 簡易 JSON 値取得（jq があれば優先、なければ python3）
json_get() {
  local key="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$HOOK_INPUT" | jq -r "$key // empty" 2>/dev/null
  else
    printf '%s' "$HOOK_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin)
keys=sys.argv[1].lstrip('.').split('.')
v=d
try:
  for k in keys:
    if k=='': continue
    v=v[k] if isinstance(v,dict) else None
    if v is None: break
  print('' if v is None else v)
except Exception:
  print('')" "$key" 2>/dev/null
  fi
}

log_event() {
  local hook_name="$1"
  local level="$2"  # INFO / DETECT / WARN
  local message="$3"
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  printf '[%s] %s %s %s\n' "$ts" "$level" "$hook_name" "$message" \
    >> "$HOOK_LOG_DIR/hooks.log"
}

dry_run_exit() {
  exit 0
}
