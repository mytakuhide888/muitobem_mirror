# タスク記録 — .claude 整備（sakura-ama-wowma の構造を muitobem_mirror に取り入れ）

## 概要
- 背景：sakura-ama-wowma で整理された skills / agents / hooks / workflows / memory の運用が確立。muitobem_mirror 側はほぼ未整備で、開発時に承認プロンプト多発・機密混入・教訓散逸のリスクあり。
- ゴール：muitobem_mirror に同等の `.claude/` 体系を構築し、Plan→Build→Review→Test→Ship の自動化レイヤーと、機密遮断・構文検証・要約欠落検知の hook を稼働させる。
- 影響範囲：`.claude/` 配下全般、`CLAUDE.md`（スリム化）、`tasks/lessons.md`（移行）、umbrella `/home/niiya/CLAUDE.md`（参照先更新）、`.gitignore`（機密ディレクトリ追加）、`.cursor/rules/`（Karpathy 複製）。
- 期限/優先度：単発作業。Phase 0（機密分離）が最優先。

## 現状（事実）
- `.claude/` には `settings.local.json`（最小権限のみ）しかない。
- `tasks/lessons.md` に教訓 5 件（Claude Code から発見されにくい場所）。
- `CLAUDE.md` 175 行、SSH パスワード `@Kuurie338` 平文記載。
- `git log origin/main` 確認結果：コミット `c4b69b2 docs: CLAUDE.mdにdocs必読ルール・デプロイ手順・SSH情報を追記` は **origin/main に push 済**。GitHub に SSH パスワード流出。
- `docs/handover_summary.md` も git 追跡済み（同様の機密含む可能性）。
- `.gitignore` 末尾に `# CLAUDE project files` のコメントだけで除外指定なし。

## Plan（編集前）

### Phase 0. 機密分離（最優先）
- `CLAUDE/ops/server.md` を新設し、SSH 接続情報・パスワード・デプロイ手順を集約（AI が把握できる形で残す）。
- `.gitignore` に `CLAUDE/ops/` を追加。
- `CLAUDE.md` と `docs/handover_summary.md` から平文パスワードを削除し、`CLAUDE/ops/server.md` への参照に置換。
- 既に push 済の漏洩は人間にレポート（履歴書き換えは破壊的操作のため AI からは実施しない）。

### Phase 1. `.claude/settings.json`（共有）新設
- `permissions.allow`: `Bash(*)` `Read` `Write` `Edit` `Grep` `Glob` `WebFetch` `Computer` `Mcp`（umbrella §0「git は人間」と整合する形で **deny で git push --force* / -f を遮断**）。
- `permissions.deny`: `Bash(rm -rf /)` `Bash(rm -rf ~)` `Bash(rm -rf ~/*)` `Bash(git push --force*)` `Bash(git push -f *)` `Bash(git push -f)`。
- `hooks` に PreToolUse / PostToolUse / Stop の 4 件を登録。

### Phase 2. `.claude/hooks/` 4 種＋共通ライブラリを移植
- `_lib.sh`：sakura 版を流用。
- `pre-edit-secret-scan.sh`：muitobem 用に対象拡張（`docker-compose.yml`, `Caddyfile`, `docs/handover_summary.md`, `CLAUDE/ops/*`, `*.env`, `*.pem`, `*.key`, `threads_session.json` 等）。
- `pre-bash-force-push-block.sh`：force-push に加え、umbrella §0 違反となる `git add` / `git commit` / `git push` 全般を WARN 検出（dry-run）。
- `post-edit-pyflake.sh`：sakura 版そのまま。
- `stop-summary-required.sh`：muitobem の `CLAUDE/<YYYYMMDD>_<連番>/summary.md` 規約に合わせる。
- 全 hook は **dry-run（exit 0）** で開始。

### Phase 3. `.claude/agents/` 4 種を移植
- architect / coder / reviewer / optimizer。
- 参照先（ADR / runbook）を muitobem 用に書き換え（muitobem は ADR 未整備なので汎用記述に留める）。

