# lessons.md — 重要な学び（時系列）

高シグナル知見のみ。一般論や手順は書かない。
詳細手順は `.claude/skills/`、設計の全体像は `CLAUDE/project_overview.md`、生ログは `CLAUDE/<日付>_<連番>/summary.md` へ。

---

## 2026-02-24 — 複数プロジェクト混在環境での誤配置
- **学び**: `/home/niiya/` 配下に muitobem_mirror / muitobem-platform / netsea / sakura-ama-wowma / meta-dev.git が混在。直近の似た名前で誤って別ディレクトリに実装したことがあった。
- **回避**: 作業開始前に必ず対象プロジェクトのディレクトリを確認する。muitobem 関連は **`muitobem_mirror` がメインリポジトリ**。
- **再利用**: 似た名前のプロジェクトが並ぶ環境では「ユーザー指示の名称」と「実ディレクトリ」を最初に紐付ける。

## 2026-02-24 — git add 漏れで VPS デプロイ時 ModuleNotFoundError
- **学び**: ローカルで新規作成した `services/` 配下のファイルを `git add` し忘れ、VPS で `git pull` 後に import エラー。
- **回避**: 新規ファイル作成後は必ず `git status` で未追跡を確認。サービス層は他から import されるため漏れると即エラーになる。
- **適用**: `git add -A` は禁止（umbrella §0、機密混入防止）。**対象ファイルを明示的に指定する**ため、漏れチェックが特に重要。

## 2026-02-24 — urls.py と view の不整合
- **学び**: `urls.py` に URL 定義を追加したが、対応する view 関数を含めずコミット → 500 エラー。
- **回避**: `urls.py` 変更時は、参照先の view 関数が **同一コミット**に含まれるか確認する。

## 2026-02-24 — innerHTML は XSS リスク
- **学び**: テンプレートで `innerHTML` を使用し、セキュリティチェックで検出された。
- **回避**: ユーザー入力／API 応答を DOM に挿入する際は **`createElement` + `textContent`** を使う。`innerHTML` は禁止。
- **適用**: Threads / Instagram のテンプレートで API 応答を表示する箇所すべて。

## 2026-02-24 — `docker compose restart` は `.env` を再読み込みしない
- **学び**: `.env` に新環境変数を追加し `docker compose restart` で反映を試みたが、コンテナに変数が渡らなかった。
- **回避**: **`.env` 変更は `docker compose up -d`** を使う。`restart` は既存プロセス再起動のみ。
- **適用**: `vps-deploy` Skill の手順に組み込み済。

---

## 進行中作業の参照
状態スナップショット（現状ステータス・次アクション候補）は本ファイルに書かない。
- 全体像: `CLAUDE/project_overview.md`
- ロードマップ: `CLAUDE/buzz_feature_roadmap.md`
- セッション記録: `CLAUDE/<日付>_<連番>/summary.md`

本ファイルは「教訓」のみを蓄える。
