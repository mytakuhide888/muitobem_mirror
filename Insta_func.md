# Instagram運用 現状調査まとめ

## できていること（コード上の実装）
- **データモデル/管理画面**  
  - Instagramビジネスアカウント、投稿、予約投稿、配信、DMスレッド/メッセージ、自動返信テンプレ/ルール、Webhookイベントがモデル化され、管理画面で閲覧・編集可能（`ig/models.py`, `ig/admin.py`, `social/admin.py`）。  
  - FacebookAccount と紐づけ（linked_facebook）や access_token 保存フィールドが用意されている。
- **Webhook受信**  
  - `/webhook/instagram/`（`social/views.py`）と `/webhook/meta/`（`app/console/views/webhooks.py` 統合エンドポイント）で POST 受信し、`social.WebhookEvent` / `ig.IGWebhookEvent` に保存する仕組みあり。  
  - `/webhook/meta/` は `X-Hub-Signature-256/sha1` を検証（App Secretベース、IG Secretも任意で使用可）し、署名OKなら `ig.services.webhook_handlers.ingest_instagram_messaging` で DM をDBへ保存する実装がある。
- **トークン解決ヘルパー**  
  - `social/services/auth.py#get_ig_creds` で InstagramAccount/FacebookAccount から page_id/ig_user_id/access_token を解決する補助関数あり。
  - Metaユーザトークン管理モデル `sns_core.MetaUserToken` あり（管理画面で保管可能）。
- **管理コマンド**  
  - `ig_webhook_subscribe`, `ig_webhook_check` など、Webhook購読状態確認/登録のためのコマンドがある（実API呼び出しは要実装/トークン設定依存）。  
  - `ig_autoreply_worker` は IGWebhookEvent を参照して自動返信する枠があるが、中で実送信処理を実装する必要あり。
- **画面/ユーティリティ**  
  - 管理画面の「アカウント連携」「権限チェック」「Webhook受信テスト」などのビューで InstagramBusinessAccount の一覧や疎通チェック枠がある（`app/console/views/accounts.py`, `views/permissions.py`, `views/api_ig.py` など）。  
  - `app/console/utils/meta.py` に InstagramBusinessAccount を取り込み・更新するユーティリティ枠がある。
- **予約投稿ジョブ枠**  
  - `th_run_due_posts` と同様、`social/management/commands/social_worker.py` にジョブ実行の枠があり、Instagram向けの Job (REPLY/PUBLISH/INSIGHT) を処理する想定。  
  - ただし実際の送信は `social.services.ig_api.send_dm` などスタブが呼ばれるだけ。

## まだ未実装/スタブの部分
- **実API呼び出しがスタブ**  
  - `social/services/instagram_api.py` は fetch/post をダミー値で返す。  
  - `ig/services/instagram_api.py` もロガー出力のみで外部APIには接続しない。  
  - `ig_autoreply_worker` も実際の送信処理を実装していない。
- **OAuth/長期トークンの自動更新フローが未実装**  
  - Metaユーザ/ページトークンの管理用モデルやヘルパーはあるが、実際の更新処理は書かれていない。  
  - `social/management/commands/meta_rotate_tokens.py` も枠のみで、実リクエストは未実装。
- **Webhook以外の検証/エラー処理が不足**  
  - `/webhook/instagram/` 側はシグネチャ検証なし、`/webhook/meta/` 側は署名検証あり。実運用では `/webhook/meta/` に統一し、App Secret を必須にした方が安全。
- **予約投稿/配信の実行処理がない**  
  - ジョブ実行枠はあるが実投稿・スケジューラ実行がスタブなので、APPROVEDな予約投稿があっても実送信はされない。

