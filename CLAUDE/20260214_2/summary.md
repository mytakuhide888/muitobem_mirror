# タスク記録
## 概要
- 背景：ジョブ失敗時にエラー原因が不明。error_message に str(exception) しか保存されず traceback がない。UIの「失敗」はただのテキストで詳細を見る手段がない。buzz_fetch_author_posts はジョブレコードを作成しないため失敗追跡不可。
- ゴール：エラー詳細（traceback・エラー種別・対処法）をUI上で確認可能にする
- 影響範囲：モデル、管理コマンド4本、ビュー、テンプレート4画面
- 期限/優先度：高

## 現状（事実）
- エラー発生 → `str(exception)` のみ保存
- UI上の「失敗」は静的テキスト
- セッション切れ等の兆候は検出不可
- buzz_fetch_author_posts はジョブレコードなし

## Plan（編集前）
- 原因仮説：traceback未保存、UI未対応
- 変更候補ファイル：11ファイル
- ロールバック案：マイグレーション0012を削除、各ファイルをgit revert

## 実装内容

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `app/th/models.py` | `error_traceback` TextField フィールド追加 |
| `app/th/migrations/0012_thbuzzsearchjob_error_traceback.py` | 新規マイグレーション |
| `app/th/management/commands/th_buzz_search.py` | traceback保存 + セッション診断 |
| `app/th/management/commands/th_buzz_fetch_author.py` | 同上 |
| `app/th/management/commands/th_buzz_deep_scan.py` | 同上 |
| `app/th/management/commands/th_buzz_keyword_scan.py` | 同上 |
| `app/app/console/views/buzz.py` | `_classify_job_error()` ヘルパー, job_status拡張, fetch_author_posts ジョブ化 |
| `buzz_search.html` | エラー詳細モーダル + 失敗リンク化 |
| `buzz_keyword_scan.html` | エラー詳細モーダル + 失敗リンク化 |
| `buzz_growth_ranking.html` | 深掘りスキャン失敗時の詳細リンク + モーダル |
| `buzz_author_detail.html` | ジョブポーリング + エラー詳細モーダル |

### 変更概要
1. **モデル**: THBuzzSearchJob に `error_traceback` TextField追加
2. **管理コマンド4本**: 共通パターンで traceback保存 + セッション診断を追加
3. **ビュー**: `_classify_job_error()` でエラーを5種に分類。job_status APIが分類結果と対処法も返却。fetch_author_posts がジョブレコードを作成
4. **テンプレート**: 4画面すべてにエラー詳細モーダル追加。「失敗」がクリック可能リンクに

### 追加改修: タイムアウト延長 + 部分完了対応
5. **stale ジョブ判定**: 30分→3時間に延長。途中結果(result_count>0)がある場合は COMPLETED + 警告メッセージに
6. **逐次更新**: 4コマンドすべてで、キーワード/アカウント処理完了ごとに `job.result_count` を DB に逐次保存
7. **部分完了**: 4コマンドの finally で、エラー発生でも途中結果がある場合は COMPLETED（`部分完了（N件取得後にエラー）`）に

### 影響/副作用の可能性
1. buzz_fetch_author_posts が --job-id 経由で起動（1アカウント配列で動作同等）
2. 既存FAILEDジョブの error_traceback は空文字（想定通り）
3. 投稿データ自体はトランザクションなしで個別にDB保存されるため、ジョブがタイムアウトしても途中までの投稿データは常にDBに残っている

## 次のアクション
- 人間が行う作業:
  1. `python manage.py migrate th` でマイグレーション適用
  2. 動作確認
  3. git add / commit / push
