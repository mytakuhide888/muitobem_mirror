# タスク記録 — Phase G 実装完了（リサーチスクレイパ・VPS_WARMUP・通知・運用 UI）

> **このファイルだけで Phase G の全機能・運用方針が把握できるように構成しています。別チャット引き継ぎ用。**
> 関連: [phase_g_plan.md](phase_g_plan.md)（事前 Plan）、[handover.md](../20260517_1/handover.md)（前段引き継ぎ）

---

## 0. 全体サマリ（30 秒で把握する）

- **何をやったか**：旧 `uranai_tomori` 凍結を踏まえ、リサーチ用 Threads スクレイパを「複数アカウント対応・プロキシ経由・ステータス連動レート制限・凍結検知・通知層・運用 UI」付きで再構築。
- **新規アカウント**：`arayasaki7`（IG 起点 → Threads 派生、ウォームアップ済み）を `VPS_WARMUP` 14 日間で運用開始。
- **完了ライン**：コード改修＋VPS デプロイ＋migration＋1 ジョブ手動実行（44 件取得・凍結検知ゼロ）＋運用 UI（`/admin/console/buzz-research-overview/`）まで到達。
- **次にやること**：14 日間の観察フェーズ（日 1 回チェック）→ 自動 `ACTIVE` 昇格 → 2〜4 週連続無凍結確認後に Phase F（投稿）着手。

---

## 1. 背景・ゴール

### 背景
- 旧アカウント `uranai_tomori`（Threads）が凍結（恒久 BAN、確信度 95%）。原因は「ブラウザログイン経由スクレイピングの高頻度・同一 IP・人間挙動逸脱」。
- VPS は新 Xserver（`220.158.21.178`）に移行完了、`muitobem.top` も切替済（Phase E-2 完了）。
- Phase G として、リサーチ専用アカウント＋プロキシ経由スクレイピング機構を新設、安定確認後に Phase F（投稿）へ。

### ゴール
1. リサーチ用 Threads アカウントを凍結リスク最小で立ち上げ（複数体プール対応設計）
2. Outbound IP を VPS 生 IP からプロキシ経由に分離（IPRoyal Residential、JP 固定、Sticky 30 分）
3. `buzz_scraper.py` を 人間挙動エミュ＋頻度ガード＋凍結検知 に改修
4. 凍結検知時の通知機構（DB ログ＋管理画面で設定可能な Gmail SMTP メール通知）
5. 人間が `muitobem.top` で全運用できる UI 入口の整備

---

## 2. 確定方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| アカウント作成順 | IG 起点 → Threads 派生、新規 FB は作らない | Meta は FB/IG/Threads を Accounts Center で同一人物リンク。FB 経由でフラグ伝播。Plan §2.2 |
| 初期運用 | 1 体運用から開始（複数アカウント対応はモデル設計のみ） | 1 体凍結ノウハウ取得後に 2 体目作成、並行全滅リスク回避 |
| プロキシ | Residential 必須（DC NG）、IPRoyal Pay-as-you-go、JP・Sticky 10〜30 分 | Meta は IP の ASN で DC を判定して即 Bot フラグ |
| 改修順序 | (b) buzz_scraper 改修先行、並行で人間がアカウント＋プロキシ準備 | アカウント準備中に AI が実装完成させる |
| 通知方式 | DB ログ基本＋管理画面で指定したメールに重要通知 | 緊急停止トリガと履歴の両立 |
| Gmail SMTP | `ebisu.uranai@gmail.com`（アプリパスワード `wrcshpmmgzomyvjz`） | 凍結通知は 1 日数通レベル、500 通/日制限内 |
| ステータス機構 | `NEW` / `VPS_WARMUP` / `ACTIVE` / `SUSPENDED` の 4 値 | 「VPS 起動時の安全運転期間」を明示的に表現（2026-05-21 ユーザー追加要件） |
| ウォームアップ期間 | デフォルト 14 日、`auto_promote=True` で自動昇格 | 経過後に通常頻度（15 req/h）に移行 |
| scheduler | Phase G 安定確認まで起動しない（手動実行のみ） | 連鎖凍結回避 |
| 既存資産流用 | `THBuzzAuthor 3977` / `THBuzzPost 468905` をそのまま | 再キュレーション不要 |

