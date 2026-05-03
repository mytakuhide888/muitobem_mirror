#!/usr/bin/env bash
# PostToolUse: Edit / Write / MultiEdit
# .py 編集後に ast.parse で構文検証。dry-run なので失敗してもログのみ。

source "$(dirname "$0")/_lib.sh"
read_stdin_json

tool_name="$(json_get '.tool_name')"
file_path="$(json_get '.tool_input.file_path')"

if [[ -z "$file_path" ]]; then
  dry_run_exit
fi

case "$file_path" in
  *.py) ;;
  *) dry_run_exit ;;
esac

if [[ ! -f "$file_path" ]]; then
  dry_run_exit
fi

if err="$(python3 -c "import ast,sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
except SyntaxError as e:
    print(f'{e.__class__.__name__}: {e.msg} (line {e.lineno})')
    sys.exit(1)
" "$file_path" 2>&1)"; then
  log_event "post-edit-pyflake" "INFO" "OK tool=$tool_name path=$file_path"
else
  log_event "post-edit-pyflake" "WARN" \
    "SyntaxError tool=$tool_name path=$file_path detail=${err}"
  printf '[hook dry-run] pyflake: %s で構文エラー: %s\n' \
    "$file_path" "$err" >&2
fi

dry_run_exit
