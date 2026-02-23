# muitobem_mirror プロジェクト概要

## プロジェクト基本情報

**プロジェクト名**: muitobem_mirror
**目的**: Instagram/Threads API を用いた SNS 投稿管理プラットフォーム
**公開URL**: https://muitobem.top/admin/
**リポジトリ**: https://github.com/mytakuhide888/muitobem_mirror
**環境**: ConoHa VPS + Docker Compose
**管理者**: niiya

---

## 技術スタック

### バックエンド
- **言語**: Python 3.12
- **フレームワーク**: Django 5.2.4
- **データベース**: MySQL 8.0
- **リバースプロキシ**: Caddy 2（HTTPS対応）
- **タスク実行**: Celery（予定）、カスタムコマンド（現状）

### 主要ライブラリ
- **認証/API**: google-auth, gspread（Google Sheets連携）
- **スクレイピング**: beautifulsoup4, selenium, webdriver-manager
- **管理画面**: django-jazzmin（AdminLTE ベース、日本語対応）
- **その他**: mysqlclient, Pillow, requests, openpyxl

### インフラ構成（Docker Compose）
| サービス | 役割 | イメージ | ポート |
|---------|------|---------|--------|
| db | MySQL データベース | mysql:8.0 | 3306（内部） |
| django | Django アプリケーション | カスタム（Dockerfile） | 8000（内部） |
| caddy | HTTPS リバースプロキシ | caddy:2-alpine | 80, 443 |
| scheduler | 定期ジョブ実行（60秒間隔） | カスタム（Dockerfile） | - |

---

## ディレクトリ構造

```
/home/niiya/muitobem_mirror/
├── docker-compose.yml          # サービス定義
├── Caddyfile                   # リバースプロキシ設定
├── app/                        # Django プロジェクトルート
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/                    # Django 設定
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── console/            # 管理画面・ダッシュボード
│   ├── social_core/            # ベースモデル定義
│   ├── social/                 # SNS共通機能
│   ├── th/                     # Threads 専用アプリ
│   ├── ig/                     # Instagram 専用アプリ
│   ├── sns_core/               # メタユーザートークン管理
│   ├── webhooks/               # Webhook エンドポイント
│   ├── yaget/                  # 外部連携（WOWMA等）
│   └── templates/              # テンプレート
└── CLAUDE/                     # プロジェクト管理ディレクトリ
```

---

## データモデル構造

### ベースモデル（social_core/models.py）
- **BaseSocialAccount**: SNSアカウント基底クラス（トークン、有効期限管理）
- **BasePost**: 投稿基底クラス（外部ID、メディア、いいね数、インプレッション）
- **BaseScheduledPost**: 予約投稿基底クラス（タイトル、本文、ステータス）
- **BaseDMThread/BaseDMMessage**: DM管理基底クラス
- **BaseAutoReplyTemplate/Rule**: 自動返信基底クラス
- **BaseWebhookEvent**: Webhook イベント記録基底クラス

### Threads 実装（th/models.py）
- ThreadsAccount, THPost, THScheduledPost
- THDMThread, THDMMessage
- THAutoReplyTemplate, THAutoReplyRule
- THWebhookEvent

### Instagram 実装（ig/models.py）
- InstagramBusinessAccount, IGPost, IGScheduledPost
- IGBroadcast, IGDMThread, IGDMMessage
- IGAutoReplyTemplate, IGAutoReplyRule
- IGWebhookEvent

### 共通モデル（social/models.py）
- FacebookAccount, ThreadsApp, InstagramAccount
- ScheduledPost（Platform: THREADS/INSTAGRAM）

---

## 機能実装状況

### Threads（完成度: 80%）
| 機能 | 状態 | 備考 |
|------|------|------|
| OAuth認可フロー | △ | スコープ定義済み、実装は部分的 |
| テキスト投稿 | ✓ | threads_api.py で実装済み |
| 画像/動画投稿 | △ | 枠のみ |
| 予約投稿実行 | ✓ | th_run_due_posts（60秒間隔ジョブ） |
| プロフィール取得 | ✓ | get_profile() 実装済み |
| スレッド取得 | ✓ | get_threads() 実装済み |
| インサイト取得 | △ | get_insights() スタブ |
| Webhook 受信 | ✓ | 署名検証（X-Hub-Signature-256） |
| DM 送受信 | △ | モデル定義のみ |
| 自動返信 | △ | ルール定義済み、エンジン未実装 |
| トークン自動更新 | △ | meta_tokens.py 枠のみ |

### Instagram（完成度: 20%）
| 機能 | 状態 | 備考 |
|------|------|------|
| OAuth認可フロー | ✗ | 未実装 |
| 投稿（テキスト/画像） | ✗ | API実装がスタブ |
| 予約投稿実行 | △ | 枠のみ（ig_autoreply_worker） |
| DM 送受信 | ✗ | モデル定義のみ |
| インサイト取得 | ✗ | スタブ |
| Webhook 受信 | ✓ | /webhook/meta/ で署名検証済み |
| 自動返信 | △ | ルール定義済み、エンジン未実装 |