### 設計原則（絶対遵守）
1. VPS 生 IP で Threads にアクセスしない（`RESEARCH_PROXY_URL` 未設定時は明示エラー）
2. 投稿アカウント（Phase F）とリサーチ用アカウントを混在させない
3. scheduler は安定確認まで起動しない
4. 新規 FB は作らない（IG → Threads 派生のみ）
5. Business アカウント化しない

---

## 3. アーキテクチャ全体図

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       muitobem.top (Caddy → Django)                       │
│                                                                            │
│  左サイドバー「企画 / リサーチ」                                          │
│   ├─ ◀NEW▶ バズ・人気アカウントリサーチ ← 運用入口（Overview）           │
│   ├─ コンセプト設計                                                       │
│   ├─ バズ投稿取得 / 急成長ランキング / 一括巡回 / トレンド分析            │
│   └─ ...                                                                  │
│                                                                            │
│  Overview ページから以下へ遷移:                                           │
│   ① buzz_keyword_scan（既存）→ Threads 巡回実行                          │
│   ② /admin/th/scrapereventlog/ → イベントログ確認                        │
│   ③ /admin/th/researchaccount/ → ステータス管理                          │
│   ④ /admin/th/scrapernotificationconfig/ → 通知設定                      │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (manage.py コマンド or 一括巡回 API)
┌──────────────────────────────────────────────────────────────────────────┐
│                       th_buzz_keyword_scan (等)                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ ThreadsBuzzScraper (app/th/services/buzz_scraper.py)                      │
│  ├─ __init__(account=None) — DB から is_available() なものを自動選択      │
│  ├─ maybe_auto_promote() — 14 日経過で VPS_WARMUP → ACTIVE                │
│  ├─ AccountRateLimiter(account) — ステータス連動レート制限                │
│  │    ├─ 深夜停止判定（QUIET_HOURS_ENTER 通知）                          │
│  │    ├─ 日次上限判定（DAILY_LIMIT_REACHED 通知）                        │
│  │    ├─ 時間上限判定（RATE_LIMIT_HIT 通知＋待機）                       │
│  │    ├─ 対数正規分布で待機                                              │
│  │    └─ daily_request_count / last_used_at 更新                          │
│  ├─ _create_playwright_browser(account, proxy_url, require_proxy)         │
│  │    ├─ RESEARCH_PROXY_URL 必須（未設定時 RuntimeError）                 │
│  │    ├─ ResearchAccount.storage_state_path から Cookie 読込              │
│  │    └─ scraper_config.pick_user_agent() で UA 約 15 種からランダム      │
│  └─ _check_suspension(url, html)                                          │
│       challenge/checkpoint URL or 凍結文言検出                            │
│       → SUSPENSION_DETECTED 通知 → ResearchAccount.status=SUSPENDED       │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ scraper_config.py — レートプロファイル＋UA プール                         │
│   VPS_WARMUP: 5 req/h, 60-180s 待機, 22:00-09:00 停止, 日次 30, スクロ 3   │
│   ACTIVE:     15 req/h, 15-45s 待機, 02:00-06:00 停止, 日次 200, スクロ 10│
│   全値が SCRAPER_(WARMUP_)* 環境変数でオーバーライド可能                   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ scraper_notifier.log_event(event_type, account, message, payload, level)  │
│   ├─ ScraperEventLog にレコード作成                                       │
│   ├─ SUSPENSION_DETECTED → account.status=SUSPENDED 自動化                │
│   └─ ScraperNotificationConfig 判定                                       │
│        ├─ enabled & recipient_emails 非空                                 │
│        ├─ event_type が notify_events に含まれる                          │
│        ├─ level >= min_level                                              │
│        └─ 集約: aggregate_window_min 内 aggregate_threshold 件未満ならスキップ│
│           → send_mail（Gmail SMTP smtp.gmail.com:587, TLS）              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 実装ファイル一覧（全て git 管理）

### 新規作成（コード）
| パス | 役割 |
|---|---|
| `app/th/services/scraper_config.py` | ステータス別レートプロファイル、UA プール、対数正規分布、深夜停止判定、`RESEARCH_PROXY_URL` 強制チェック |
| `app/th/services/scraper_notifier.py` | DB ログ書込／Gmail SMTP 通知／集約／自動停止 |
| `scripts/local_threads_login.py` | Django 不要のスタンドアロン Threads ログイン補助スクリプト（ローカル WSL/Win から実行用） |
| `app/app/console/templates/admin/console/buzz_research_overview.html` | 運用 Overview 画面（運用手順＋ステータスサマリ＋サブメニューカード＋イベント対応表） |
| `app/th/migrations/0021_researchaccount_scrapernotificationconfig_and_more.py` | 3 モデル分の migration（VPS で自動生成済み） |

