# SNS管理機能 概要

## 予約投稿
- 管理画面から作成し、「承認」するとスケジューラ対象になります。
- スケジューラ実行(スタブ): `python manage.py shell -c "from social_core.services.scheduler import dispatch_scheduled_posts; dispatch_scheduled_posts()"`

## 投稿データ取り込み
- 投稿一覧画面上部の「取り込む」「最新化する」ボタンから実行します。

## Webhook テスト
- `/webhook/threads/` や `/webhook/instagram/` に POST すると `WebhookEvent` が作成されます。

## .env サンプル

```
FACEBOOK_APP_ID=123
FACEBOOK_APP_SECRET=xxx
IG_APP_ID=123
IG_APP_SECRET=xxx
IG_REDIRECT_URI=https://example.com/ig/callback/
VERIFY_TOKEN_IG=test_token_ig
VERIFY_TOKEN_TH=test_token_th
TH_APP_ID=123
TH_APP_SECRET=xxx
DEFAULT_API_VERSION=v23.0
```

## Webhook 登録と検証
- Facebook/Instagram 管理画面で上記の Verify Token を設定し、
  コールバック URL に `/webhook/instagram/` を指定します。
- Threads 用も同様に `/webhook/threads/` と `VERIFY_TOKEN_TH` を利用します。

## Worker 起動
バックグラウンドジョブは以下のコマンドで処理されます。

```
python manage.py social_worker --loop
```

## 疑似 POST 例

```
curl -X POST http://localhost:8000/webhook/instagram/ \
  -H 'Content-Type: application/json' \
  -d '{"entry":[{"messaging":[{"sender":{"id":"u1"},"message":{"text":"hello"}}]}]}'
```

## スケジューラ
- 予約投稿や配信のディスパッチはスタブです: `python manage.py shell -c "from social_core.services.scheduler import dispatch_scheduled_posts, dispatch_broadcasts; dispatch_scheduled_posts(); dispatch_broadcasts()"`
