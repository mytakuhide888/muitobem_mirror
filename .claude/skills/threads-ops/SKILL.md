---
name: threads-ops
description: Threads（Meta API）の業務オペレーション（投稿・予約投稿・バズリサーチ巡回・スクレイピング・自動投稿生成・コンセプト分析・インサイト取得・NGワードチェック）を扱うときに使用。`th_buzz_*` / `th_run_due_posts` / `th_classify_fortune` 管理コマンド、`th/services/` 配下の各種サービス、`social/services/threads_api.py` をガイドする。「Threads」「スレッズ」「th_buzz」「予約投稿」「バズリサーチ」「コンセプト分析」「自動投稿生成」「fortune_classifier」のキーワードで発動。
---

# threads-ops

Threads 業務の能力単位。設計概要は [`CLAUDE/project_overview.md`](../../../CLAUDE/project_overview.md) を、機能仕様は [`Threads_func.md`](../../../Threads_func.md) を参照。

## いつ使うか
- Threads 投稿（即時／予約）を実装・確認したい
- バズリサーチ（他アカウント情報収集・分類）を回したい
- 自動投稿（参考投稿 AI リライト）を扱いたい
- コンセプト設計（ずらしコンセプト案生成）を扱いたい
- インサイト（インプレッション／いいね）を取得したい

## 主要モジュール

### サービス層
| ファイル | 役割 |
|---|---|
| `app/social/services/threads_api.py` | Threads API クライアント（共通基盤） |
| `app/social/services/post_importer.py` | 投稿取込 |
| `app/social/services/scheduler.py` | 予約投稿実行 |
| `app/social/services/meta_tokens.py` | Meta トークン管理 |
| `app/th/services/threads_api.py` | th アプリ用 API |
| `app/th/services/buzz_scraper.py` | バズリサーチ用スクレイパ |
| `app/th/services/fortune_classifier.py` | 占い系投稿分類 |
| `app/th/services/concept_analyzer.py` | コンセプト分析 |
| `app/th/services/auto_post_generator.py` | 自動投稿生成（参考投稿リライト） |
| `app/th/services/content_generator.py` | コンテンツ生成 |
| `app/th/services/ng_word_checker.py` | NG ワード／法令チェック |
| `app/th/services/post_insights_fetcher.py` | インサイト取得 |
| `app/th/services/similar_finder.py` | 類似アカウント発見 |
| `app/th/services/trend_analyzer.py` | トレンド分析 |

### 管理コマンド（`app/th/management/commands/`）
| コマンド | 用途 |
|---|---|
| `th_buzz_auto_pipeline` | バズ自動巡回パイプライン |
| `th_buzz_search` | キーワード検索 |
| `th_buzz_keyword_scan` | キーワードスキャン |
| `th_buzz_deep_scan` | 詳細スキャン |
| `th_buzz_fetch_author` | 著者情報取得 |
| `th_buzz_login` | ログイン |
| `th_buzz_run_scheduled` | スケジュール実行 |
| `th_buzz_update_avatars` | アバター更新 |
| `th_classify_fortune` | 占い系分類 |
| `th_run_due_posts` | 予約投稿実行 |

## 実行（VPS のみ）

### 予約投稿実行（手動トリガ）
```bash
docker compose -p muitobem exec django python manage.py th_run_due_posts
```

### バズリサーチ巡回
```bash
docker compose -p muitobem exec django python manage.py th_buzz_auto_pipeline
docker compose -p muitobem exec django python manage.py th_buzz_keyword_scan --keyword <KW>
docker compose -p muitobem exec django python manage.py th_buzz_deep_scan --author <username>
```

### 占い分類
```bash
docker compose -p muitobem exec django python manage.py th_classify_fortune
```

## モデル（`app/th/models.py`）
- `ThreadsAccount`: Threads アカウント
- `THPost` / `THScheduledPost`: 投稿／予約投稿
- `THDMThread` / `THDMMessage`: DM
- `THAutoReplyTemplate` / `THAutoReplyRule`: 自動返信
- `THWebhookEvent`: Webhook イベント
- `THBuzzAuthor` 系: バズリサーチ用著者情報
- `ConceptProject` / `ConceptProjectAuthor`: コンセプト設計プロジェクト
- `AppraisalCharacter` / `AppraisalTemplate`: 鑑定キャラ／テンプレ

## 制約・注意
- **Webhook 署名検証**: `webhooks/` で実装済。署名検証を外さない。
- **NG ワードチェック必須**: 全出力（投稿／DM／自動返信）に `ng_word_checker.py` を通す（事業戦略 第 11 章 法令遵守）。
- **innerHTML 禁止**: テンプレートで `createElement` + `textContent` を使う（教訓: XSS リスク）。
- **scheduler コンテナ**: 60 秒間隔で `th_run_due_posts` 等が走る → ログ追跡は `docker compose logs scheduler`。
- **完成度**: Threads は 80%（投稿実装済、予約投稿稼働中）。Instagram は 20%（[`instagram-ops`](../instagram-ops/SKILL.md)）。

## 関連
- 機能仕様: [`Threads_func.md`](../../../Threads_func.md)
- 戦略: `CLAUDE/strategy/`（事業戦略・コンセプト設計ガイド）
- ロードマップ: `CLAUDE/buzz_feature_roadmap.md`
- 鑑定 v2: `CLAUDE/20260226_appraisal_v2/`
