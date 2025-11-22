# 連携ガイド（Facebook / Instagram / Threads）— はじめてでも迷わない手順書

> **対象者**: 初めて Meta 連携を設定する担当者  
> **ゴール**: Facebook/Instagram/Threads を muitobem サイトと正しく連携し、Webhook でイベントを受信できるようにする

---

## 0. 用語と前提
- **SITE_BASE**: あなたの公開URL。例: `https://muitobem.top`  
- **コールバックURL**（OAuthの戻り先）: `https://{SITE_BASE}/oauth/meta/callback/`  
- **Webhook Verify URL**: `https://{SITE_BASE}/oauth/meta/webhook/`（GET検証）  
- **Webhook Inbound URL**: `https://{SITE_BASE}/oauth/meta/webhook/inbound/`（POSTイベント）  
- **Verify Token**: 任意の長い文字列。**Meta側とサイト側(.env)で一致させる**  
- **必要スコープ（例）**:  
  `pages_show_list, instagram_basic, instagram_manage_messages, pages_manage_metadata, pages_read_engagement`  
  （運用内容により `instagram_manage_comments` など追加）

---

## 1. 全体の流れ（先に全体像を把握）
1) **Meta（Facebook開発者）側の準備**  
   アプリ作成 → 製品追加（Facebook Login / Instagram Graph API / Webhooks） → OAuth と Webhook を設定  
2) **muitobem サイト側の設定**  
   `.env` に各種キー・URLを設定、Django のホスト許可設定を入れて再起動  
3) **OAuth 実行 → Page/IG取り込み**  
   管理画面からログイン開始 → 同意 → コールバック画面で権限とページ確認 → 取り込み  
4) **Webhook の疎通確認**  
   GET Verify（hub.challenge）→ POST 署名付きでイベント送信テスト  
5) **運用開始**  
   受信ログを監視しながらテンプレ配信・自動応答などを運用

---

## 2. Meta（Facebook 開発者）コンソールでの設定（クリック場所を具体的に）

### 2-1. アプリを作成する
1. ブラウザで **Facebook for Developers** にアクセスし、右上の **[マイアプリ]** を開く  
2. **[アプリを作成]** → アプリの種類は **「ビジネス」** を推奨（Instagram Graph API を使うため）  
3. アプリ名・連絡先メールを入力 → **[アプリを作成]**  
4. 作成後、左メニューの **[設定] → [ベーシック]** を開き、以下を設定  
   - **アプリドメイン**: `muitobem.top`（SITE_BASE のドメイン）  
   - **プライバシーポリシーURL**（必要に応じて）  
   - **アプリアイコン**（任意）  
   - 右上の **[変更を保存]**

### 2-2. 製品を追加する（Facebook Login / Instagram Graph API / Webhooks）
1. 左メニュー **[製品]** → 画面下部 **[製品を追加]**  
2. **Facebook Login** の **[設定]** を押す  
3. 再度 **[製品を追加]** → **Instagram Graph API** を追加  
4. 再度 **[製品を追加]** → **Webhooks** を追加

### 2-3. Facebook Login の OAuth リダイレクトURIを登録する
1. 左メニュー **[製品] → [Facebook Login] → [設定]** を開く  
2. **有効な OAuth リダイレクト URI** に **`https://{SITE_BASE}/oauth/meta/callback/`** を追加  
3. **[変更を保存]**

> 補足: 開発中は「開発モード」のままでも OK。外部ユーザーを対象にする際は「ライブモード」化と権限審査が必要。

### 2-4. Webhooks でコールバックURLと Verify Token を登録する
1. 左メニュー **[製品] → [Webhooks]** を開く  
2. **[サブスクリプションを追加]** で **オブジェクト = Instagram** を選択  
3. ダイアログに以下を入力  
   - **コールバック URL**: `https://{SITE_BASE}/oauth/meta/webhook/`  
   - **検証トークン**: **Verify Token**（.env と同じ文字列）  
   - **フィールド**（必要に応じて選択）: 例）`messages`, `mentions`, `comments` など  
4. 同様に **オブジェクト = Page** も必要に応じて登録（Messenger連携等を使う場合）  
5. 保存後、**「テスト送信」**（送信ボタン）から疎通テストが可能

### 2-5. Instagram アカウントの前提確認（よく躓くポイント）
- Instagram は **プロアカウント（ビジネス/クリエイター）** に切替済みか？  
- **Facebook ページとリンク** されているか？（Facebook ページの設定 > 連携済みアカウント／または Instagram アプリの **アカウントセンター**）  
- これが未設定だと、**Page → IG Business Account** の解決ができず取り込みに失敗します

---

