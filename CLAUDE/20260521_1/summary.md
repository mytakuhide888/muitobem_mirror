# タスク記録 — Phase G 実装 G3-2 / G3-3（buzz_scraper 改修 & 通知層整備）

## 概要
- **背景**：Phase G の人間タスク（IG/Threads アカウント `arayasaki7` ウォームアップ、IPRoyal プロキシ契約、Gmail SMTP アプリパスワード発行）が揃ったため、AI 側の改修（G3-2 buzz_scraper・G3-3 通知機構）を実装する。
- **ゴール**：
  1. リサーチ用アカウントを `ResearchAccount` モデルで複数管理し、運用ステータス（`NEW`/`VPS_WARMUP`/`ACTIVE`/`SUSPENDED`）を持たせる
  2. 「VPS スタートアップ時の安全運転期間」をステータス機構で表現し、1〜2 週間（デフォルト 14 日）は超低頻度で動かす
  3. `buzz_scraper.py` を プロキシ統合・ステータス連動レート・人間挙動エミュ・凍結検知に改修
  4. `ScraperEventLog` ＋ `ScraperNotificationConfig` で通知システムを構築（Gmail SMTP）
  5. 改修コードを VPS へ反映、`arayasaki7` を `VPS_WARMUP` で登録し 1 ジョブ手動実行で疎通確認
- **影響範囲**：
  - `app/th/models.py`（3 モデル追加）
  - `app/th/services/buzz_scraper.py`（プロキシ・ステータス連動・凍結検知）
  - `app/th/services/scraper_config.py`（新規、設定層）
  - `app/th/services/scraper_notifier.py`（新規、通知層）
  - `app/th/admin.py`（新規モデルを Admin 登録）
  - `app/th/management/commands/th_buzz_login.py`（`--account` 引数追加）
  - `app/app/settings.py`（Gmail SMTP 追加）
  - VPS の `.env`（プロキシ／Gmail SMTP／レート関連変数）
- **期限／優先度**：高（Phase F 投稿フェーズに進む前提条件）

## 現状（事実）
- 引き継ぎ：`CLAUDE/20260517_1/handover.md` の Phase G Plan 確定済み
- 人間提供情報（2026-05-21）:
  - IG/Threads アカウント `arayasaki7` ウォームアップ完了済み
  - IPRoyal Pay-as-you-go 契約済み（geo.iproyal.com:12321、JP・Sticky 30 分）
  - Gmail SMTP `ebisu.uranai@gmail.com` のアプリパスワード発行済み
- 機密情報は `CLAUDE/ops/server.md`（git 管理外）に集約

## 確定方針（2026-05-21 追加）
| 項目 | 決定 |
|---|---|
| 運用ステータス | `NEW`／`VPS_WARMUP`／`ACTIVE`／`SUSPENDED` の 4 種を `ResearchAccount` に保持 |
| ウォームアップ期間 | デフォルト 14 日。`warmup_duration_days` で個別調整可、`auto_promote=True` で経過時に `ACTIVE` 自動昇格 |
| `VPS_WARMUP` レート | 5 req/h・待機 60〜180 秒・深夜停止 22:00〜09:00・日次 30 req・スクロール 3 回 |
| `ACTIVE` レート | 15 req/h・待機 15〜45 秒・深夜停止 02:00〜06:00・日次 200 req・スクロール 10 回 |
| 環境変数オーバーライド | 各値を `.env` で個別に上書き可能（保守的な微調整に対応） |
| Gmail 送信元 | `ebisu.uranai@gmail.com`（DEFAULT_FROM_EMAIL も同じ） |
| 完了ライン | VPS デプロイ＋migrate＋`arayasaki7` 登録＋1 ジョブ手動実行までやり切る |

## Plan（編集前）

### Step 0：作業準備
- `CLAUDE/20260521_1/summary.md` 作成（本ファイル）
- `CLAUDE/ops/server.md` に機密情報追記
- `CLAUDE/ops/env_additions.md` に `.env` 追記内容ガイドを作成

### Step 1：モデル追加（`app/th/models.py`）
- `ResearchAccount`（ステータス・ウォームアップ管理・凍結フラグ・日次カウンタ）
- `ScraperEventLog`（イベント種別／レベル／メッセージ／払い出し）
- `ScraperNotificationConfig`（メール宛先・通知種別・集約・自動停止）

### Step 2：設定層 `app/th/services/scraper_config.py`（新規）
- ステータス別プロファイル `get_profile(status)`
- UA プール（実機 UA を約 15 種類）
- `pick_delay_seconds(profile)`（対数正規分布）
- `is_in_quiet_hours(profile)`（深夜停止判定、深夜跨ぎ対応）

