# タスク記録
## 概要
- 背景：キーワード検索・投稿取得時に低品質リプライ（絵文字のみ、短文、エンゲージメント0）が大量混入
- ゴール：低品質リプライを除外するフィルタ追加（デフォルトON、チェックボックスで切替）
- 影響範囲：buzz_scraper.py, 管理コマンド2件, views, テンプレート2件
- 期限/優先度：高

## Plan
- buzz_scraper.py: `_is_low_quality_reply()` 判定関数追加、search_keyword/fetch_author_posts に exclude_replies パラメータ
- th_buzz_search.py: --include-replies フラグ
- th_buzz_fetch_author.py: --include-replies フラグ
- views/buzz.py: POST パラメータ受取、コマンド引数反映
- buzz_search.html: チェックボックス（検索フォーム）
- buzz_author_detail.html: チェックボックス（投稿取得ボタン横）

## 実装内容
### 変更ファイル一覧

1. **app/th/services/buzz_scraper.py**
   - `_EMOJI_ONLY_RE`: 絵文字+記号+空白のみにマッチする正規表現
   - `_is_low_quality_reply(post_data)`: 低品質リプライ判定
     - 条件: `like_count==0 AND repost_count==0 AND (テキスト50文字以下 OR 絵文字のみ)`
   - `search_keyword()`: `exclude_replies` パラメータ追加（デフォルト True）、return 前にフィルタ適用、除外件数ログ出力
   - `fetch_author_posts()`: 同上

2. **app/th/management/commands/th_buzz_search.py**
   - `--include-replies` フラグ追加（指定時のみリプライ含む）
   - `scraper.search_keyword(kw, exclude_replies=...)` に渡す

3. **app/th/management/commands/th_buzz_fetch_author.py**
   - `--include-replies` フラグ追加
   - `scraper.fetch_author_posts(..., exclude_replies=...)` に渡す

4. **app/app/console/views/buzz.py**
   - `buzz_run_search()`: POST の `exclude_replies` を確認、未送信なら `--include-replies` をコマンドに追加
   - `buzz_fetch_author_posts()`: 同上

5. **app/app/console/templates/admin/console/buzz_search.html**
   - 検索フォーム内にチェックボックス「リプライを除外」追加（デフォルト checked）
   - `runSearch()` JS: checked なら `exclude_replies=1` を FormData に追加

6. **app/app/console/templates/admin/console/buzz_author_detail.html**
   - 「投稿文を取得」ボタン横にチェックボックス「リプライを除外」追加（デフォルト checked）
   - `fetchAuthorPosts()` JS: checked なら `exclude_replies=1` を FormData に追加

### データフロー
```
UI checkbox ON → POST exclude_replies=1 → view: コマンドにフラグなし → コマンド: exclude_replies=True → scraper: フィルタ適用
UI checkbox OFF → POST exclude_replies なし → view: --include-replies 追加 → コマンド: exclude_replies=False → scraper: フィルタなし
```

## 次のアクション
- 人間が行う作業:
  1. git add / commit / push
  2. Docker ビルド・デプロイ
  3. `/console/buzz-search/` でキーワード検索時にチェックボックス確認
  4. 投稿者詳細で「投稿文を取得」時にチェックボックス確認
  5. ログで「低品質リプライ除外: N件除外」が出ることを確認
