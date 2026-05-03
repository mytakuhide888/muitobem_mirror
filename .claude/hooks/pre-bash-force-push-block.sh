#!/usr/bin/env bash
# PreToolUse: Bash
# umbrella §0「git は人間」規約に従い、AI による git 操作（add/commit/push）を WARN 検出。
# force-push 系は settings.json の deny で遮断済だが、ログでも残す。dry-run なので進行は許可。

source "$(dirname "$0")/_lib.sh"
read_stdin_json

cmd="$(json_get '.tool_input.command')"

if [[ -z "$cmd" ]]; then
  dry_run_exit
fi

# git 系コマンドかチェック
if [[ ! "$cmd" =~ (^|[[:space:]])git[[:space:]] ]]; then
  dry_run_exit
fi

detected=""
level="DETECT"

# 危険度高: force-push 系
if [[ "$cmd" =~ (^|[[:space:]])--force([[:space:]]|$) ]]; then
  detected="git --force"
  level="WARN"
elif [[ "$cmd" =~ (^|[[:space:]])-f([[:space:]]|$) && "$cmd" =~ git[[:space:]]+push ]]; then
  detected="git push -f"
  level="WARN"
elif [[ "$cmd" =~ --force-with-lease ]]; then
  detected="git push --force-with-lease"
  level="WARN"
elif [[ "$cmd" =~ git[[:space:]]+push[[:space:]]+[^[:space:]]+[[:space:]]+\+ ]]; then
  detected="git push +ref refspec"
  level="WARN"
# umbrella §0 違反: AI による git 操作（人間タスク）
elif [[ "$cmd" =~ git[[:space:]]+add[[:space:]] ]]; then
  detected="git add (AI 実行禁止 — umbrella §0)"
elif [[ "$cmd" =~ git[[:space:]]+commit ]]; then
  detected="git commit (AI 実行禁止 — umbrella §0)"
elif [[ "$cmd" =~ git[[:space:]]+push ]]; then
  detected="git push (AI 実行禁止 — umbrella §0)"
elif [[ "$cmd" =~ git[[:space:]]+(checkout|switch|reset|rebase|cherry-pick|merge|branch[[:space:]]+-D) ]]; then
  detected="git branch 操作 (人間判断推奨)"
fi

if [[ -n "$detected" ]]; then
  log_event "pre-bash-force-push-block" "$level" \
    "kind=$detected command=$cmd"
  printf '[hook dry-run] git 操作検出 (kind=%s): %s\n' \
    "$detected" "$cmd" >&2
fi

dry_run_exit