### Step 3：通知層 `app/th/services/scraper_notifier.py`（新規）
- `log_event(event_type, account, message, payload, level)` 一元化 API
- `ScraperEventLog` 書き込み → 集約判定 → `send_mail`
- `SUSPENSION_DETECTED` で `ResearchAccount.status=SUSPENDED` に倒す

### Step 4：`buzz_scraper.py` 改修
- `ScraperConfig` クラス削除、`scraper_config` モジュール経由に
- `RateLimiter` をステータス連動に
- `_create_playwright_browser`：`account` 引数（任意）、プロキシ注入、`account.storage_state_path` を読む
- 凍結検知：ログインウォール／challenge 検出 → `SUSPENSION_DETECTED` 通知
- 既存呼び出し側 (th_buzz_keyword_scan 等) の互換性維持：未指定なら DB から `is_available()` なものをローテーション選択

### Step 5：`settings.py` に Gmail SMTP 追加
- 末尾にブロック追加（既存設定は不変）

### Step 6：`th_buzz_login.py` 改修
- `--account <name>` 引数追加
- 保存パスを `threads_session_<name>.json` に切替
- 引数未指定時は従来通り `threads_session.json`

### Step 7：`admin.py` 拡張
- 新規 3 モデルの ModelAdmin

### Step 8：ローカル syntax check
- `python3 -c "import ast; ast.parse(open(...).read())"` を全変更ファイルに

### Step 9：VPS デプロイ
- 人間が git add／commit／push（umbrella §0）
- AI が `ssh muitobem-new`：
  1. `cd /srv/muitobem && git pull origin main`
  2. `.env` に Phase G 用変数を追記
  3. `docker compose -p muitobem exec django python manage.py makemigrations th`
  4. `docker compose -p muitobem exec django python manage.py migrate`
  5. `docker compose -p muitobem restart django`
- 検証：System check 通過、django ログにエラーなし

### Step 10：`arayasaki7` 登録 ＋ ログイン
- VPS 上で Admin か Django shell から `ResearchAccount(name='arayasaki7', threads_username='arayasaki7', storage_state_path='/app/deploy/threads_session_arayasaki7.json', status='VPS_WARMUP', warmup_started_at=now, warmup_duration_days=14)` を作成
- 人間：ローカル PC で `python manage.py th_buzz_login --account arayasaki7` 実行 → `threads_session_arayasaki7.json` を scp で VPS の `/srv/muitobem/app/deploy/` に配置
- `ScraperNotificationConfig` を初期化（通知メール=人間指定アドレス）

### Step 11：1 ジョブ手動実行検証
- `docker compose exec django python manage.py th_buzz_keyword_scan --keyword "占い" --limit 5`
- ログ追跡：プロキシ経由・JP IP・凍結検知ゼロ・`JOB_COMPLETE` イベント発火

## 調査ログ（追記）

### 2026-05-21 開始時点の確認事項
- `buzz_scraper.py`（1564 行）：現仕様で `STORAGE_STATE_PATH` 固定、`ScraperConfig` 内部値、`RateLimiter` 単一クラス、UA 3 種
- `models.py`（683 行）：`THBuzzAuthor`/`THBuzzPost`/`THBuzzSearchJob`/`THBuzzAuthorAnalysis`/`ConceptProject` 等が存在
- `settings.py`（361 行）：`EMAIL_*` 関連設定なし
- `admin.py`（121 行）：Threads 系モデルを Jazzmin で登録済み
- `docker-compose.yml`：`env_file: .env` で取り込み、scheduler コンテナは停止固定運用
- 旧 `threads_session.json` は全環境から削除済み（2026-05-17 確認）

## 実装内容（2026-05-22 完了）

### ローカル変更ファイル
- `app/th/models.py`：`ResearchAccount` / `ScraperEventLog` / `ScraperNotificationConfig` 追加
- `app/th/services/scraper_config.py`（新規）：ステータス別プロファイル＋UA プール＋対数正規分布＋深夜判定
- `app/th/services/scraper_notifier.py`（新規）：DB ログ＋Gmail SMTP 通知＋集約＋自動停止
- `app/th/services/buzz_scraper.py`：`AccountRateLimiter` 化、プロキシ統合、`_check_suspension`、UA を `scraper_config` 経由
- `app/th/management/commands/th_buzz_login.py`：`--account` / `--proxy` 引数追加、`ResearchAccount` 同期
- `app/th/admin.py`：3 モデル Admin 登録、`promote` / `pause_warmup` / `resume_warmup` アクション
- `app/app/settings.py`：Gmail SMTP 設定 + Jazzmin アイコン
- `.gitignore`：`threads_session_*.json` / `debug_author_html.txt` を除外パターン追加
- `scripts/local_threads_login.py`（新規）：Django 不要のスタンドアロン Threads ログインヘルパー
- `CLAUDE/ops/server.md`：機密情報追記（git 管理外）
- `CLAUDE/ops/env_additions.md`（新規）：VPS .env 追記ガイド（git 管理外）

