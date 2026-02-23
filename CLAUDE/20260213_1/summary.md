# タスク記録
## 概要
- 背景：バズ投稿取得画面（`/console/buzz-search/`）にはキーワード検索機能があるが、特定のThreadsアカウントを直接指定してプロフィール＋過去投稿を取得する手段がない
- ゴール：バズ投稿取得画面に「アカウント指定検索」の入力欄を追加し、ユーザー名を直接入力して即時実行/予約実行できるようにする
- 影響範囲：バズ投稿取得画面、ジョブ管理、スケジューラ
- 期限/優先度：通常

## 現状（事実）
- キーワード検索フォームのみ存在
- 投稿者詳細画面からは個別に「投稿文を取得」ボタンで取得可能だが、直接ユーザー名指定で一括取得はできない

## Plan（編集前）
- 原因仮説：機能未実装
- 変更候補ファイル：models.py, th_buzz_fetch_author.py, th_buzz_run_scheduled.py, views/buzz.py, urls.py, buzz_search.html, admin.py
- ロールバック案：変更をrevertすればOK（マイグレーション rollback含む）

## 実装内容（追記）
- 変更ファイル一覧：
  - `app/th/models.py` - THBuzzSearchJob に `job_type` フィールド追加（keyword/account）
  - `app/th/migrations/0006_thbuzzsearchjob_job_type.py` - マイグレーション新規作成
  - `app/th/management/commands/th_buzz_fetch_author.py` - `--job-id` 引数追加、複数アカウントループ処理、ジョブステータス追跡
  - `app/th/management/commands/th_buzz_run_scheduled.py` - `job_type` による起動コマンド分岐
  - `app/app/console/views/buzz.py` - `buzz_run_account_fetch` ビュー追加
  - `app/app/console/urls.py` - `api/buzz/run-account-fetch/` URL追加
  - `app/app/console/templates/admin/console/buzz_search.html` - アカウント入力フォーム追加、ジョブ種別列追加、`runAccountFetch()` JS関数追加、`pollJobStatus()` 汎用化
  - `app/th/admin.py` - `job_type` を list_display/list_filter に追加

- 変更概要：
  - モデルに `job_type` CharField を追加（default='keyword' で既存レコード互換）
  - `th_buzz_fetch_author` コマンドの既存ロジックを `_fetch_single_author()` メソッドに抽出し、`--job-id` 指定時は `job.keywords` からユーザー名リストを読み取りループ処理
  - スケジューラが `job_type == 'account'` のジョブを `th_buzz_fetch_author` コマンドで起動するよう分岐
  - テンプレートに「アカウント指定検索」セクション追加（テキストエリア、予約実行、リプライ除外オプション）
  - `pollJobStatus()` を `pollJobStatus(jobId, msgElId)` に汎用化して両方のフォームから共用

- 影響/副作用の可能性：
  - 既存のキーワード検索ジョブには `job_type='keyword'` がデフォルト設定されるため影響なし
  - `pollJobStatus()` の引数変更は既存の `runSearch()` 内の呼び出しも同時に更新済み

## 次のアクション
- 人間が行う作業：
  1. マイグレーション実行: `python manage.py migrate th`
  2. 動作確認
  3. git add/commit/push