### 変更（コード）
| パス | 変更内容 |
|---|---|
| `app/th/models.py` | `ResearchAccount` / `ScraperEventLog` / `ScraperNotificationConfig` 追加 |
| `app/th/services/buzz_scraper.py` | `ScraperConfig` 削除 → `scraper_config` モジュール経由。`AccountRateLimiter` 化、プロキシ統合、`_check_suspension`、凍結検知を `search_keyword`/`fetch_author_profile`/`fetch_author_posts` に組込、`check_session_validity(account=None)` |
| `app/th/management/commands/th_buzz_login.py` | `--account` / `--proxy` 引数追加、`threads_session_<name>.json` 保存、`ResearchAccount` 同期 |
| `app/th/admin.py` | 3 モデルの Admin、アクション（`promote_to_active`/`pause_warmup`/`resume_warmup`） |
| `app/app/settings.py` | Gmail SMTP ブロック追加（`EMAIL_BACKEND`/`EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/`DEFAULT_FROM_EMAIL`）、Jazzmin アイコン 3 件 |
| `app/app/console/urls.py` | `console:buzz_research_overview` ルート追加 |
| `app/app/console/views/buzz.py` | `buzz_research_overview` ビュー追加（ResearchAccount / ScraperEventLog / NotificationConfig をテンプレに渡す） |
| `app/templates/admin/partials/custom_sidebar.html` | 左サイドバー「企画 / リサーチ」最上位に「バズ・人気アカウントリサーチ」追加（コンセプト設計より上） |
| `.gitignore` | `threads_session_*.json`、`debug_author_html.txt` 除外パターン追加 |

### 新規作成（ドキュメント／機密）
| パス | git 管理 | 役割 |
|---|---|---|
| `CLAUDE/20260521_1/summary.md` | ✅ | 本ファイル |
| `CLAUDE/ops/server.md`（追記） | ❌（`.gitignore`） | SSH、IPRoyal、Gmail SMTP、arayasaki7 アカウント認証情報 |
| `CLAUDE/ops/env_additions.md` | ❌（`.gitignore`） | VPS `.env` 追記内容ガイド |

### 関連 commit
- `5b4e8be` `feat(th): Phase G - research scraper with VPS warmup status, proxy, notifications`
- `f7e3464` `feat(console): バズ・人気アカウントリサーチ Overview ページ追加`

---

## 5. データモデル

### `th.ResearchAccount`（テーブル: `meta_th_research_accounts`）
リサーチ専用 Threads アカウント。複数管理対応。

| フィールド | 型 | 用途 |
|---|---|---|
| `name` | CharField(64, unique) | 識別名（例: `arayasaki7`） |
| `threads_username` | CharField(128) | @username（表示用） |
| `storage_state_path` | CharField(256) | コンテナ内 Cookie ファイルパス（例: `/app/deploy/threads_session_arayasaki7.json`） |
| `status` | Choices | `NEW` / `VPS_WARMUP` / `ACTIVE` / `SUSPENDED` |
| `warmup_started_at` | DateTimeField | `VPS_WARMUP` 開始日時 |
| `warmup_duration_days` | IntegerField (default=14) | 期間経過で自動昇格 |
| `auto_promote` | BooleanField (default=True) | False なら手動昇格のみ |
| `suspended_at`/`suspended_reason` | | 凍結検知時自動セット |
| `last_used_at` / `daily_request_count` / `daily_count_reset_at` | | レートリミッタが自動更新 |
| `memo` | TextField | 運用メモ |

メソッド:
- `is_available()` → `VPS_WARMUP` or `ACTIVE` のみ True
- `days_in_warmup()` → 経過日数
- `maybe_auto_promote()` → 14 日経過 & auto_promote=True で `ACTIVE` 昇格、True/False 返却

### `th.ScraperEventLog`（テーブル: `meta_th_scraper_event_log`）
スクレイパ運用イベント。append-only、Admin は ReadOnly。

| フィールド | 型 |
|---|---|
| `account` | FK to ResearchAccount (null 可) |
| `event_type` | Choices（下表 §7 参照） |
| `level` | Choices: DEBUG/INFO/WARN/ERROR/CRITICAL |
| `message` | TextField (最大 1000 文字) |
| `payload` | JSONField |
| `notified` | BooleanField（メール通知済みフラグ） |
| `created_at` | DateTimeField (auto_now_add) |

### `th.ScraperNotificationConfig`（テーブル: `meta_th_scraper_notification_config`）
通知設定。pk=1 のシングルトン、`ScraperNotificationConfig.load()` で取得（初回は既定値で自動作成）。

| フィールド | 既定値 |
|---|---|
| `enabled` | True |
| `recipient_emails` | `ebisu.uranai@gmail.com`（カンマ区切りで複数可） |
| `notify_events` (JSON 配列) | `['LOGIN_FAILED','RATE_LIMIT_HIT','HTTP_403','HTTP_429','SUSPENSION_DETECTED','JOB_FAILED','PROXY_ERROR']` |
| `min_level` | `WARN` |
| `aggregate_window_min` | `30` |
| `aggregate_threshold` | `3` |
| `auto_stop_on_suspension` | True |

---

## 6. 環境変数（VPS `/srv/muitobem/.env` 末尾セクション）

```bash
# === Phase G: Research scraper ===
RESEARCH_PROXY_URL=http://mHewoPLDn532KvFi:G2LMyNGpuI8fiWtK_country-jp_city-amagasaki_session-fnrWpF0W_lifetime-30m@geo.iproyal.com:12321
IPROYAL_API_TOKEN=6867bd6f2fc4e7ebcf3b1ae2a74b7255d6791e59c7eb6ca0e691cee83e63

