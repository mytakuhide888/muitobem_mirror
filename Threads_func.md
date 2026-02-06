# Threads運用 現状調査まとめ

## できていること（コード上の実装）
- **データモデル**（`th/models.py`, `social/models.py`）  
  Threadsアカウント・投稿・予約投稿・DM・自動返信テンプレ/ルール・Webhookイベントなどのモデルと管理画面が定義済み。
- **管理画面への露出**  
  Django/Jazzminの管理サイトで上記モデルを閲覧/編集可能（`th/admin.py`, `social/admin.py`）。
- **Webhook受信エンドポイント**  
  `/webhook/threads/` にPOSTすると `social.models.WebhookEvent` にペイロードを保存（署名検証なし、処理も記録のみ）。
- **簡易ヘルス/プレースホルダービュー**（`th/urls.py`, `th/views.py`）  
  `/sns/th/...` 配下にダッシュボード等のプレースホルダーがあり、HTTP 200 を返すのみ。
- **予約投稿ジョブの枠**  
  `th/management/commands/th_run_due_posts.py` で「APPROVEDな予約投稿を送信する」というジョブ枠があり、docker-compose の `scheduler` サービスが 60 秒毎に実行する構成になっている。
- **Threads用トークン解決ヘルパー**（`social/services/auth.py`）  
  ThreadsApp / ThreadsAccount / FacebookAccount から access_token と app_id を引くスタブ関数 `get_threads_token` がある。
- **Threads APIクライアントのスタブ**（`social/services/threads_api.py`, `th/services/threads_api.py`）  
  fetch/post/reply 等の関数シグネチャはあるが、実API呼び出しはしておらず固定ダミー値を返す。

## まだ未実装・実行されない部分
- **実際の投稿/API呼び出しが無い**  
  `th_run_due_posts.py` の `_post_to_threads` は常に True を返すスタブで、実際の Threads API 呼び出し処理は未記述。`social/services/threads_api.py` も全てスタブ。
- **Threads向け OAuth/トークン取得フローが無い**  
  OAuth スコープ定義はある（`app/console/views/oauth.py` に `THREADS_SCOPES = ["threads_basic", "threads_content_publish", "threads_manage_replies"]`）が、Threads用の実トークン発行/保存処理は実装されていない。
- **Webhook検証/署名チェックなし**  
  `/webhook/threads/` は署名検証をせずにペイロードをそのまま保存するだけ。Metaの `X-Hub-Signature` 等の検証は未対応。
- **予約投稿の実行トリガーは枠のみ**  
  `scheduler` サービスが 60 秒ごとに `th_run_due_posts` を回しているが、実投稿処理がスタブなので何も送信されない。
- **メッセージ返信・DM処理も未実装**  
  DM/自動返信モデルはあるが、Threads向けの受信/送信ロジックは書かれていない。

## Facebook/Meta アプリとの連動状況
- **環境変数の用意はあるが未使用に近い**  
  `app/settings.py` に `TH_APP_ID`, `TH_APP_SECRET`, `DEFAULT_API_VERSION` などの設定があるものの、実コードでAPIコールに使われていない。  
  OAuth スコープ定義は前述のとおり存在するが、実フローが未実装。
- **必要になるであろう権限（コードから推測）**  
  - Threads: `threads_basic`, `threads_content_publish`, `threads_manage_replies`（`app/console/views/oauth.py` より）  
  - Webhook: Threads用のサブスクリプション設定が別途必要（コードでは未実装/未検証）。
- **現状の利用可否**  
  実API呼び出しがないため、Meta側の権限が適切でも送信/取得は行われない。権限を追加しても、コードを実装しない限り機能しない。

## 運用面での挙動（cron/ジョブなど）
- `docker-compose.yml` の `scheduler` サービスが 60 秒ごとに `python manage.py th_run_due_posts -v 2` を実行し、APPROVEDな `THScheduledPost` を処理する枠がある。  
  ただし `_post_to_threads` がスタブのため、現状はDBのステータス変更も送信ログ出力も行われない。
- 予約投稿を5分後に自動発火…といった運用は「ジョブ枠はあるが実働コードなし」という状態。

## 不足している設定・実装と解決策
1. **Threads API 実装**  
   - `th_run_due_posts.py` の `_post_to_threads` を実装し、Threads Graph API（または提供されているエンドポイント）で投稿を実行。  
   - `social/services/threads_api.py` のスタブを実装し、投稿/返信/取得を実APIに置き換える。
2. **トークン/OAuth フロー実装**  
   - `app/console/views/oauth.py` に Threads用の認可URL生成・コールバック処理・トークン保存（`th.ThreadsAccount` や `social.ThreadsAccount`）を追加。  
   - `THREADS_SCOPES` を実際の認可リクエストに乗せる。
3. **Webhook検証**  
   - `/webhook/threads/` で `X-Hub-Signature-256` 等の検証を実装し、許可されたアプリからのみ受け付ける。  
   - Webhookサブスクリプションの登録手順を Meta 開発者コンソール側で実施。