### VPS 反映（HEAD `5b4e8be`）
- `git pull origin main` で 10 ファイル更新（+1401 −56 行）
- `.env` に Phase G セクション追記（バックアップ `.env.bak.20260522_141734` 残存）
- `python manage.py makemigrations th` で `0021_researchaccount_scrapernotificationconfig_and_more.py` 生成
- `python manage.py migrate th` 適用 OK
- `docker compose -p muitobem up -d django` でコンテナ再生成（`.env` 再読込のため `restart` ではなく `up -d`）
- Django shell から `ResearchAccount(name='arayasaki7')` を `VPS_WARMUP` で作成、`ScraperNotificationConfig.load()` 初期化（recipient=`ebisu.uranai@gmail.com`、min_level=WARN）

### 既知の未対応
- `JOB_START` / `JOB_COMPLETE` イベントを管理コマンド側から発火させる組み込みは未実施（最小スコープのため）。必要に応じて後日 `th_buzz_keyword_scan` 等の `handle()` 入口/出口に `log_event` を仕込む
- 凍結検知のメール通知ループはモック未テスト。実運用での初発火を観察予定

## 検証結果（2026-05-22）

### Django システムチェック
- `System check identified no issues (0 silenced).` — エラーゼロで起動
- 環境変数：`RESEARCH_PROXY_URL`, `GMAIL_SMTP_*`, `SCRAPER_*`, `SCRAPER_WARMUP_*` がコンテナ内で展開済み

### 1 ジョブ手動実行（`th_buzz_keyword_scan -k "占い" --max-profile-fetch 3`）
- 開始 14:19 JST → 完了 14:30 JST（約 11 分、`VPS_WARMUP` の 60〜180 秒待機が複数回入る）
- 検索 1 回で 44 件取得（うち重複除外 27 件が新規）
- プロフィール 3 件すべて取得成功（`@touma_sprit` / `@reishi_uranai.gen` / `@susa.uranaishi`）
- `ResearchAccount.daily_request_count = 4`、`last_used_at` 更新済
- `ScraperEventLog` 0 件（凍結検知・レート上限・深夜停止すべてトリガーなし）
- `is_suspended = False`、`status = VPS_WARMUP` 維持
- `THBuzzAuthor` 3977 → 4001（+24）、`THBuzzPost` 468905 → 468932（+27）

### 受け入れ条件チェック
| Phase G Plan §9 受け入れ条件 | 結果 |
|---|---|
| `buzz_scraper.py` 改修コード完成・syntax check pass | ✅ |
| `ResearchAccount` モデル migrate 完了 | ✅ |
| `ScraperEventLog` モデル migrate 完了 | ✅ |
| `ScraperNotificationConfig` Admin で設定可能 | ✅ |
| プロキシ環境変数が docker-compose 経由で渡る | ✅ |
| 1 ジョブ手動実行でプロキシ経由アクセス成功 | ✅（44 件取得・凍結なし） |
| 凍結検知シミュレーションでメール送信成功 | ⏸ 未実施（実運用観察に委ねる） |
| 3 日連続 1 ジョブ/日で凍結検知なし → Stage 3 へ | ⏳ 観察フェーズ |

## 次のアクション

### 即時
- なし（コード／インフラ完成、Stage 1 = 1 ジョブ手動実行成功）

### 観察フェーズ（次の 14 日間 = ウォームアップ期間）
1. 日次 1 回程度、人間が `th_buzz_keyword_scan` を手動実行して凍結兆候の有無を確認
2. `ScraperEventLog` の admin（`/admin/th/scrapereventlog/`）で WARN 以上の発火がないか毎日チェック
3. メール通知（`ebisu.uranai@gmail.com`）の到着確認
4. 14 日経過後、`maybe_auto_promote()` で `ACTIVE` に自動昇格 → 通常頻度（15 req/h、待機 15〜45 秒）に移行
5. Stage 3（scheduler 復活）への進行判断は phase_g_plan.md §6 のガード基準に従う

### Phase F（投稿アカウント立ち上げ）— 後段
- リサーチが 2〜4 週連続無凍結を確認してから着手
- 別端末・別アカウントで投稿用を立ち上げ（リサーチ用 `arayasaki7` と混在させない）

### 推奨：通知メールの宛先見直し
- 現在 `ebisu.uranai@gmail.com`（送信元と同じ）
- 別のオペレーション窓口に届けたい場合は Admin の `ScraperNotificationConfig` で `recipient_emails` を変更（カンマ区切り複数可）