GMAIL_SMTP_USER=ebisu.uranai@gmail.com
GMAIL_SMTP_APP_PASSWORD=wrcshpmmgzomyvjz
SCRAPER_NOTIFY_EMAIL_FROM=ebisu.uranai@gmail.com

# レートプロファイル（ACTIVE = 通常稼働）
SCRAPER_REQUESTS_PER_HOUR=15
SCRAPER_MIN_DELAY_SEC=15
SCRAPER_MAX_DELAY_SEC=45
SCRAPER_QUIET_HOURS=02:00-06:00
SCRAPER_DAILY_LIMIT=200
SCRAPER_MAX_SCROLL_COUNT=10

# レートプロファイル（VPS_WARMUP = 1〜2週間の安全運転）
SCRAPER_WARMUP_REQUESTS_PER_HOUR=5
SCRAPER_WARMUP_MIN_DELAY_SEC=60
SCRAPER_WARMUP_MAX_DELAY_SEC=180
SCRAPER_WARMUP_QUIET_HOURS=22:00-09:00
SCRAPER_WARMUP_DAILY_LIMIT=30
SCRAPER_WARMUP_MAX_SCROLL_COUNT=3
```

- `.env` 変更後は **必ず `docker compose -p muitobem up -d django`**（restart では再読込されない、教訓）
- バックアップ: `/srv/muitobem/.env.bak.20260522_141734`

### コード側の既定値（環境変数未設定時）
`scraper_config.py` 内の `_profile_warmup()` / `_profile_active()` に書かれている値が既定値。上記 `.env` と同じ。

---

## 7. ScraperEventLog イベント種別と運用対応

| event_type | 既定レベル | 意味 | 必要な対応 |
|---|---|---|---|
| `LOGIN_SUCCESS` | INFO | ログイン成功 | 不要 |
| `LOGIN_FAILED` | WARN | Cookie 失効・認証エラー | `scripts/local_threads_login.py` を再実行 → `scp` で VPS 配置 |
| `RATE_LIMIT_HIT` | WARN | 時間あたり上限到達（自動待機後再開） | 頻発するなら `SCRAPER_REQUESTS_PER_HOUR` 引き下げ |
| `HTTP_403` | WARN | Threads から制限応答 | 頻度低下＋プロキシセッション切替待ち |
| `HTTP_429` | WARN | Threads から制限応答 | 同上 |
| `SUSPENSION_DETECTED` | CRITICAL | challenge/checkpoint/凍結 URL 検知 | 該当アカウントは自動 SUSPENDED。原因調査 → 別アカウント立ち上げ |
| `JOB_START` | INFO | 管理コマンド開始（※発火組込は最小スコープのため未実装） | — |
| `JOB_COMPLETE` | INFO | 管理コマンド正常終了（※同上、未実装） | — |
| `JOB_FAILED` | ERROR | 管理コマンド例外終了（※同上、未実装） | エラーメッセージ確認、再発防止 |
| `DAILY_LIMIT_REACHED` | INFO | 日次上限到達で当日終了 | 翌日自動リセット。継続到達なら上限引き上げ |
| `QUIET_HOURS_ENTER` | DEBUG | 深夜停止帯突入 | 正常動作。`SCRAPER_(WARMUP_)QUIET_HOURS` で調整可 |
| `PROXY_ERROR` | ERROR | プロキシ接続エラー | IPRoyal の残量・認証情報を確認 |
| `WARMUP_PROMOTED` | INFO | `VPS_WARMUP` → `ACTIVE` 自動昇格 | 記録のみ |

> 注: `JOB_*` イベントは Phase G では最小スコープのため発火点を組み込んでいません。各管理コマンド（`th_buzz_keyword_scan` 等）の `handle()` 入口/出口に `from th.services.scraper_notifier import log_event` を仕込むと有効化できます。

---

## 8. 運用 UI 構成

### 左サイドバー位置
```
Console
└─ 企画 / リサーチ
    ├─ バズ・人気アカウントリサーチ  ◀NEW▶
    ├─ コンセプト設計
    ├─ バズ投稿取得
    ├─ 急成長ランキング
    ├─ 一括巡回
    └─ トレンド分析