4. **権限/設定確認（Facebook/Meta アプリ側）**  
   - アプリに Threads 製品が追加されているか、上記スコープが許可される状態か（開発モード→ライブモード時の審査要否も確認）。  
   - Webhook のコールバックURL設定（`/webhook/threads/` または `/webhook/meta/` 等に合わせる）と Verify Token の一致を確認。
5. **ジョブの実働確認**  
   - 実投稿処理を実装後、`scheduler` サービスが正常に DB にアクセスできるか（.env の `MYSQL_*` が揃っているか）を確認し、ログに成功/失敗が出るようにする。

## 現状の .env と不足している Threads 用設定
- `.env` には Instagram/共通の `META_APP_ID`/`META_APP_SECRET`/`META_WEBHOOK_VERIFY_TOKEN` はあるが、Threads用のアプリ情報が未設定。  
- ユーザー提供の Threads アプリ情報（「スレッズデータ取得アプリ」）  
  - Threads アプリID: `780871534595691`  
  - Threads アプリシークレット: `3c47450099fb81fca19d1ff0c8197824`  
  - Callback: `https://muitobem.top/hello/meta_callback`  
  - Webhook callback: `https://muitobem.top/hello/webhook/threads_callback`  
  - Verify token: `uranai-verify-token-123`  
  - ThreadsユーザID: `9841762272597036`  
  - 例示アクセストークン: `THAALGMtJvTmtBUVJtYnQydExZAWU1vbGhHY0x1ZAlVuSEp3ZA1lnbE5EaTRuUW42NVV3dExZAdFlPTmNjekYzSVlJVXdNN290ZAGV3cGZAjTlBoSk9rT1UwZA05KTDRZAOHlTRjNZAT1ZAuWWtWZAVNOMHowcVo1SkF1cVVNYzhHc2lUaFJJRElnMjBVZAV96UHZAyX0VSZAFEZD`

### 追加入力を推奨する環境変数（例）
- Threads 用に別変数を用意して分離管理する（既存の IG/FB と混在させない）。  
```
META_THREADS_APP_ID=780871534595691
META_THREADS_APP_SECRET=3c47450099fb81fca19d1ff0c8197824
META_THREADS_WEBHOOK_VERIFY_TOKEN=uranai-verify-token-123
META_THREADS_USER_ID=9841762272597036
META_THREADS_ACCESS_TOKEN=THAALGMtJvT...X0VSZAFEZD   # 実トークン
META_THREADS_WEBHOOK_URL=https://muitobem.top/hello/webhook/threads_callback
META_THREADS_OAUTH_REDIRECT_URI=https://muitobem.top/hello/meta_callback
```
- コード側で利用する際は、既存の `app/settings.py` とサービス層（OAuth/投稿/署名検証）でこれらを参照する処理を追加する。

### Facebook/Meta アプリ側で見直す点
- Threads 製品が追加済みか（Meta開発者コンソールで確認）。  
- 上記 callback / webhook URL をアプリ設定に登録し、Verify Token を一致させる。  
- 署名検証用に Threadsアプリの App Secret を `/webhook/threads/` または `/webhook/meta/` の検証処理に渡す。  
- 権限（threads_basic, threads_content_publish, threads_manage_replies）をリクエストできる状態か、テスター/ユーザーが登録されているかを確認。  
- 発行済みトークン（`META_THREADS_ACCESS_TOKEN`）が短期/長期か、失効期限の確認と更新手段を決める。

### 実装追加時の注意
- Secrets は `.env` のみに置き、リポジトリにコミットしない。  
- Webhook署名検証を必須化し、許可された App ID のみ受け付けるようにする。  
- OAuth/トークン保存処理を Threads 用にも実装し、`ThreadsAccount`/`ThreadsApp` に紐づけて管理する。

## Meta/Facebookアプリ側で追加調査すべき内容
- Threads API が有効化されているか（製品追加の有無、提供ステータス）。  
- 上記 Threads スコープ（`threads_basic`, `threads_content_publish`, `threads_manage_replies`）が取得可能か、審査が必要か。  
- Webhook のサブスクリプション設定（URL/Verify Token）と、送信元の署名仕様（`X-Hub-Signature-256` など）を確認。  
- App ID / App Secret / リダイレクトURI がコードの `.env` 設定と一致するか。

## まとめ
- **現状の機能はほぼスタブ**：モデルと管理画面、Webhook記録、ジョブの枠はあるが、実際の Threads API 呼び出し・OAuth・署名検証は未実装。  
- **動かしたい場合の最優先**：① OAuth/トークン取得の実装、② 投稿/返信APIの実装、③ Webhook署名検証、④ scheduler 内 `_post_to_threads` の実装。  
- **Meta側の確認**：Threads製品追加・必要スコープ・Webhook設定の有無を開発者コンソールで確認し、.env と突き合わせる。完成後に実APIで疎通テストを行う。
