# タスク記録
## 概要
- 背景：予約実行（スケジュール）のバズ検索が必ず0件で完了する
- ゴール：予約実行でも即時実行と同様にデータ取得できるようにする
- 影響範囲：docker-compose.yml, th_buzz_run_scheduled.py
- 期限/優先度：高

## 現状（事実）
- 「すぐに実行」は正常にデータ取得できる
- 「予約実行」は処理が動くが取得件数が常に0件
- 同じキーワードで即時実行すると問題なく取得可能

## 調査ログ
- docker-compose.yml の volume マウントを比較
  - django: `./app/deploy:/app/deploy` → ホストのファイルが見える
  - scheduler: `static_volume:/app/deploy` → Docker名前付きボリューム（ホストと別）
- scheduler コンテナ内に `threads_session.json` が存在しない
- Playwright が未認証でアクセス → Threads 検索結果 0 件
- さらに `stdout/stderr=DEVNULL` でエラーが破棄されていたため気づけなかった

## 実装内容
### 変更ファイル一覧

1. **docker-compose.yml**
   - scheduler の volume: `static_volume:/app/deploy` → `./app/deploy:/app/deploy` に変更
   - これにより `threads_session.json` が scheduler コンテナからも参照可能に

2. **app/th/management/commands/th_buzz_run_scheduled.py**
   - `subprocess.DEVNULL` → ログファイル出力に変更（即時実行と同じ方式）
   - `deploy/buzz_search_stdout.log`, `deploy/buzz_search_stderr.log` に追記
   - `pathlib.Path` インポート追加

## 次のアクション
- 人間が行う作業:
  1. git add / commit / push
  2. `docker compose down && docker compose up -d --build`
  3. 予約実行でキーワード検索 → 指定時刻後にデータ取得されることを確認
  4. 万一失敗した場合は `deploy/buzz_search_stderr.log` でエラー内容を確認可能