```

### `/admin/console/buzz-research-overview/`（新規）
- **URL 名**: `console:buzz_research_overview`
- **View**: `app/app/console/views/buzz.py::buzz_research_overview`
- **Template**: `app/app/console/templates/admin/console/buzz_research_overview.html`
- **構成**:
  - 📌 通常フェーズの運用手順（4 ステップ、頻度の目安）
  - 現在の状態サマリ（リサーチアカウント数／直近 24h WARN+ 件数／通知設定）
  - ResearchAccount テーブル（status / warmup / 日次カウンタ / 最終使用）
  - サブメニューカード × 4
  - 主要イベント対応表
  - 📎 観察フェーズ（1〜2 週間）の補足

### サブメニュー（カードから 1 クリック遷移）
| カード | 遷移先 | 用途 |
|---|---|---|
| ① バズキーワードスキャン | `console:buzz_keyword_scan` | キーワード入力→Threads 巡回実行 |
| ② スクレイピングログ | `/admin/th/scrapereventlog/` | イベント時系列確認、フィルタ |
| ③ リサーチ用アカウントの状態 | `/admin/th/researchaccount/` | ステータス管理、アクション |
| ④ 通知設定 | `/admin/th/scrapernotificationconfig/` | メール宛先・イベント種別・集約・自動停止 |

---

## 9. 運用ガイド

### 9.1 通常フェーズ（`ACTIVE`、ウォームアップ完了後）

| 頻度 | 操作 |
|---|---|
| 日 1〜3 回 | `バズ・人気アカウントリサーチ` → ①「バズキーワードスキャン」でキーワード（占い等）入力 → 「実行」ボタン |
| 日 1 回（朝） | Overview ページ上部「直近 24h の WARN+ イベント = 0 件」を確認、または ②「スクレイピングログ」を開いて WARN+ 直接確認 |
| 日 1 回 | ③「リサーチ用アカウントの状態」で `daily_request_count` / `status=ACTIVE` を確認 |
| 通知到着時 | Gmail（`ebisu.uranai@gmail.com`）で受信、メール本文 → Admin リンクで該当ログ参照 |

### 9.2 観察フェーズ（`VPS_WARMUP`、新規追加後 1〜2 週間）

| 頻度 | 操作 |
|---|---|
| 日 1 回のみ | ①「バズキーワードスキャン」を慎重に 1 回実行（複数回は控える） |
| 日 1 回 | ②「スクレイピングログ」で WARN+ 件数ゼロ確認 |
| 日 1 回 | ③ で `status=VPS_WARMUP` 維持、`is_suspended=False` 確認 |
| 異常時 | ③ で該当アカウントを即 `SUSPENDED` に。原因（プロキシ／頻度／UA）を見直し |

14 日経過後、次回 `ThreadsBuzzScraper()` 生成時に `maybe_auto_promote()` が走り `ACTIVE` に自動昇格。`WARMUP_PROMOTED` イベントがログに記録される。

### 9.3 新規リサーチアカウント追加手順（2 体目以降の参考）

1. **人間タスク**（端末・回線・電話番号・メアド完全分離）：
   - スマホで IG 新規登録（モバイル回線、Wi-Fi OFF）
   - 個人 IG として 2〜4 週ウォームアップ（5〜15 件フォロー、3〜5 投稿）
   - IG から Threads 派生（Accounts Center 経由）、Threads でも 1〜2 週ウォームアップ
2. **ローカル WSL**（要 Win11 + WSLg or X server）：
   ```bash
   cd /home/niiya/muitobem_mirror
   source .venv/bin/activate
   export RESEARCH_PROXY_URL='http://....@geo.iproyal.com:12321'
   python scripts/local_threads_login.py <新アカウント名>
   ```
   → `app/deploy/threads_session_<新アカウント名>.json` を生成
3. **scp で VPS へ転送**：
   ```bash
   scp app/deploy/threads_session_<新アカウント名>.json muitobem-new:/srv/muitobem/app/deploy/
   ```
4. **VPS で Django shell から `ResearchAccount` 作成**:
   ```python
   from django.utils import timezone
   from th.models import ResearchAccount
   ResearchAccount.objects.create(
       name='<新アカウント名>', threads_username='<同>',
       storage_state_path='/app/deploy/threads_session_<新アカウント名>.json',
       status=ResearchAccount.STATUS_VPS_WARMUP,
       warmup_started_at=timezone.now(),
       warmup_duration_days=14,
   )
   ```
5. Overview 画面で新アカウントが `VPS_WARMUP` で出現することを確認

### 9.4 緊急対応

| 状況 | 対応 |
|---|---|
| `SUSPENSION_DETECTED` 通知メール受信 | ③ ResearchAccount で該当行が `SUSPENDED` になっていることを確認。原因を調査（プロキシ品質／頻度／UA／時間帯）。回復見込みなら ③ の「SUSPENDED 解除（VPS_WARMUP で再開）」アクション、回復見込みなしなら別アカウント立ち上げ（§9.3） |
| 全アカウントが SUSPENDED | scheduler が起動していれば停止、`SCRAPER_WARMUP_*` を保守的に下げ、新規アカウント立ち上げ |
| 通知メールが届かない | ④ で `enabled=True`、`recipient_emails` 入力済み、`min_level` が低すぎないかを確認。Gmail 側でブロックされていないか迷惑メールフォルダも確認 |
| IPRoyal の残量切れ | `IPROYAL_API_TOKEN` で管理画面照会、または手動で IPRoyal ダッシュボード確認。`PROXY_ERROR` 連発が予兆 |
| ローカル WSL でブラウザが開かない | `echo "$WAYLAND_DISPLAY $DISPLAY"` 確認。Win11+WSLg なら自動、Win10 は VcXsrv 必要 |

---

## 10. VPS 状態（2026-05-22 時点）

```
VPS: 220.158.21.178 (Xserver, Ubuntu 26.04 LTS, SSH alias: muitobem-new)
HEAD: f7e3464 (5b4e8be Phase G core + f7e3464 Overview UI)
Containers: db / django / caddy 稼働中、scheduler は停止固定