---

## API 連携詳細

### Threads API（実装済み）
**クライアント**: `app/social/services/threads_api.py`

**実装メソッド**:
- `post_text(text)`: テキスト投稿
- `get_profile()`: プロフィール取得
- `get_threads()`: スレッド一覧取得
- `get_insights()`: インサイト取得（スタブ）
- `verify_signature()`: Webhook 署名検証

**環境変数**:
```
META_THREADS_APP_ID=780871534595691
META_THREADS_APP_SECRET=3c47450099fb81fca19d1ff0c8197824
META_THREADS_USER_ID=9841762272597036
META_THREADS_ACCESS_TOKEN=THAALGMtJvT...（長期トークン）
THREADS_API_BASE_URL=https://graph.threads.net/v1.0
THREADS_WEBHOOK_VERIFY_TOKEN=uranai-verify-token-123
```

### Instagram API（未実装）
**クライアント**: `app/ig/services/instagram_api.py`（スタブ）

**スタブメソッド**:
- `fetch_posts()`: ダミー返却
- `publish_post()`: ダミー返却
- `send_dm()`: ダミー返却
- `get_insights()`: ダミー返却

**環境変数**:
```
META_IG_APP_ID=24532460019678867
META_IG_APP_SECRET=adb3ea922bf80d9bfaede31e19772772
META_IG_REDIRECT_URI=https://muitobem.top/hello/ig/oauth/callback/
META_IG_BUSINESS_ID=3820031998295148
```

---

## Webhook エンドポイント

| パス | 対象 | 署名検証 | 状態 |
|------|------|---------|------|
| `/webhook/threads/` | Threads | ✓（X-Hub-Signature-256） | 実装済み |
| `/webhook/instagram/` | Instagram | ✗ | 非推奨 |
| `/webhook/meta/` | Instagram/Facebook | ✓（X-Hub-Signature-256） | 実装済み（推奨） |

**検証トークン**:
- `META_WEBHOOK_VERIFY_TOKEN`: 統合用
- `THREADS_WEBHOOK_VERIFY_TOKEN`: Threads個別用
- `VERIFY_TOKEN_IG`: Instagram個別用

---

## デプロイメント

### 起動フロー
1. `docker compose -p muitobem up -d`
2. DB: MySQL 起動 → ヘルスチェック
3. Django: マイグレーション → collectstatic → runserver 0.0.0.0:8000
4. Scheduler: th_run_due_posts を 60秒ごと実行
5. Caddy: django:8000 へリバースプロキシ、/static/* はファイルサーバ

### ログ出力
- **Django**: `/app/deploy/app.log` + 標準出力（RotatingFileHandler: 2MB × 3）
- **Scheduler**: JSON ファイル（max-size: 10MB, max-file: 5）
- **Caddy**: 標準出力

### Static Files
- `STATIC_ROOT`: `/app/deploy`
- `STATIC_URL`: `/static/`
- Caddy で 7日間キャッシュ

---

## 管理画面（Jazzmin UI）

**アクセス**: https://muitobem.top/admin/

**主要メニュー**:
- ダッシュボード
- アカウント連携
- 権限チェック
- 投稿インポート/投稿同期
- Webhook 受信テスト/イベント一覧/設定
- セットアップ/テンプレート管理
- 統合ガイド/ログ/接続テスト

**モデル管理**: ig, social, th, auth の順で左ナビ表示

---

## 優先実装課題

### 1. Instagram Graph API 実装（高優先）
- `app/ig/services/instagram_api.py` を実装
- 投稿、DM、インサイト取得の実装

### 2. OAuth フロー実装
- `ig/views.py` で token_callback 処理
- アクセストークン取得・保存

### 3. トークン自動更新
- `meta_rotate_tokens.py` の実装
- 長期トークンのリフレッシュ処理

### 4. Threads 機能拡張
- 返信機能
- 画像/動画投稿
- インサイト取得の完全実装

### 5. スケジューラ拡張
- Instagram 予約投稿ジョブ追加
- 自動返信エンジンの実装

---

## セキュリティ設定

- **HTTPS**: Caddy による自動SSL/TLS
- **CSRF**: Trusted Origins 設定（muitobem.top）
- **Session**: HTTPS専用、7日間有効、SameSite=Lax
- **Webhook**: X-Hub-Signature-256 による署名検証

---

## 関連ドキュメント

- `Insta_func.md`: Instagram 現状調査
- `Threads_func.md`: Threads 現状調査
- `status.md`: システム稼働状況

---

## 更新履歴

- 2026-02-06: プロジェクト概要初版作成
