# システム状況 / 運用メモ（muitobem）

## 1. 環境・起動
- ディレクトリ: `/srv/muitobem`
- .env: META_THREADS_* / META_IG_* / DB など設定済み（Threads長期トークン含む）
- コンテナ/サービス（docker compose -p muitobem）:
  - `django`（muitobem-django-1）
  - `scheduler`（muitobem-scheduler-1）
  - `db`（muitobem-db-1, MySQL 8.0, healthy）
  - `caddy`（muitobem-caddy-1, 80/443）
- 主なコマンド（/srv/muitobem で実行）:
  - 起動/再作成: `docker compose -p muitobem up -d --force-recreate`
  - 停止: `docker compose -p muitobem down`
  - ログ: `docker compose -p muitobem logs --tail=100 django`
  - コンテナに入る: `docker compose -p muitobem exec django bash`
  - Caddy が止まっている場合の起動: `docker compose -p muitobem up -d caddy`
  - 管理画面の「ログ」ページは settings.LOG_FILE（例: `/app/deploy/app.log`）を読む。ファイルが無い場合は空になるので、必要なら `docker compose -p muitobem logs` を併用。

## 2. 現在の稼働状態
- Threads API: `.env` の長期トークンで疎通済み。プロフィール取得・テキスト投稿OK。
  - テスト例（成功済み）: `ThreadsApiClient.post_text('12/7です お久しぶり')`
  - 設定確認: manage.py shell で `settings.THREADS_USER_ACCESS_TOKEN`, `THREADS_APP_ID`, `THREADS_APP_SECRET` が設定済み。
- Webアプリ/管理画面: `https://muitobem.top/admin/` で稼働。Caddyがフロント、Djangoは 8000/tcp で動作。
- scheduler: 60秒ごとに th_run_due_posts を実行する枠あり（Threads予約投稿）。実送信ロジックを実装済み（テキスト投稿のみ）。

## 3. 実装済み・できていること
- Threads:
  - APIクライアント実装（social/services/threads_api.py）：プロフィール取得、投稿/返信、スレッド/リプライ/インサイト取得、署名検証ヘルパー。
  - 予約投稿コマンド th_run_due_posts：APPROVEDなTHScheduledPostをThreadsに送信（テキストのみ）。
  - Webhook `/webhook/threads/`：Verify Token チェック＋署名検証（X-Hub-Signature-256, App Secret）。
- Instagram:
  - モデル/管理画面/統合Webhook（/webhook/meta/）あり。IG用環境変数は META_IG_* で統一。
- 環境変数整理:
  - Threads: `META_THREADS_APP_ID`, `META_THREADS_APP_SECRET`, `META_THREADS_ACCESS_TOKEN`, `META_THREADS_USER_ID`, `THREADS_API_BASE_URL`（settings で読み込み）。
  - IG: `META_IG_APP_ID`, `META_IG_APP_SECRET`, `META_IG_REDIRECT_URI`, `META_IG_BUSINESS_ID`, `META_IG_APP_ACCESS_TOKEN`。
  - Verify Token: `META_WEBHOOK_VERIFY_TOKEN`（統合）、`THREADS_WEBHOOK_VERIFY_TOKEN`、`VERIFY_TOKEN_IG`（個別IG用、必要なら）。
  - DB: MYSQL_* / DATABASE_URL。

## 4. これからの確認・残課題
- Threads:
  - Webhook疎通テスト（Meta側で callback/Verify Token/署名設定を合わせ、テスト送信で 200 を確認）。
  - 予約投稿（THScheduledPost）実送信の本番確認：SENT/FAILED 更新と Threads 側の投稿実在を確認。
  - 画像/動画投稿・メンション/返信イベントの処理拡張（現在はテキスト投稿中心、Webhook取り込みも最小）。
  - トークンの有効期限ウォッチ／必要なら更新フローの追加。
- Instagram:
  - 実API（投稿/DM/コメント返信/インサイト）の実装はスタブのまま。必要に応じて Graph API を実装する。
  - OAuth/長期トークン更新の自動化は未実装。必要なら meta_rotate_tokens などを整備。
- 運用:
  - `.env` を更新した場合は `docker compose -p muitobem up -d --force-recreate` で再作成する。
  - Webhook署名検証（Threads/IG）で使う Secret と Verify Token が Metaコンソール設定と一致しているか定期確認。

## 5. トラブルシュートのヒント
- 環境変数が設定に入っていない場合: コンテナを再作成（up --force-recreate）し、`env | grep META_THREADS` で確認。
- Threads API で 500/unknown: 短期トークンや user_id 不一致、スコープ不足の可能性。`debug_token` で検証。
- 予約投稿が送信されない: THScheduledPost の status/時刻、アカウントの user_id/access_token、scheduler ログを確認。
