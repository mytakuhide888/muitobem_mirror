# タスク記録
## 概要
- 背景：Threadsキーワード検索で、デフォルトが時系列順ではない（関連度順？）
- ゴール：明示的に新しい投稿から順（時系列降順）で取得できるようにする
- 影響範囲：app/th/services/buzz_scraper.py
- 期限/優先度：未定 / 中

## 現状（事実）
- 再現手順：管理画面からキーワード検索を実行すると、結果が時系列順ではない
- 観測ログ/エラー：特になし（機能としては動作している）
- 期待動作：最新の投稿から順に取得されること

## Plan（編集前）

### 実装アプローチ（3段階）

#### Phase 1: URLパラメータ試行（最優先）
最もシンプルな方法として、URLパラメータで時系列順を指定できるか試す。

**変更内容**:
- `buzz_scraper.py` の `search_keyword()` 関数を修正
- 現在: `search?q={keyword}&serp_type=default`
- 変更案: `search?q={keyword}&serp_type=recent`
- または: `search?q={keyword}&filter=recent`

**メリット**: 最小の変更で済む、コード追加不要
**デメリット**: パラメータが機能しない可能性あり

#### Phase 2: Playwrightでフィルタタブをクリック（Phase 1失敗時）
ページ読み込み後に「Recent」タブを探してクリックする。

**変更内容**:
1. 検索ページにアクセス
2. 「Recent」「Latest」ボタンを探す（セレクタ: `text="Recent"`, `role=button` など）
3. 見つかったらクリック
4. ページ更新を待つ
5. 既存のスクロール・抽出ロジックを実行

**メリット**: UIの動作を忠実に再現、確実性が高い
**デメリット**: コード追加が必要、セレクタがUI変更で壊れる可能性

#### Phase 3: GraphQL APIパラメータ解析（Phase 2失敗時）
既存のAPI傍受機能を使ってGraphQLリクエストを解析し、ソートパラメータを特定。

**変更内容**:
1. デバッグモードでGraphQLリクエストボディを記録
2. ソート指定のパラメータを特定
3. 必要ならPlaywrightでGraphQL APIを直接呼び出す

**メリット**: 最も堅牢
**デメリット**: 実装が複雑、Meta側のAPI変更に依存

### 推奨アプローチ
**Phase 1 → Phase 2 の順で試す**

まずURLパラメータ変更（最小変更）を試し、結果が時系列順になるか検証。
ダメならPlaywrightでタブクリックを実装。

### 変更候補ファイル
- `app/th/services/buzz_scraper.py` (search_keyword関数: 595行目付近)

### 検証方法
1. **Phase 1 実装後の検証**:
   ```bash
   # ドライランで動作確認
   docker compose -p muitobem exec django python manage.py th_buzz_search -k "占い" --dry-run

   # 実際に検索実行
   docker compose -p muitobem exec django python manage.py th_buzz_search -k "占い"

   # DBで取得した投稿の日時を確認（最新順か？）
   docker compose -p muitobem exec django python manage.py shell
   >>> from th.models import THBuzzPost
   >>> posts = THBuzzPost.objects.filter(search_keywords__icontains='占い').order_by('-posted_at')[:10]
   >>> for p in posts: print(p.posted_at, p.text_content[:50])
   ```

2. **Phase 2 実装後の検証**:
   - 同様にDBの投稿日時を確認
   - さらに `/app/deploy/debug_scraper_html.txt` で「Recent」タブがクリックされたか確認

### ロールバック案
- 変更前のURL形式に戻す: `search?q={keyword}&serp_type=default`
- Phase 2の場合: タブクリックロジックをコメントアウト

### 影響/副作用の可能性
1. URLパラメータが無効な場合、エラーまたは空結果になる可能性（→ Phase 2へ）
2. 「Recent」タブのセレクタが見つからない場合、タイムアウトエラー（→ try-except で対処）
3. 時系列順のデータ量がTop順と異なる可能性（バズ判定に影響？）

## 調査ログ（追記）
### 2026-02-08: 現状確認
- 現在のURL: `https://www.threads.com/search?q={encoded}&serp_type=default`
- `serp_type=default` は関連度順と推測される
- Threadsの実際のUIパラメータを確認する必要あり

