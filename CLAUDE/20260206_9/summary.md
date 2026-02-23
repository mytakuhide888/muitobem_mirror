# タスク記録
## 概要
- 背景：パスワード変更後の Cookie 再取得手順が煩雑（手動 SCP）
- ゴール：既存 threads_login.py に SCP 自動転送を追加
- 影響範囲：scripts/threads_login.py
- 期限/優先度：中

## 現状（事実）
- scripts/threads_login.py が既に存在（ブラウザ起動 → 手動ログイン → セッション保存）
- SCP は手動（スクリプト終了時にコマンドを表示するのみ）
- SSH 設定 `muitobem-vps` が ~/.ssh/config に設定済み

## Plan
- `--no-scp` フラグ追加（デフォルト SCP ON）
- `--scp-dest` オプション追加（デフォルト: muitobem-vps:/srv/muitobem/app/deploy/threads_session.json）
- subprocess.run で scp 実行、成功/失敗メッセージ表示

## 実装内容
### 変更ファイル一覧

1. **scripts/threads_login.py**
   - `--no-scp` フラグ: SCP スキップ
   - `--scp-dest` オプション: 転送先カスタマイズ
   - ログイン・セッション保存後に `scp` コマンドを自動実行
   - 転送失敗時は手動コマンドを表示

## 次のアクション
- 使い方:
  ```bash
  cd /home/niiya/muitobem_mirror
  python3 scripts/threads_login.py
  ```
- `--no-scp` でローカル保存のみも可能