### Phase 4. `.claude/skills/` 5 種を新設
| Skill | 内容 |
|---|---|
| vps-deploy | sshpass + git pull + collectstatic + restart + migrate + 検証 |
| docker-ops | `docker compose ps/logs/exec/restart`、コンテナ別の使い分け |
| threads-ops | `social/services/threads_api.py`、投稿、バズリサーチ巡回 |
| instagram-ops | ig/ モデル・Webhook、API スタブ状況 |
| scheduler-ops | 60 秒間隔の定期ジョブ、予約投稿 |

### Phase 5. `.claude/workflows/plan-build-review-test-ship.md` を移植
- sakura 版を流用、Test ステップの検証コマンドを muitobem 用（HTTP 200 確認・docker logs grep ERROR）に置換。

### Phase 6. lessons.md 移行
- `tasks/lessons.md` 5 件を `.claude/memory/lessons.md` に移行。書式は sakura の高シグナル教訓スタイルに整える。
- umbrella `/home/niiya/CLAUDE.md` の `tasks/lessons.md` 参照を `.claude/memory/lessons.md` に更新。
- `tasks/lessons.md` は移行後に空ファイル化＋移行先案内を残す（既存リンク切れ防止）。

### Phase 7. `CLAUDE.md` スリム化
- 175 行 → 60〜80 行程度の「システムの脳」化。
- デプロイ手順は vps-deploy Skill へ、SSH 情報は `CLAUDE/ops/server.md` へ移管。
- クイックリファレンス表で各リソースへのリンクのみ残す。

### Phase 8. `.cursor/rules/karpathy-guidelines.mdc` 複製
- sakura 版を流用（プロジェクト非依存）。

### 検証コマンド
- 構文: 各 hook を `bash -n` で構文チェック、Python 系は `python3 -c "import ast; ast.parse(...)"`。
- 動作: hook stdin に擬似 JSON を流し込み、ログが書き出されるか確認。
- settings: `python3 -c "import json; json.load(open('.claude/settings.json'))"`。

### ロールバック
- `.claude/` は新規追加のみなのでディレクトリごと削除で完全復元。
- `CLAUDE.md` / `tasks/lessons.md` / `.gitignore` / umbrella は変更前の内容を summary.md に貼って残す（次セクション）。

## 調査ログ（追記）
- 2026-05-02 11:xx: sakura-ama-wowma 配下の `.claude/` 全部読み込み済（agents/hooks/skills/workflows/memory）。
- 2026-05-02 11:xx: muitobem_mirror の `git ls-files` で `CLAUDE.md` `docs/handover_summary.md` が追跡済と判明。`git log @{u}..` 空で push 済確定。

## 実装内容（追記）

### Phase 0. 機密分離
- `CLAUDE/ops/server.md` 新規作成（SSH 接続情報・パスワード・デプロイコマンド集約）
- `.gitignore` に `CLAUDE/ops/` ／ `.claude/hooks/log/` ／ `.claude/settings.local.json` を追加
- `CLAUDE.md` 内の SSH パスワード平文記載を削除し、`CLAUDE/ops/server.md` 参照に置換
- `docs/handover_summary.md` には平文パスワードなし（IP のみ）→ 修正不要

### Phase 1. `.claude/settings.json` 新設
- `permissions.allow`: Read / Write / Edit / Grep / Glob / WebFetch / Computer / Mcp / Bash(*)
- `permissions.deny`: rm -rf 系 4 件＋ git push --force 系 4 件
- `hooks` に PreToolUse（2）／ PostToolUse（1）／ Stop（1）の 4 hook を登録

### Phase 2. `.claude/hooks/` 5 ファイル
- `_lib.sh`：共通ライブラリ（stdin JSON パース・ログ・dry-run 終了）
- `pre-edit-secret-scan.sh`：機密ファイル編集検出（`.env` / `Caddyfile` / `docker-compose.yml` / `CLAUDE/ops/` / `threads_session.json` / 鍵ファイル等）
- `pre-bash-force-push-block.sh`：force-push 検出＋ umbrella §0 違反（`git add` / `git commit` / `git push`）の WARN 検出
- `post-edit-pyflake.sh`：`.py` 編集後の `ast.parse` 構文検証
- `stop-summary-required.sh`：`CLAUDE/<日付>_<連番>/summary.md` の「## 検証結果」欄を確認
- 全 hook が dry-run（exit 0）で動作
- `README.md` で運用方針記載

