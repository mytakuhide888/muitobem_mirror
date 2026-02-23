# タスク記録
## 概要
- 背景：検索ジョブが RUNNING のまま完了にならない
- ゴール：ジョブステータスが確実に更新される仕組みにする
- 影響範囲：th_buzz_search.py, views/buzz.py
- 期限/優先度：高

## 現状（事実）
- 問題1: View が Popen の後に RUNNING を設定 → subprocess の COMPLETED/FAILED を上書きする可能性
- 問題2: コマンドの try ブロック外でクラッシュすると RUNNING のまま放置

## Plan
- th_buzz_search.py: try/finally で確実にステータス更新
- views/buzz.py: RUNNING 設定を Popen 前に移動、stale ジョブ自動検出

## 実装内容
### 変更ファイル一覧

1. **app/th/management/commands/th_buzz_search.py**
   - `try/except` → `try/except/finally` に変更
   - `finally` ブロック: `job.refresh_from_db()` → エラーなら FAILED、RUNNING のままなら COMPLETED に更新
   - `finally` 内も `try/except` で包み、ステータス更新自体の失敗もログ出力
   - `error_occurred` 変数でエラー状態を追跡

2. **app/app/console/views/buzz.py**
   - `job.status = 'RUNNING'` を `subprocess.Popen()` の**前**に移動（競合解消）
   - `timedelta` インポート追加
   - `buzz_search` ビュー: stale ジョブ検出ロジック追加
     - 30分以上 RUNNING のジョブを一括で FAILED に更新
     - 画面表示のたびにチェック → 既存の RUNNING 残りも次回アクセス時に自動解消

## 次のアクション
- 人間が行う作業:
  1. git add / commit / push
  2. Docker ビルド・デプロイ
  3. `/console/buzz-search/` を開く → 既存の RUNNING ジョブが FAILED に変わることを確認
  4. 新規検索実行 → 完了後に COMPLETED になることを確認
