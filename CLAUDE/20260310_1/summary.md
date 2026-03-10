# タスク記録
## 概要
- 背景：COMPLETEDプロジェクトがウィザード画面を表示してしまい、閲覧・編集ができない
- ゴール：COMPLETED専用の詳細画面を提供（MD閲覧/編集、参考アカウント管理、Threads紐付け、コンセプト再生成）
- 影響範囲：console アプリのビュー・テンプレート・URL・設定

## 実装内容
### 変更ファイル一覧
1. `app/app/console/views/concept_design.py` — COMPLETED分岐追加 + 3 API新規追加
2. `app/app/console/templates/admin/console/project_detail.html` — 新規作成
3. `app/app/console/urls.py` — 3パス追加
4. `app/app/settings.py` — JAZZMIN custom_links更新
5. `app/app/console/templates/admin/console/dashboard.html` — カード追加

## 検証結果
- Python構文チェック: 全ファイルOK

## 次のアクション
- git add/commit/push → VPSデプロイ → 動作確認