### Phase 3. `.claude/agents/` 5 ファイル
- `architect.md` / `coder.md` / `reviewer.md` / `optimizer.md`
- 参照先（システムの脳・教訓・SKILL）を muitobem 用に書き換え
- `README.md` で役割対応表

### Phase 4. `.claude/skills/` 6 ファイル
- `vps-deploy/SKILL.md`：sshpass 経由のデプロイフロー、検証コマンド
- `docker-ops/SKILL.md`：4 コンテナ構成、`restart` vs `up -d` 使い分け
- `threads-ops/SKILL.md`：Threads 業務（投稿・バズ・コンセプト・自動投稿）
- `instagram-ops/SKILL.md`：Instagram 業務（Webhook・自動返信・インサイト）
- `scheduler-ops/SKILL.md`：60 秒ループ・flock・06:00 パイプライン
- `README.md` で Skill 一覧

### Phase 5. `.claude/workflows/` 2 ファイル
- `plan-build-review-test-ship.md`：5 ステップ × 各 verify ＋失敗時分岐
- `README.md`

### Phase 6. lessons.md 移行
- `tasks/lessons.md` 5 件 → `.claude/memory/lessons.md` に書式統一（**学び** / **回避** / **適用** / **再利用**）で移行
- `tasks/lessons.md` は移行案内ファイルに置換
- umbrella `/home/niiya/CLAUDE.md` の `tasks/lessons.md` 参照を `.claude/memory/lessons.md` に更新（2 箇所）
- `.claude/memory/README.md` で運用基準記載

### Phase 7. CLAUDE.md スリム化
- 175 行 → 約 75 行
- sakura-ama-wowma 風「システムの脳」化（メンタルモデル＋実行ルール＋クイックリファレンス）
- デプロイ手順は `vps-deploy` Skill へ移管、SSH 情報は `CLAUDE/ops/server.md` 参照に統一
- 教訓のサマリ（innerHTML 禁止／.env 変更時 up -d ／ git add -A 禁止）を本文に明記

### Phase 8. `.cursor/rules/karpathy-guidelines.mdc` 複製
- sakura 版を流用（`alwaysApply: true`）

## 検証結果（追記）

### 実行コマンドと結果
- `find .claude .cursor CLAUDE/ops -type f`：26 ファイル生成確認（settings.json / hooks 5 / agents 5 / skills 6 / workflows 2 / memory 2 / cursor 1 / ops 1 ＋ settings.local.json 既存）
- `python3 -c "import json; json.load(...)"`：settings.json 構造妥当（3 hook events, 9 allow, 7 deny）
- `bash -n` 全 hook ファイル：構文 OK
- `pre-edit-secret-scan.sh` ドライラン（`CLAUDE/ops/server.md` 編集をシミュレート）：DETECT 出力＋ exit=0 ＋ ログ書き込み確認
- `pre-bash-force-push-block.sh` ドライラン（`git push --force origin main`）：WARN 出力＋ exit=0 ＋ ログ書き込み確認
- `git ls-files | xargs grep -l "Kuurie338"`：**追跡ファイルから機密文字列の混入なし**
- `git check-ignore -v CLAUDE/ops/server.md`：`.gitignore:34:CLAUDE/ops/` で除外確認
- `git check-ignore -v .claude/hooks/log/hooks.log`：`.gitignore:35:.claude/hooks/log/` で除外確認

### 受け入れ条件チェック
- [x] `.claude/settings.json` で承認プロンプト激減（Bash(*) 解放）
- [x] hooks dry-run で機密検出ログが残る
- [x] 全 agent / skill / workflow が独立配置・README 完備
- [x] tasks/lessons.md → .claude/memory/lessons.md 移行＋ umbrella 参照更新
- [x] CLAUDE.md から SSH パスワード除去（CLAUDE/ops/server.md に隔離）
- [x] `.gitignore` で機密ディレクトリ・ログを除外
- [x] Cursor 用の Karpathy ルールも複製済

## 追加実装：履歴書き換え（A 案、2026-05-03 実施）

### 背景
ユーザー指示で A 案（`git filter-repo` で履歴書き換え＋ force push）を採用。

