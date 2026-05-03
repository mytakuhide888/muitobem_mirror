#!/usr/bin/env bash
# Stop: セッション終了時
# CLAUDE/<YYYYMMDD>_<連番>/summary.md の「## 検証結果」セクションが空なら警告。
# umbrella §1.2 規約に基づく作業記録ディレクトリを対象とする。
# dry-run なので警告のみ、進行は阻害しない。

source "$(dirname "$0")/_lib.sh"
read_stdin_json

CLAUDE_BASE="${CLAUDE_PROJECT_DIR:-/home/niiya/muitobem_mirror}/CLAUDE"

if [[ ! -d "$CLAUDE_BASE" ]]; then
  dry_run_exit
fi

today="$(date '+%Y%m%d')"
latest_dir=""
while IFS= read -r d; do
  latest_dir="$d"
  break
done < <(ls -1dt "$CLAUDE_BASE"/${today}_* 2>/dev/null)

if [[ -z "$latest_dir" || ! -d "$latest_dir" ]]; then
  log_event "stop-summary-required" "INFO" \
    "今日の作業記録ディレクトリなし（base=$CLAUDE_BASE today=$today）"
  dry_run_exit
fi

summary="$latest_dir/summary.md"
if [[ ! -f "$summary" ]]; then
  log_event "stop-summary-required" "WARN" "summary.md が無い: $latest_dir"
  printf '[hook dry-run] stop-summary: %s/summary.md が存在しません\n' \
    "$latest_dir" >&2
  dry_run_exit
fi

body="$(awk '
  /^## 検証結果/ { capture=1; next }
  capture==1 && /^## / { exit }
  capture==1 { print }
' "$summary")"

content_chars="$(printf '%s' "$body" | tr -d '[:space:]' | wc -c | tr -d ' ')"

if [[ "$content_chars" -lt 30 ]] || printf '%s' "$body" | grep -qE "（実装完了後に追記）|検証ステップ完了後に追記"; then
  log_event "stop-summary-required" "WARN" \
    "## 検証結果 が空または placeholder のみ: $summary"
  printf '[hook dry-run] stop-summary: %s の「## 検証結果」が未記入です\n' \
    "$summary" >&2
else
  log_event "stop-summary-required" "INFO" "OK: $summary（chars=$content_chars）"
fi

dry_run_exit
