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

## 垢バン回避ルール（厳守）

2026-05-31 リサーチ用アカウント `arayasaki7` 凍結インシデント（詳細: [`CLAUDE/20260531_2/summary.md`](../../../CLAUDE/20260531_2/summary.md)）と外部有識者の知見をもとに策定。**Threads / Instagram いずれの実装・運用判断にも適用する**。レート上限・自動投稿・スクレイパ・noVNC 操作のすべてに影響する。

### 10 原則

| # | ルール | 実装/運用上の意味 |
|---|---|---|
| ① | **異変を感じたら 2 日は完全に休む**（表示回数1桁・投稿削除・ステータス警告は危険信号） | `ScraperEventLog` に `SUSPENSION_DETECTED` / `HTTP_403` / `HTTP_429` が出たら **当該 `ResearchAccount` を 48h 操作禁止**にする（自動 Cooldown フラグの導入を検討）。焦って再開しない |
| ② | **Instagram と連動していることを忘れない** | Threads の違反は Instagram 本体まで飛ぶ（Accounts Center 紐付け）。Threads 側の対策は IG 側にも適用する。両方で挙動を揃える |
| ③ | **AI 生成文をそのまま投稿しない** | `auto_post_generator.py` / `content_generator.py` の出力は **必ず人手 or 別工程で「自分の言葉・体験・感情の一文」を混ぜる**。完全 AI 文は Meta の AI 検知に引っかかる |
| ④ | **外部リンクを貼りすぎない** | 短縮 URL / LP 直リンクの連投は危険。1 投稿に複数リンクや、連続投稿でリンク多用は禁止。要所だけ |
| ⑤ | **NG ワードを連投しない** | 「稼ぐ・副業・LINE・無料・特典」の多用はリーチ激減＋警告対象。`ng_word_checker.py` に該当語の **連投検知**ロジックを足す。1 投稿に複数 NG 語を詰めない |
| ⑥ | **複数端末から同じアカウントに同時ログインしない** | 乗っ取り疑惑で一発アウト。`research-browser/`（VPS proxy 経由）とスマホ実機を同一アカウントで同時刻に触らない。チーム運用なら端末固定 |
| ⑦ | **同じ IP・同じ端末で複数アカ転生を繰り返さない** | 過去 BAN 垢の端末指紋・顔データが紐づくと連鎖 BAN。新規 `ResearchAccount` 作成時は **Chromium プロファイル `/srv/muitobem/research-browser-config/` を退避→新規プロファイル**から始める。IPRoyal セッション ID も変更 |
| ⑧ | **短時間の大量いいね・大量フォローをしない** | **フォローは 1 日 50〜100 以内、時間を分散**。`buzz_scraper.py` のレート上限を必ずこの範囲内にする。通知から秒で連打は Bot 確定 |
| ⑨ | **同じコメントを連続コピペしない** | 返信・コメントは 1 件ずつ言い回しを変える。テンプレ丸コピは即機械判定。`auto_reply_*` 系の生成も同一文連投を避ける乱択処理が必要 |
| ⑩ | **短時間に 10 投稿以上の連投をしない** | **投稿間隔は最低数十分〜数時間**。`th_run_due_posts` の予約投稿配信間隔の検証時にも遵守 |

### 設計レビュー時のチェックリスト
新機能・既存改修の Plan を出す際、以下が該当する場合は本ルールへの整合を確認する：
- 自動投稿 / 自動返信 / 自動フォロー / 自動いいね を追加・拡張する
- バズリサーチのレート上限（`BuzzRateLimiter` 等）を変える
- リサーチ用ブラウザ（`research-browser/`）の利用範囲を広げる
- AI 生成文を直接投稿フローに乗せる

### 既存実装との接点（要点）
- `app/th/services/buzz_scraper.py:51` `BuzzRateLimiter` — 状態別レート上限。⑧の数値根拠として再点検対象。
- `app/th/services/scraper_notifier.py:71` `SUSPENSION_DETECTED` 時の自動 SUSPENDED 化 — ①の 48h Cooldown を足す候補位置。
- `app/th/models.py:688` `ResearchAccount` — ⑥/⑦ の「運用モード」「Chromium プロファイル世代」フィールド追加候補。
- `app/th/services/ng_word_checker.py` — ⑤の「連投検知」を足す候補。

## 関連
- 機能仕様: [`Threads_func.md`](../../../Threads_func.md)
- 戦略: `CLAUDE/strategy/`（事業戦略・コンセプト設計ガイド）
- ロードマップ: `CLAUDE/buzz_feature_roadmap.md`
- 鑑定 v2: `CLAUDE/20260226_appraisal_v2/`
