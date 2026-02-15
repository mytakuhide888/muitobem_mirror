
# モバイルレスポンシブ・ナビゲーション実装計画

## 目標
ユーザーの要望に基づき、PC画面では表示されているがモバイル画面では（ブラウザ幅が狭いため）非表示になってしまっているトップメニューのリンクを、左サイドバー（アコーディオン形式）に追加してアクセス可能にする。

## 現状
- トップメニューのリンクは `settings.py` の `JAZZMIN_SETTINGS['topmenu_links']` で定義されている。
- これらのリンクは `base_site.html` の `#jazzy-navbar` でレンダリングされているが、モバイル画面ではレイアウト崩れ等の理由で実質的に使用できない。
- 左サイドバーは `custom_sidebar.html` でレンダリングされており、現在は `admin/nav_sidebar.html` をインクルードしているのみ。

## 提案する変更
**戦略: JSインジェクション**
`admin/nav_sidebar.html` は Jazzmin の内部テンプレートであり、編集が困難であるため、JavaScript を用いて動的にメニューを追加する。

1. `app/app/templates/admin/partials/custom_sidebar.html` を修正する。
2. `<script>` ブロックを追加し、以下の処理を行う:
   - DOM読み込み完了を待つ。
   - `ul.nav-sidebar` 要素を取得する。
   - その末尾に、新しいメニュー項目「コンソールメニュー」のHTML（Djangoテンプレートタグを含む）を挿入する。
   - アコーディオンの開閉動作を手動追加する（AdminLTEの初期化後に追加されるため）。
3. このメニューは AdminLTE の `nav-treeview` クラスを使用したアコーディオン形式とし、クリックすると展開してリンク一覧を表示する。

## リンク一覧
（`settings.py` より）
- [x] ダッシュボード: `console:index`
- [x] アカウント連携: `console:accounts`
- [x] 権限チェック: `console:permissions`
- [x] 投稿インポート: `social:post-import`
- [x] 投稿同期: `social:post-sync`
- [x] Webhook 受信テスト: `console:webhook_test`
- [x] Webhook イベント一覧: `console:webhook_events`
- [x] Webhook 設定: `console:webhook_setup`
- [x] セットアップ: `console:setup_env`
- [x] テンプレ一覧: `console:tpl_list`
- [x] テンプレ新規: `console:tpl_new`
- [x] テンプレ書出し: `console:tpl_export`
- [x] テンプレ読込: `console:tpl_import`
- [x] バズ投稿取得: `console:buzz_search`
- [x] 急成長ランキング: `console:buzz_growth_ranking`
- [x] 一括巡回: `console:buzz_keyword_scan`
- [x] トレンド分析: `console:buzz_trends`
- [x] 統合ガイド: `console:help`
- [x] ログ: `console:logs`
- [x] 接続テスト: `console:connection_test`

## 検証計画
- ブラウザサブエージェントを使用し、モバイルビューポート（例: 375x812）で管理画面にアクセスする。
- ハンバーガーメニューからサイドバーを開き、「コンソールメニュー」が追加されていることを確認する。
- アコーディオンを展開し、全てのリンクが表示されることを確認する。
- リンクをクリックし、正常に遷移できることを確認する。