## Facebook/Instagram アプリとの連動と必要権限（推定）
- 環境変数・設定（`app/settings.py`）  
  - `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `META_IG_APP_ID`, `META_IG_APP_SECRET`, `META_IG_REDIRECT_URI`, `VERIFY_TOKEN_IG`, `DEFAULT_API_VERSION` など。  
  - Webhook Verify Token は `/webhook/meta/` または `/webhook/instagram/` と一致させる必要あり。
- 想定権限（Meta側設定）  
  - Instagram Graph API: `instagram_basic`, `instagram_manage_messages`, `instagram_manage_comments`（コメント返信を使う場合）, `pages_manage_metadata`, `pages_read_engagement`, `pages_show_list` など。  
  - Webhook: Instagram オブジェクトのサブスクリプション（messages/comments/mentions 等）、Verify Token 設定。  
  - 送信（DM/コメント返信/投稿）は長期ページトークン or IGユーザトークンが必要。
- 現状の利用可否  
  - コードはスタブのため、権限があっても実API連携は行われない。Webhookの署名検証は `/webhook/meta/` 経由なら可能。

## 運用面（ジョブ/cron）
- `scheduler` サービスは Threads側ジョブのみ常駐実行。Instagram用の自動ジョブは `social_worker --loop` を回す想定だが、compose で常駐させていない。  
  → 定期実行させたい場合は、`scheduler` に `python manage.py social_worker --loop` を追加するなどの構成変更が必要。  
  → さらに送信処理の実装がないため、追加しても実送信は行われない点に注意。

## 不足している設定/実装と対応策
1. **実API実装**  
   - `social/services/instagram_api.py` と `ig/services/instagram_api.py` に Graph API 呼び出しを実装（メディア投稿、DM送信、コメント返信、Insights取得など）。  
   - `ig_autoreply_worker` で返信送信を実装し、エラー時のリトライ/ログ出力を行う。
2. **OAuth & トークン更新フロー**  
- META_IG_APP_ID/SECRET とリダイレクトURIを使った認可フローを実装し、ページトークン・長期トークンを保存/更新。  
   - `meta_rotate_tokens.py` を実リクエストで動くようにし、cron的に回す（またはschedulerサービスに組み込む）。
3. **Webhookを `/webhook/meta/` に統一＆署名検証を必須に**  
   - App Secret を .env で設定し、`ALLOW_IG` を不要にする運用にしてセキュリティを確保。  
   - Meta開発者コンソールで Instagram オブジェクトのサブスクリプションを `/webhook/meta/` に設定、Verify Token を一致させる。
4. **自動ジョブの常駐化**  
   - compose の `scheduler` に `python manage.py social_worker --loop` を追加して、Instagramのジョブ（REPLY/PUBLISH/INSIGHT）を定期実行。  
   - 実送信処理が入った後、ログで成功/失敗を確認できるようにする。

## Meta側で追加調査すべき内容
- Instagram Graph API の利用設定が完了しているか（製品追加、アプリモード、審査の要否）。  
- 必要スコープ（上記）を発行できる状態か、テスター/ユーザーが適切に登録されているか。  
- Webhook サブスクリプション設定（コールバックURL/Verify Token）と署名方式の確認。  
- `.env` の App ID/Secret、リダイレクトURI が開発者コンソールの設定と一致しているか。  
- 長期トークン更新に必要な手順（FBページ紐付け、IGビジネスアカウントの確認）を満たしているか。

## まとめ
- モデル・管理画面・Webhook受信と署名検証（統合エンドポイント経由）は整っているが、実API呼び出し・トークン更新・自動実行がスタブのため、送信/取得は動かない。  
- 動かすには: ① API実装、② OAuth/長期トークン更新フロー、③ Webhook署名検証の統一、④ 自動ジョブ常駐化（`social_worker --loop`）、⑤ Meta側設定の整合確認。  
- 上記を満たせば、投稿/DM/コメント返信/Insights等の自動化が可能になる。

## 補足: 現状の .env と追加で検討すべき値
- 現在の .env には IG/FB 用の以下が設定済み:  
  - `META_APP_ID=1106433447971414`  
  - `META_APP_SECRET=7ac66669dbea483f2a79c8e89a20a772`  
  - `META_WEBHOOK_VERIFY_TOKEN=7ad70f25d94869bb32087215dd5a5d8669fced332b01e19dfca707a0d67b33b3`  
  - `META_OAUTH_REDIRECT_URI=https://muitobem.top/oauth/meta/callback/`  
  - `META_IG_APP_SECRET=adb3ea922bf80d9bfaede31e19772772`  
