# タスク記録
## 概要
- 背景：インプレッション（表示回数）未取得のためスパイク指標・バイラルスコア計算不可
- ゴール：Phase 1 - スクレイパーでインプレッション抽出 + DB保存 + デバッグログ
- 影響範囲：buzz_scraper.py, th_buzz_search.py, th_buzz_fetch_author.py
- 期限/優先度：高

## 現状（事実）
- THBuzzPost.impressions フィールドはモデルに存在（IntegerField, nullable）
- スクレイパーの _parse_ssr_post() で impressions 未抽出
- 管理コマンドで impressions 未保存

## Plan
- _parse_ssr_post(): SSR JSON から view_count 等を試行抽出 + デバッグログ
- _extract_thread_items_from_html(): HTML の「万回表示」テキストからフォールバック
- 管理コマンド2件: impressions を DB に保存

## 実装内容
### 変更ファイル一覧

1. **app/th/services/buzz_scraper.py**
   - `_parse_view_count_text()` 関数追加: HTML テキスト「○○万回表示」「123K views」等 → int 変換
   - `_parse_ssr_post()`:
     - SSR JSON の post 直下から `view_count`, `play_count`, `impression_count`, `views`, `video_view_count` 等を試行
     - `text_post_app_info` 内からも同様に試行
     - デバッグログ: 最初の3投稿で post/tpai 内の全数値フィールドをログ出力（フィールド名特定用）
     - 戻り値に `impressions` を追加

2. **app/th/management/commands/th_buzz_search.py**
   - `imp = post_data.get('impressions')` で取得
   - 既存レコード更新時: `imp is not None` なら `existing.impressions = imp`
   - 新規作成時: `impressions=imp` を渡す

3. **app/th/management/commands/th_buzz_fetch_author.py**
   - 同上（更新時・新規作成時に impressions を保存）

### マイグレーション不要
- `impressions` フィールドは既存モデルに存在

## 次のアクション
- 人間が行う作業:
  1. git add / commit / push
  2. Docker ビルド・デプロイ
  3. 手動実行してログ確認:
     ```
     docker compose exec django truncate -s 0 /app/deploy/buzz_fetch_stderr.log
     docker compose exec django python manage.py th_buzz_fetch_author --username akaikarasu666 2>/dev/null
     docker compose exec django cat /app/deploy/buzz_fetch_stderr.log | grep "impressions候補"
     ```
  4. ログの `impressions候補 post数値:` を共有 → SSR JSON のどのフィールドに表示回数があるか特定
  5. 特定後 → Phase 2（spike_index, viral_score 計算・DB保存・管理画面表示）
