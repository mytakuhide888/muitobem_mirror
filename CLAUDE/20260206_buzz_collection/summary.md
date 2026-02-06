# タスク記録

## 概要
- **背景**: Threads でバズっている投稿をキーワード検索でリサーチし、投稿内容・投稿者情報をDB管理したい
- **ゴール**: Playwright スクレイピングでバズ投稿を取得し、管理画面から検索・閲覧・分析できるようにする
- **影響範囲**:
  - Threads スクレイピング（Playwright + Chromium）
  - 新規モデル 3つ（THBuzzAuthor, THBuzzPost, THBuzzSearchJob）
  - 管理画面（バズ投稿取得画面、投稿者詳細画面）
  - Docker（Playwright 追加、scheduler 拡張）
- **期限/優先度**: 未定 / 高優先度

---

## 現状（事実）
- **再現手順**: 現在はバズ投稿を取得する機能が存在しない
- **観測ログ/エラー**: N/A（新規機能）
- **期待動作**:
  - 管理画面からキーワード指定で即時/予約検索実行
  - 検索結果をテーブル表示（ソート/フィルタ対応）
  - 投稿者プロフィールを別画面で閲覧
  - 投稿者の過去投稿を遡って取得

---

## Plan（承認済み）

### アプローチ
- Threads 公式 API では他人の公開投稿検索ができないため、Playwright でブラウザスクレイピング
- バズ判定: エンゲージメント率（フォロワー数に対するいいね/リプライ/リポスト比率）で判定
  - micro(〜1万): いいね500+/リプライ50+/ER5%+
  - mid(〜10万): いいね5000+/リプライ200+/ER3%+
  - macro(10万+): いいね50000+/リプライ1000+/ER2%+
- レート制限: 3〜8秒ランダム待機、1時間60リクエスト上限

### 変更候補ファイル → 実装完了
下記「実装内容」参照

---

## 調査ログ（追記）

### 2026-02-06: 初期調査
- プロジェクト構造を理解
- 既存の Selenium/Chromium が Docker に導入済み（Dockerfile）
- Playwright を新規追加する方針に決定
- 前回チャットの Playwright + stealth アプローチを採用

### 2026-02-06: 管理画面構造調査
- Jazzmin 管理画面の topmenu_links にメニュー追加方式を確認
- console アプリの views/urls/templates パターンを把握
- base.html の `{% block console_content %}` パターンに従う

---

## 実装内容（追記）

### 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `app/th/models.py` | 編集 | THBuzzAuthor, THBuzzPost, THBuzzSearchJob 3モデル追加 |
| `app/th/admin.py` | 編集 | 3モデルの Django Admin 登録 |
| `app/th/services/buzz_scraper.py` | **新規** | Playwright スクレイパー（検索/プロフィール/過去投稿取得） |
| `app/th/management/commands/th_buzz_search.py` | **新規** | キーワード検索コマンド |
| `app/th/management/commands/th_buzz_fetch_author.py` | **新規** | 投稿者の過去投稿取得コマンド |
| `app/th/management/commands/th_buzz_run_scheduled.py` | **新規** | 予約ジョブ実行コマンド |
| `app/app/console/views/buzz.py` | **新規** | バズ投稿取得画面ビュー（5つのビュー関数） |
| `app/app/console/views/__init__.py` | 編集 | buzz_views インポート追加 |
| `app/app/console/urls.py` | 編集 | バズ機能 URL 5件追加 |
| `app/app/console/templates/admin/console/buzz_search.html` | **新規** | バズ投稿取得メイン画面 |
| `app/app/console/templates/admin/console/buzz_author_detail.html` | **新規** | 投稿者詳細画面 |
| `app/app/settings.py` | 編集 | JAZZMIN_SETTINGS にメニュー・アイコン追加 |
| `app/requirements.txt` | 編集 | playwright>=1.40.0 追加 |
| `app/Dockerfile` | 編集 | `playwright install --with-deps chromium` 追加 |
| `docker-compose.yml` | 編集 | scheduler に th_buzz_run_scheduled 追加 |

### 変更概要
1. **モデル**: 投稿者(THBuzzAuthor)、バズ投稿(THBuzzPost)、検索ジョブ(THBuzzSearchJob) の3モデル
2. **スクレイパー**: Playwright でスレッズ検索ページ・プロフィールページをスクレイピング
3. **管理コマンド**: CLI からの検索実行、投稿者の過去投稿取得、予約ジョブ実行
4. **管理画面**: キーワード入力→即時/予約実行→結果テーブル（ソート/フィルタ対応）
5. **投稿者詳細**: プロフィール表示 + 投稿一覧 + 「投稿文を取得」ボタン

### 影響/副作用の可能性
1. Playwright 追加により Docker イメージサイズが増加（約200MB）
2. スクレイピングは Threads の DOM 変更で動作しなくなる可能性あり（セレクタの保守が必要）

---

## 検証結果（追記）

### 未実行（デプロイ前）
以下のコマンドでの検証が必要:

```bash
# Docker イメージ再ビルド
docker compose -p muitobem build django scheduler

# マイグレーション
docker compose -p muitobem exec django python manage.py makemigrations th
docker compose -p muitobem exec django python manage.py migrate

# 管理画面確認
# https://muitobem.top/console/buzz-search/

# CLI テスト
docker compose -p muitobem exec django python manage.py th_buzz_search -k "AI" --dry-run
```

---

## 次のアクション

### TODO
1. [x] モデル定義（THBuzzAuthor, THBuzzPost, THBuzzSearchJob）
2. [x] スクレイパーサービス（buzz_scraper.py）
3. [x] 管理コマンド（th_buzz_search, th_buzz_fetch_author, th_buzz_run_scheduled）
4. [x] Views/Templates（buzz_search, buzz_author_detail）
5. [x] メニュー統合（JAZZMIN_SETTINGS, urls.py）
6. [x] Docker 更新（Dockerfile, docker-compose.yml, requirements.txt）
7. [ ] **デプロイ検証**: Docker ビルド → マイグレーション → 動作確認
8. [ ] **スクレイピング精度向上**: Threads DOM 構造の詳細調査・セレクタ調整
9. [ ] **エラーハンドリング強化**: ブラウザ起動失敗時のリトライ、ログ充実

### 人間が行う作業（git add/commit/push等）
1. `git add` で変更ファイルをステージング
2. `git commit -m "feat: Threads バズ投稿取得機能を追加"`
3. `git push origin main`
4. 本番 VPS で `git pull && docker compose -p muitobem build && docker compose -p muitobem up -d`
5. `docker compose -p muitobem exec django python manage.py makemigrations th`
6. `docker compose -p muitobem exec django python manage.py migrate`
7. 管理画面で動作確認: https://muitobem.top/console/buzz-search/