- Threads 用の変数は未設定なので、IG と混在させず別変数（例: `META_THREADS_*`）で分離すると安全（Threads_func.md 参照）。
- Instagram 側で追加検討:  
  - `META_IG_APP_ID` / `META_IG_APP_SECRET` / `META_IG_REDIRECT_URI` を `.env` に明示して、実装側で参照するように揃える。  
  - 長期トークン更新を自動化する場合は、更新バッチで使う App ID/Secret と対象のページ/IGビジネスIDを `.env` または DB に保存する。  
  - Webhookを `/webhook/meta/` に統一する場合、Verify Token と App Secret を必ず `.env` に揃える。

## 追加情報（tmp_img/instagram のキャプチャより）
- Facebookアプリ（インスタ投稿管理アプリ）
  - アプリID: `1106433447971414`  
  - プライバシーポリシー: `https://muitobem.top/hello/privacy/`  
  - 利用規約: `https://muitobem.top/hello/kiyaku/`  
  - ユーザーデータ削除URL: `https://muitobem.top/hello/delete_tejun/`
- Instagram側
  - InstagramアプリID: `24532460019678867`  
  - IGビジネスログイン リダイレクトURL: `https://muitobem.top/hello/ig/oauth/callback/`  
  - Instagram business_id: `3820031998295148`

### 追加/見直しを推奨する環境変数例（プレフィックスを META_IG_ に統一）
```
META_IG_APP_ID=24532460019678867
META_IG_APP_SECRET=adb3ea922bf80d9bfaede31e19772772
META_IG_REDIRECT_URI=https://muitobem.top/hello/ig/oauth/callback/
META_IG_BUSINESS_ID=3820031998295148
META_IG_APP_ACCESS_TOKEN=IGAFcoJH...（長期ページ/IGユーザトークン）
```
- Webhook用 Verify Token: `/webhook/instagram/` は `VERIFY_TOKEN_IG`、統合 `/webhook/meta/` は `META_WEBHOOK_VERIFY_TOKEN` を使うので、`VERIFY_TOKEN_IG` も `.env` に入れておくと個別エンドポイントの動作検証が容易。
- IGビジネスログインのリダイレクトURIがアプリ設定と一致しているか再確認する。
- 現在の `.env` では `VERIFY_TOKEN_IG` が未定義なので、個別 `/webhook/instagram/` を使う場合は追加を推奨（統合 `/webhook/meta/` だけなら不要）。

### Facebook/Meta アプリ側で更新すべき内容
- Instagram製品が追加され、上記リダイレクトURLが「有効な OAuth リダイレクトURI」に登録されているか確認。  
- Webhooksで Instagram オブジェクトがサブスクライブされ、コールバックURL/Verify Token が `.env` と一致しているか確認。  
- アプリのモード（開発/ライブ）とテスター登録を確認し、必要なスコープ（`instagram_basic`, `instagram_manage_messages`, `pages_manage_metadata`, など）を取得できる状態にする。  
- IG Business Account と Facebookページのリンクが正しく設定されているか（business_id = `3820031998295148` が想定通りか）。

### 実装面の次ステップ
- `.env` に META_IG_APP_ID/SECRET/REDIRECT_URI/BUSINESS_ID を設定し、コード（OAuth・トークン管理・Webhook検証）で参照できるようにする。  
- `/webhook/meta/` の署名検証に App Secret を使い、Instagram webhook もそちらに統一。  
- トークン取得/更新フローを実装し、取得トークンを DB に保存する処理を追加する。