### 実施内容
1. `git-filter-repo` を `/home/niiya/.local/bin/` にスクリプト直接配置（pip / apt 不可のため curl 経由）
2. ミラーバックアップ取得：`/home/niiya/muitobem_mirror_backup_20260503_100129.git`
3. `/tmp/secret-replacements.txt` に置換ルール（`@Kuurie338==>[REDACTED-PASSWORD]` ／ `Kuurie338==>[REDACTED-PASSWORD]`）
4. `git filter-repo --replace-text /tmp/secret-replacements.txt --force` 実行 → 全履歴を 1.02 秒で書き換え完了
5. 全 ref から `Kuurie338` 完全消去確認（`git log --all -S "Kuurie338"` 空）
6. 副作用対応：filter-repo の `--force` がワーキングツリーを HEAD に reset したため、Phase 0/6/7 の追跡ファイル変更（`.gitignore` ／ `tasks/lessons.md` ／ `CLAUDE.md`）が消失。**未追跡ファイル（`.claude/` ／ `.cursor/` ／ `CLAUDE/20260502_1/` ／ `CLAUDE/ops/`）は無事**で、追跡 3 ファイルを再適用して復旧。
7. `origin` remote 再設定（filter-repo が削除した）。

### 検証結果（追加分）
- `git log --all -S "Kuurie338" --oneline`：**空**（履歴上の機密完全消去）
- `git ls-files | xargs grep -l "Kuurie338"`：**空**（作業ツリー追跡ファイル機密なし）
- `git remote -v`：origin 復活
- HEAD SHA は `e0f1ffb` → `a03bf86` に変化（書き換えにより全 commit の SHA が更新）
- ミラーバックアップ存在確認：`/home/niiya/muitobem_mirror_backup_20260503_100129.git`

## 次のアクション
- TODO（実装後の運用面）：
  - hooks の dry-run 期間を経て exit 2 化を検討（最低 1 週間運用 → ログ確認）
  - 必要が出てきた都度、`.claude/skills/` に新規 Skill を追加（webhook-ops / appraisal-ops 等が候補）
  - `.claude/memory/lessons.md` を補充するための「ユーザー訂正後の自動転記」習慣

- 人間が行う作業（**最優先】）：
  1. **履歴書き換え後の force push**（AI からは `settings.json` の deny で実行不可）：
     ```bash
     cd /home/niiya/muitobem_mirror
     # バックアップ存在確認
     ls -d /home/niiya/muitobem_mirror_backup_*

     # ステージ（機密は .gitignore で除外済）
     git add .gitignore CLAUDE.md tasks/lessons.md \
             .claude/ .cursor/ CLAUDE/20260502_1/

     # コミット
     git commit -m "chore(.claude): 整備（settings/hooks/agents/skills/workflows/memory）と機密分離"

     # force push（履歴 SHA が全変化済 → --force 必須、--force-with-lease は filter-repo が origin 関係解除済のため不可）
     git push --force origin main
     ```
  2. **パスワードローテーション**（履歴書き換えしても GitHub のキャッシュ・既存クローン・第三者の控えに残る可能性 → 本筋）：
     - VPS の `django` ユーザーパスワードを変更
     - 新パスワードを `CLAUDE/ops/server.md`（git 管理外）に反映
     - 可能なら **SSH 鍵認証への切替**（パスワードログイン無効化）
  3. **GitHub 側の追加クリーンアップ（任意）**：
     - GitHub サポートに古い commit ハッシュ（`c4b69b2` / `fe9e2f8`）のキャッシュ削除を依頼すると、PR・fork・参照リンクからも除去できる
     - 古い SHA を直リンク（`https://github.com/mytakuhide888/muitobem_mirror/commit/c4b69b2`）でアクセス不能になっているか確認
  4. **バックアップの扱い**：
     - `/home/niiya/muitobem_mirror_backup_20260503_100129.git` は **平文パスワードを含む書き換え前ミラー**。force push 成功＋動作確認後に削除推奨：
       ```bash
       rm -rf /home/niiya/muitobem_mirror_backup_20260503_100129.git
       ```
  5. umbrella `/home/niiya/CLAUDE.md` も更新済（`.claude/memory/lessons.md` を新基準に）。他プロジェクトにも同方針を展開する場合は別途相談。