/srv/muitobem/.env: Phase G セクション追記済（.env.bak.20260522_141734 にバックアップ）
/srv/muitobem/app/deploy/threads_session_arayasaki7.json: 25KB, django:django 0644
/srv/muitobem/app/deploy/ ディレクトリ: django:django 0775（書込み可、scp 受け入れ可）

DB:
  ResearchAccount: 1 件
    arayasaki7 / VPS_WARMUP / warmup_started_at=2026-05-22T14:19:06+09 / warmup_duration_days=14 / auto_promote=True
  ScraperNotificationConfig: 1 件 (pk=1, recipient=ebisu.uranai@gmail.com, min_level=WARN, auto_stop_on_suspension=True)
  ScraperEventLog: 0 件（凍結検知なし、WARN+ ゼロ）
  THBuzzAuthor: 4001 件 (Phase G 初回 +24)
  THBuzzPost: 468932 件 (Phase G 初回 +27)
```

---

## 11. 検証結果（2026-05-22）

### Django システムチェック
- `System check identified no issues (0 silenced).`
- コンテナ内環境変数: `RESEARCH_PROXY_URL` / `GMAIL_SMTP_*` / `SCRAPER_*` / `SCRAPER_WARMUP_*` すべて展開済み

### 1 ジョブ手動実行（`th_buzz_keyword_scan -k "占い" --max-profile-fetch 3`）
- 14:19〜14:30 JST（約 11 分、VPS_WARMUP の 60〜180s 待機が複数回）
- 検索 1 回: 44 件取得（重複除外 27 件が新規）
- プロフィール 3 件すべて取得成功（`@touma_sprit` / `@reishi_uranai.gen` / `@susa.uranaishi`）
- `daily_request_count = 4`
- `ScraperEventLog`: 0 件（凍結・レート・深夜すべてトリガーなし）

### 新規 UI HTTP 確認
- `https://muitobem.top/admin/console/buzz-research-overview/` → HTTP 200