### 2026-02-08: ウェブ調査結果
**ソース**:
- [Threads Introduces Recent Tab for Chronological Search Results](https://web.swipeinsight.app/posts/threads-introduces-recent-tab-for-chronological-search-results)
- [Threads Adds Recent Filter for Search Results](https://www.socialmediatoday.com/news/threads-adds-recent-filter-search-results/716249/)
- [Threads Search Guide](https://newsletter.fullstackrecruiter.net/p/threads-search-guide-tips)

**発見事項**:
1. Threadsには「Recent」タブが存在する（時系列順）
2. UIでは検索時に「Top」と「Recent」を切り替え可能
3. 3点ボタン（⋮）をタップして表示されるメニューから選択
4. 選択した設定は記憶される（次回検索時も適用）
5. モバイルアプリでは利用可能、Web版では制限がある可能性

**課題**:
- URLパラメータの具体的な構文は公式ドキュメントに記載なし
- ThreadsはReact SPAのため、フィルタ切り替えがURL変更なしで行われる可能性
- GraphQL APIを使用している可能性が高い

### 2026-02-08: 技術的アプローチの検討
**アプローチ1: URLパラメータを試行**
- `serp_type=recent` を試す
- `filter=recent` を試す
- `sort=latest` を試す
- その他の一般的なパラメータ

**アプローチ2: Playwrightでフィルタタブをクリック**
- ページ読み込み後、「Recent」タブを探してクリック
- クリック後にGraphQL APIレスポンスを傍受（既存の_on_response機能を活用）
- この方式の方が確実

**アプローチ3: GraphQL APIを直接調査**
- 既存のAPI傍受機能で、検索時のGraphQLリクエストを解析
- リクエストボディに含まれるソートパラメータを特定

## 実装内容（追記）

### Phase 1: URLパラメータ試行（実装完了）

**変更ファイル**:
- `app/th/services/buzz_scraper.py` (595行目)

**変更内容**:
```python
# 変更前
search_url = f"{THREADS_BASE}/search?q={encoded}&serp_type=default"

# 変更後
search_url = f"{THREADS_BASE}/search?q={encoded}&serp_type=recent"
```

**変更概要**:
- 検索URLのクエリパラメータを `serp_type=default` から `serp_type=recent` に変更
- これにより、時系列順（新しい投稿順）での結果取得を試みる
- 最小変更（1行のみ）で実装

**影響/副作用の可能性**:
1. `serp_type=recent` がThreadsで有効なパラメータでない場合、デフォルト動作にフォールバック or エラーの可能性
2. 時系列順とTop順で取得される投稿の内容が異なる可能性（バズっていない最新投稿も含まれる）

## 検証結果（追記）

### 検証待ち

以下のコマンドで検証が必要:

```bash
# 1. Dockerコンテナを再起動（変更反映）
cd /srv/muitobem
docker compose -p muitobem restart django

# 2. テスト検索実行
docker compose -p muitobem exec django python manage.py th_buzz_search -k "占い"

# 3. 取得した投稿の日時を確認
docker compose -p muitobem exec django python manage.py shell
>>> from th.models import THBuzzPost
>>> from django.utils import timezone
>>> from datetime import timedelta
>>>
>>> # 今回の検索結果を取得
>>> recent_posts = THBuzzPost.objects.filter(
...     search_keywords__icontains='占い',
...     created_at__gte=timezone.now() - timedelta(minutes=10)
... ).order_by('-posted_at')[:20]
>>>
>>> # 投稿日時を確認（新しい順に並んでいるか？）
>>> for p in recent_posts:
...     print(f"{p.posted_at} | {p.author.username} | {p.text_content[:50]}")
>>>
>>> # 投稿日時の範囲を確認
>>> if recent_posts:
...     print(f"最新: {recent_posts.first().posted_at}")
...     print(f"最古: {recent_posts.last().posted_at}")
```

**期待結果**:
- 投稿が新しい順（降順）に並んでいること
- 最新の投稿が上位に来ること
- 過去のバズ投稿より最新の投稿が優先されること

**Phase 1 失敗の判定基準**:
- 投稿日時がランダム（時系列順ではない）
- エラーが発生する
- 取得件数が0件

→ その場合は Phase 2（Playwrightでタブクリック）へ進む

## 次のアクション

### TODO
1. [ ] Phase 1の検証（上記コマンドで実行）
2. [ ] 検証結果に応じて次のアクションを決定：
   - ✅ 成功 → 完了
   - ❌ 失敗 → Phase 2（Playwrightでタブクリック）実装
   - ⚠️ 部分的成功 → パラメータを変更して再試行（`filter=recent` など）

### 人間が行う作業
1. git add / commit / push（Phase 1の変更）
2. 本番環境で `docker compose -p muitobem restart django`
3. 検証コマンドを実行して結果を確認
4. 結果を共有（成功/失敗/部分的成功）

### 次回チャット時に報告してほしい内容
- Phase 1の検証結果（成功/失敗）
- 投稿日時の並び順（時系列順になっているか？）
- エラーログの有無
- 必要に応じてPhase 2の実装を依頼