## 3. muitobem サイト側の設定（.env と Django）

### 3-1. .env（例）
```dotenv
SITE_BASE=https://muitobem.top
META_APP_ID=＜Facebook開発者のアプリID＞
META_APP_SECRET=＜Facebook開発者のアプリシークレット＞
META_WEBHOOK_VERIFY_TOKEN=＜Webhooksで設定した検証トークンと同じ＞

# 任意（指定時はこれが最優先）
META_OAUTH_REDIRECT_URI=https://muitobem.top/oauth/meta/callback/
```

### 3-2. Django の基本設定（settings.py）
- `ALLOWED_HOSTS = ["muitobem.top", "localhost", "127.0.0.1", "testserver"]`  
- `CSRF_TRUSTED_ORIGINS = ["https://muitobem.top"]`  
- プロキシ配下などでHTTPS終端する場合：  
  - `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO","https")`  
  - `USE_X_FORWARDED_HOST = True`

> 設定を変更したら **Docker 再起動** を忘れずに。

---

## 4. 実行：OAuth → 取り込み → Webhook検証

### 4-1. OAuth を開始
1. ブラウザで **`https://{SITE_BASE}/oauth/meta/start/`** を開く  
2. Facebook の同意画面が開くのでログイン＆許可  
3. コールバック **`/oauth/meta/callback/`** に戻り、**付与済み権限（granted）/ 未付与（declined）** と **ページ一覧** が表示されます

### 4-2. ページを取り込む（IG Business Account を登録）
1. コールバック画面で取り込みたい **Facebook ページ** を選ぶ  
2. 取り込み（POST）を実行 → バックエンドの `InstagramBusinessAccount` に **IGビジネスID** と **アクセストークン** が保存されます

> API で直接叩く場合（例）：
```bash
curl -X POST "https://{SITE_BASE}/oauth/meta/import/"   -H "Content-Type: application/json"   -d '{"page_id":"＜選択したPageのID＞","verify_token":"＜.envと同じ文字列＞"}'
```

### 4-3. Webhook の GET Verify（hub.challenge）を確認
```bash
curl -i "https://{SITE_BASE}/oauth/meta/webhook/?hub.mode=subscribe&hub.verify_token=＜.envの値＞&hub.challenge=12345"
# → HTTP/200 で "12345" が返ればOK
```

### 4-4. Webhook の POST 受信（署名検証あり）を確認
```bash
RAW='{"object":"instagram","entry":[{"id":"<PAGE_OR_IG_ID>","changes":[{"field":"messages","value":{"sample":"ok"}}]}]}'
SIG=$(printf '%s' "$RAW" | openssl dgst -sha256 -hmac "$META_APP_SECRET" -r | awk '{print $1}')

curl -i "https://{SITE_BASE}/oauth/meta/webhook/inbound/"   -H "X-Hub-Signature-256: sha256=$SIG"   -H "Content-Type: application/json"   -d "$RAW"
# → HTTP/200 {"ok": true}
```

---

## 5. 運用のコツ（毎日の点検）
- **受信ログの監視**: 403（署名不一致）や verify mismatch が出ていないか  
- **権限の失効チェック**: コールバック画面で declined が増えたら **再認可**（/oauth/meta/start/）  
- **アカウント追加**: 複数の Page/IG を取り込むときは、同じフローを繰り返す  
- **テンプレ＆自動応答**: 既存のコンソールUI（テンプレ編集・差し込みプレビュー）を活用

---

## 6. よくあるつまずきと対処
- **redirect_uri mismatch**  
  → Facebook Login の **有効な OAuth リダイレクト URI** に **`/oauth/meta/callback/`** を正確に登録  
- **verify_token mismatch**  
  → Webhooks の検証トークンと、サイト `.env` の `META_WEBHOOK_VERIFY_TOKEN` が一致しているか確認  
- **署名エラー 403**  
  → `X-Hub-Signature-256` の計算に **App Secret** を使っているか、**RAW本文**と一致しているか確認  
- **Page→IG解決が空**  
  → Instagram 側が **プロアカウント** かつ **Facebookページとリンク** されているか再確認（アカウントセンター）  
- **本番で他ユーザーに使わせたい**  
  → アプリを **ライブモード** にし、必要権限を **審査**。審査用の手順書・動画・テストアカウントを準備

---

## 7. 参照（muitobem 側のURL一覧・再掲）
- OAuth:  
  - `GET /oauth/meta/start/`  
  - `GET /oauth/meta/callback/`  
  - `POST /oauth/meta/import/`
- Webhooks:  
  - `GET /oauth/meta/webhook/`（Verify）  
  - `POST /oauth/meta/webhook/inbound/`（イベント受信）
