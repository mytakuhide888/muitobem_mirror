# プロジェクト状況・引き継ぎ資料 (2026-02-16)

## プロジェクト概要
Django Admin (Jazzmin theme) を使用した管理画面の改修プロジェクト。
直近では「モバイル表示時のナビゲーション改善」を行いました。

## 直近の作業内容：モバイルナビゲーション改修

### 課題
モバイルビュー（幅狭画面）において、Jazzminのトップメニュー（「ダッシュボード」「急成長ランキング」等）が表示されず、アクセスできない問題が発生していました。

### 対応策
JavaScript (`app/static/js/mobile_nav.js`) を用いて、サイドバー内に「コンソールメニュー」というアコーディオンメニューを動的に注入しました。

### 実装詳細（重要）
Jazzmin (AdminLTE v3) の既存動作との競合を避けるため、以下の特定の実装を行っています。次回修正時はこの経緯に注意してください。

1.  **ファイル構成**
    - `app/static/js/mobile_nav.js`: メニュー注入と制御ロジック
    - `app/app/settings.py`: `JAZZMIN_SETTINGS["custom_js"]` に上記スクリプトを追加

2.  **AdminLTEとの競合回避（重要）**
    - 当初、注入したメニューに `has-treeview` クラスを付与していましたが、AdminLTEの標準スクリプトがこれを検知し、「勝手にメニューを閉じる」「アニメーションが競合する」という問題が発生しました。
    - **解決策**: 注入する HTML から `has-treeview` クラスを**意図的に削除**しました。
    - 代わりに、jQuery の `slideToggle` を使用して、AdminLTEのものとそっくりなアニメーション（ゆっくり開閉）を自前で実装しています。
    - `mobile_nav.js` 内では `e.stopPropagation()` 等を使用し、イベントの二重発火を防いでいます。

### 確認方法
1.  **環境**
    - ローカル: `wsl.localhost/Ubuntu/home/niiya/muitobem_mirror`
    - サーバー: ssh 接続 (160.251.140.93)
    - URL: `https://muitobem.top/admin/`

2.  **デプロイ手順**
    ```bash
    # ローカルで変更後
    git add .
    git commit -m "msg"
    git push origin main
    
    # リモート反映
    sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 'cd /srv/muitobem && git pull origin main && docker compose exec django python manage.py collectstatic --noinput'
    ```

3.  **検証**
    - ブラウザの開発者ツールでスマホサイズ（375x812等）に設定。
    - サイドバーを開き、「コンソールメニュー」をクリック。
    - **正常な挙動**: メニューが下にスライドして開き、リンク一覧が表示される。勝手に閉じない。
    - **異常な挙動**: 一瞬開いてすぐ消える（AdminLTEとの競合再発の可能性あり）。

## 残タスク / 次のステップ
- [ ] **実機検証**: ブラウザ自動テストツールがAPIエラーで不安定だったため、実機（スマホ）での最終動作確認が必要です。
- [ ] **コードクリーンアップ**: `console` アプリ内の不要なテンプレートファイル等がもしあれば整理する（今回は `custom_sidebar.html` を削除済み）。

## 関連ドキュメント
- `docs/implementation_plan.md`: 実装計画の履歴
- `docs/walkthrough.md`: 検証結果と経緯詳細