### Phase G 受け入れ条件チェック（plan §9）
| 項目 | 結果 |
|---|---|
| `buzz_scraper.py` 改修コード完成・syntax check pass | ✅ |
| `ResearchAccount` モデル migrate 完了 | ✅ |
| `ScraperEventLog` モデル migrate 完了 | ✅ |
| `ScraperNotificationConfig` Admin で通知メール／イベント種別を設定可能 | ✅ |
| プロキシ環境変数が docker-compose 経由で django コンテナに渡る | ✅ |
| 1 ジョブ手動実行でプロキシ経由アクセス成功 | ✅（44 件取得、凍結なし） |
| 凍結検知シミュレーション → メール送信成功 | ⏸ 実運用観察に委譲 |
| 3 日連続 1 ジョブ/日で凍結検知なし → Stage 3 へ | ⏳ 観察フェーズ進行中 |

---

## 12. 既知の制限・宿題

### Phase G では実装していないもの
- `JOB_START` / `JOB_COMPLETE` / `JOB_FAILED` イベントの **発火点**（各管理コマンドの handle に組込みは未実施、必要なら後日 `log_event(...)` を仕込む）
- `ScraperEventLog` 90 日経過分の自動削除コマンド（テーブル肥大化対策、後日）
- IPRoyal 残量・コストの自動監視（`IPROYAL_API_TOKEN` は `.env` 投入済みだが API 呼出処理は未実装）
- 凍結検知のモックテスト（実運用での自然な初発火を観察する方針）

### Phase G 追加機能（2026-05-23 追加）
- **キーワード一括巡回画面に「プロフ取得上限」入力欄**（デフォルト 20）
- **投入直後にジョブ見積り表示**：総リクエスト数／推定所要時間／完了予想時刻／レート上限超過判定
  - 実装: `scraper_config.estimate_job()` ／ `buzz_run_keyword_scan` API レスポンス ／ `buzz_keyword_scan.html` の `renderEstimate()`
  - 計算式: `total_requests = num_keywords + max_profile_fetch`、`base = total × (avg_delay + 8s)`、`extra = ceil((total - rph) / rph) × 3600s`

#### 推奨投入値（VPS_WARMUP プロファイル、5 req/h）
| キーワード | プロフ取得上限 | 推定所要 | 備考 |
|---|---|---|---|
| 1 | 3 | **8 分** | 上限内、推奨 |
| 1 | 5 | 1h 12m | 60 分 sleep |
| 1 | 20（デフォ） | 4h 44m | 240 分 sleep |
| 3 | 10 | 2h 27m | 120 分 sleep |

#### 推奨投入値（ACTIVE プロファイル、15 req/h）
ウォームアップ完了後は `--max-profile-fetch 20` でも 25 分前後で完了。

### Phase G 修正履歴（2026-05-25 追加）
- **scrollHeight null クラッシュ修正**（job id=186 失敗時の対応）
  - Threads SPA の DOM 再構築タイミングで `document.body` が一瞬 null になり `Page.evaluate('document.body.scrollHeight')` で TypeError
  - `_safe_scroll_height()` / `_safe_scroll_to_bottom()` ヘルパー導入（`document.body || documentElement` のフォールバックチェーン）
  - `search_keyword` / `fetch_author_posts` のスクロールループを try-except で防御
  - `document.body.innerText` 取得も同様に防御
  - HEAD: `a1a87be`

