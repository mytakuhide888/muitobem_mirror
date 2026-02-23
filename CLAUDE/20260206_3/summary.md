# タスク記録
## 概要
- 背景：バズ投稿取得でスクロール後の追加データが取れない。参加日も取得したい。
- ゴール：(1)スクロール時のAPI応答を傍受して投稿データを取得 (2)プロフィールモーダルから参加日を取得
- 影響範囲：buzz_scraper.py, th_buzz_fetch_author.py, buzz_author_detail.html
- 期限/優先度：高

## 現状（事実）
- SSR JSON はスクロール後も更新されない → 初期ロード分のみ取得
- Threads はスクロール時に GraphQL API で追加データを取得している
- 参加日は「...」→「このプロフィールについて」モーダルに表示

## Plan（編集前）
- 原因仮説：`_extract_thread_items_from_html` が SSR JSON のみ対象
- 対策1：`page.on('response')` で API レスポンスを傍受
- 対策2：Playwright で UI 操作して参加日を取得
- 変更ファイル：buzz_scraper.py, th_buzz_fetch_author.py, buzz_author_detail.html

## 調査ログ
- SSR JSON はスクロール後不変確認
- Threads のモーダルUI フロー確認（画像3枚）

## 実装内容
### 変更ファイル一覧

1. **app/th/services/buzz_scraper.py**
   - `_sanitize()` 関数追加: サロゲート文字を安全にUTF-8変換
   - `_start_response_capture()`: `response.text()` → `response.body().decode('utf-8', errors='replace')` に変更
   - URL フィルタ拡張: `/api/` に加えて `/graphql` も対象
   - 全 `page.content()` / `page.title()` 呼び出しに `_sanitize()` 適用（6箇所+3箇所）
   - デバッグファイル書き込みに `errors='replace'` 追加
   - ログの `logger.debug` → `logger.warning` に変更（エラー可視化）
   - API レスポンス傍受、参加日取得、スクロール改善（前回追加分）

2. **app/app/console/templates/admin/console/buzz_author_detail.html**
   - author-stats に参加日表示を追加（`author.raw_json.joined_at`）

## 検証結果
- ローカルでコード確認のみ（実環境テストはデプロイ後）

## 次のアクション
- 人間が行う作業:
  1. git add / commit / push
  2. Docker ビルド・デプロイ
  3. ログ確認: `docker compose exec django cat /app/deploy/buzz_fetch_stderr.log`
  4. 期待: サロゲートエラーが出ない、API傍受ログが出る、参加日が表示される
