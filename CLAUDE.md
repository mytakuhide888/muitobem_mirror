# muitobem_mirror — システムの脳

占いコンテンツの SNS 自動化・収益化プラットフォーム。
Threads / Instagram の Meta API を用いてアカウント管理・投稿・スクレイピングを行う。
Django 5.2.4 + MySQL 8.0 + Docker Compose（4 コンテナ）構成、ConoHa VPS で稼働。

## メンタルモデル（リポジトリの読み方）
- **`CLAUDE.md`**（この場所）= システムの脳。薄く保つ。詳細は配下にリンク。
- **`.claude/memory/`** = 長期知能。教訓・パターン・回避策（高シグナルのみ）。
- **`.claude/skills/`** = 実行エンジン。再利用可能な能力単位（vps-deploy / docker-ops / threads-ops / instagram-ops / scheduler-ops）。
- **`.claude/agents/`** = 思考の分割。architect / coder / reviewer / optimizer。
- **`.claude/workflows/`** = 自動化レイヤー。Plan→Build→Review→Test→Ship の段取り。
- **`.claude/hooks/`** = 強制レイヤー。秘密漏えい遮断・構文検証・要約欠落検知（dry-run 中、ログ: `.claude/hooks/log/hooks.log`）。
- **`CLAUDE/ops/`** = 機密情報（SSH パスワード等、`.gitignore` 対象、AI は読み取り可）。
- **`CLAUDE/<YYYYMMDD>_<連番>/`** = チャット作業ログ（umbrella §1.2 規約）。教訓は `.claude/memory/lessons.md` に抽出。
- **`CLAUDE/project_overview.md`** = 技術概要（不変設計）。
- **`CLAUDE/strategy/`** = 事業戦略（全 12 章）。

## 実行ルール
1. **継承**: umbrella `/home/niiya/CLAUDE.md` ＋ Karpathy 4 原則（最優先）。詳細は umbrella §「Karpathy 4 原則」または `~/.claude/skills/karpathy-guidelines/SKILL.md` ／ `.cursor/rules/karpathy-guidelines.mdc`。
2. **Plan 先出し**: 非自明な変更（3+ ファイル・仕様影響・新機能・複数解釈あり）は Plan を提示し、承認後に実装。軽微な bug 修正（umbrella §6 自走の境界内）は Build から開始してよい。
3. **最小差分**: 変更行は要求にトレース可能であること（Karpathy #3）。
4. **記録**: セッション開始時に `CLAUDE/<YYYYMMDD>_<連番>/summary.md` を作成（umbrella テンプレ準拠）。
5. **git は人間**: add / commit / push / branch 操作は人間が実施。AI は `git pull` / `git status` / `git diff` / `git log` のみ。
6. **言語**: 計画・記録・コメントは日本語。
7. **ローカル制約**: WSL では Django 起動不可。`migrate` / `runserver` は VPS のみ。構文検証は `python3 -c "import ast; ast.parse(open('x.py').read())"`。
8. **機密**: SSH パスワード等は `CLAUDE/ops/server.md`（git 管理外）に集約。CLAUDE.md・docs に書かない。

## クイックリファレンス
| やりたいこと | 参照先 |
|---|---|
| 全体像・機能ステータス | `CLAUDE/project_overview.md` |
| 機能仕様（Threads / Instagram） | `Threads_func.md` ／ `Insta_func.md` |
| バズ機能ロードマップ | `CLAUDE/buzz_feature_roadmap.md` |
| 事業戦略（全 12 章） | `CLAUDE/strategy/fortune_business_strategy.md` |
| 運用方針 | `CLAUDE/20260208_2/operation_strategy.md` |
| 引き継ぎ資料 | `docs/handover_summary.md` |
| 参考資料（原文） | `docs/sankou/` ／ `CLAUDE/sankou/` |
| 教訓ログ | `.claude/memory/lessons.md` |
| VPS デプロイ手順 | `.claude/skills/vps-deploy/SKILL.md` |
| Docker 操作 | `.claude/skills/docker-ops/SKILL.md` |
| Threads 業務 | `.claude/skills/threads-ops/SKILL.md` |
| Instagram 業務 | `.claude/skills/instagram-ops/SKILL.md` |
| 定期ジョブ運用 | `.claude/skills/scheduler-ops/SKILL.md` |
| 役割別エージェント | `.claude/agents/{architect,coder,reviewer,optimizer}.md` |
| 自動化フロー | `.claude/workflows/plan-build-review-test-ship.md` |
| 機械的検証（Hook） | `.claude/hooks/`（dry-run 中、ログ: `.claude/hooks/log/hooks.log`）|
| **機密情報（SSH 接続・パスワード）** | **`CLAUDE/ops/server.md`（git 管理外、AI 読み取り可）** |
| Cursor ルール | `.cursor/rules/karpathy-guidelines.mdc`（`alwaysApply: true`）|
| 作業ログ（umbrella §1.2 規約） | `CLAUDE/<YYYYMMDD>_<連番>/summary.md` |

## アーキテクチャ要約

### コンテナ構成（Docker Compose / `-p muitobem`）
| サービス | 役割 |
|---|---|
| `django` | Django アプリ本体（Python 3.12 / Django 5.2.4） |
| `db` | MySQL 8.0 |
| `caddy` | HTTPS リバースプロキシ |
| `scheduler` | 定期ジョブ（60 秒間隔ループ＋ flock） |

### Django アプリ構成
| アプリ | 役割 | 完成度 |
|---|---|---|
| `th/` | Threads API 連携・バズリサーチ・コンセプト分析 | 80% |
| `ig/` | Instagram 機能 | 20% |
| `social/` | SNS 共通基盤（Threads API クライアント等） | — |
| `social_core/` | ベースモデル定義 | — |
| `sns_core/` | Meta トークン管理 | — |
| `webhooks/` | Webhook 受信（署名検証） | — |
| `app/console/` | カスタム管理画面 | — |

## プロジェクト固有の固定値
- ドメイン：https://muitobem.top/admin/
- リポジトリ：https://github.com/mytakuhide888/muitobem_mirror
- 本番アプリディレクトリ：`/srv/muitobem`
- テンプレート：Jazzmin の `base_site.html` を継承
- NG ワード・法令チェック：全出力に `th/services/ng_word_checker.py` を通す（事業戦略 第 11 章）
- 教訓：**innerHTML 禁止**（XSS）／ **`.env` 変更時は `up -d`**（restart は再読込しない）／ `git add -A` 禁止

## 現在の Phase
- Phase A 完了（投稿パターン分析・自動巡回パイプライン）
- Phase B 完了（fortune_classifier 改善・類似アカウント発見）
- 次の Phase は `CLAUDE/buzz_feature_roadmap.md` を参照
