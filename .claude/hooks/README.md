# .claude/hooks — 強制レイヤー

機械的検証で人間／AI の取りこぼしを防ぐ層。
**現在は dry-run（exit 0）** で運用中。検出はログに残るが進行は止めない。
本番化（exit 2 で遮断）は運用が安定してから検討。

## 構成

| Hook | イベント | 目的 |
|---|---|---|
| `pre-edit-secret-scan.sh` | PreToolUse: Edit/Write/MultiEdit | `.env` / `Caddyfile` / `docker-compose.yml` / `CLAUDE/ops/` / 鍵ファイル等への編集を検出 |
| `pre-bash-force-push-block.sh` | PreToolUse: Bash | force-push 系を検出。umbrella §0「git は人間」違反となる `git add/commit/push` も WARN 検出 |
| `post-edit-pyflake.sh` | PostToolUse: Edit/Write/MultiEdit | `.py` 編集後に `ast.parse` で構文検証 |
| `stop-summary-required.sh` | Stop | `CLAUDE/<YYYYMMDD>_<連番>/summary.md` の「## 検証結果」セクションが空でないか確認 |

## ログ
- 出力先: `.claude/hooks/log/hooks.log`（`.gitignore` 対象）
- フォーマット: `[YYYY-MM-DD HH:MM:SS] <LEVEL> <hook_name> <message>`

## 共通ライブラリ
- `_lib.sh`: stdin JSON のパース、ログ書き込み、dry-run 終了。

## 本番化（将来）
dry-run を外す場合は、各 hook の末尾 `dry_run_exit` を `exit 2` に変えて stderr に理由を出力する。