### 操作上の注意：buzz-search 画面の 2 フォーム使い分け
| 用途 | フォーム | API |
|---|---|---|
| 特定アカウントのプロフィール＋過去投稿を直接取得 | 「アカウント名」（`buzz-usernames`） | `buzz_run_account_fetch` |
| キーワードを含む投稿を横断検索 | 「キーワード検索」 | `buzz_run_search` |

ユーザー名（例: `ran_uranai1018`）を取得したい場合は **「アカウント名」フォーム** を使うこと。キーワード検索フォームに入れると 0 件か少数しかヒットせず、SPA 再構築バグを踏みやすい（修正済みだが本来の用途ではない）。

### `auto_promote` トリガー仕様
- `ThreadsBuzzScraper.__init__()` で呼ばれる `maybe_auto_promote()` が唯一の昇格起点
- つまり 14 日経過しても、誰もスクレイパを起動しなければ `ACTIVE` には上がらない（実害なし、起動時に昇格する）
- 強制昇格したい場合: Admin 「ResearchAccount」→ 該当行選択 → アクション「選択行を ACTIVE に昇格」

### scheduler 復帰計画（Phase G 安定確認後）
- Stage 1: 1 ジョブ手動実行（完了）
- Stage 2: 数日間 1 日 1 ジョブ手動実行 → 観察フェーズで実施中
- Stage 3: scheduler 復活、低頻度（1 ジョブ/時間） — Stage 2 で 3 日以上連続成功時
- Stage 4: scheduler 通常頻度（日次パイプライン）— Stage 3 で 1 週間以上連続成功時
- Stage 5: Phase F（投稿アカウント立ち上げ）— Stage 4 で 2〜4 週連続無凍結時

---

## 13. 次のアクション

### 観察フェーズ（次の 14 日間）
- `https://muitobem.top/admin/console/buzz-research-overview/` を毎日開いてチェック
- 日 1 回程度、Overview の ①「バズキーワードスキャン」で巡回実行
- WARN+ イベントが出たらこのチャットか新規チャットで共有
- 14 日経過後、`ACTIVE` に自動昇格することを確認

### 何か変更したい場合
- ウォームアップ頻度をもっと絞る: VPS で `.env` の `SCRAPER_WARMUP_*` 編集 → `docker compose -p muitobem up -d django`
- ウォームアップ期間を短く: Admin の ResearchAccount で `warmup_duration_days` を変更
- 通知メールの宛先追加: Admin の ScraperNotificationConfig で `recipient_emails` をカンマ区切りで追記

### Phase F（投稿）着手の判断基準
- 観察フェーズで 2〜4 週連続無凍結（`ScraperEventLog` の SUSPENSION_DETECTED ゼロ、HTTP_403/429 WARN がほぼゼロ）を確認してから着手
- 別端末・別アカウントで投稿用を立ち上げ（リサーチ用 `arayasaki7` と混在禁止）

---

## 14. 別チャットでこの作業を継続する際の Hello

```
muitobem_mirror プロジェクトの Phase G 観察フェーズ中です。
CLAUDE/20260521_1/summary.md を読めば全機能・運用方針が把握できます。
現在の状況: <症状や知りたいこと>
```

---

## 15. 参考リンク

- 前段 Plan: [phase_g_plan.md](phase_g_plan.md)
- 引き継ぎ前ファイル: [../20260517_1/handover.md](../20260517_1/handover.md), [../20260517_1/summary.md](../20260517_1/summary.md)
- VPS 移行履歴: [../20260511_1/summary.md](../20260511_1/summary.md)
- 凍結対応ロードマップ: [../20260503_1/summary.md](../20260503_1/summary.md)
- バズ機能ロードマップ: [../buzz_feature_roadmap.md](../buzz_feature_roadmap.md)
- 機密情報: `CLAUDE/ops/server.md`（git 管理外、AI 読み取り可）
- `.env` 追記ガイド: `CLAUDE/ops/env_additions.md`（git 管理外）
- プロジェクト全体像: [../project_overview.md](../project_overview.md)
- 運用方針: [../20260208_2/operation_strategy.md](../20260208_2/operation_strategy.md)
