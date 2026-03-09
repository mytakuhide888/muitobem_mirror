# タスク記録
## 概要
- 背景：コンセプト設計で作成したキャラクターを使い、参考アカウントの投稿をAIリライトして半自動運用するワークフローが必要
- ゴール：参考投稿→AIリライト→スケジュール投稿一括生成＋パフォーマンストラッキング
- 影響範囲：th/models.py, 新規サービス2つ, 新規ビュー/テンプレート, URL追加, th_run_due_posts修正
- 期限/優先度：即時対応

## 現状（事実）
- ConceptProject, ConceptProjectAuthor, AppraisalCharacter は既存
- THScheduledPost (DRAFT→APPROVED→SENT) の予約投稿フローは稼働中
- ThreadsBuzzScraper, content_generator, ng_word_checker は利用可能

## Plan（編集前）
- Phase 1: 参考投稿→AIリライト→一括スケジュール生成
- Phase 2: 投稿パフォーマンストラッキング
- Phase 3: 画像・動画対応（将来）

## 実装内容

### Phase 1 + 2 一括実装

#### 変更ファイル一覧
| ファイル | 変更内容 |
|---------|---------|
| `app/th/models.py` | THScheduledPost に6フィールド追加（source_buzz_post, concept_project, external_post_id, impressions, engagement, insights_updated_at） |
| `app/th/services/auto_post_generator.py` | **新規作成** — fetch_reference_posts, rewrite_post_with_concept, generate_scheduled_posts |
| `app/th/services/post_insights_fetcher.py` | **新規作成** — fetch_post_insights, bulk_fetch_insights |
| `app/app/console/views/auto_posting.py` | **新規作成** — 5つのビュー（画面+API4つ） |
| `app/app/console/templates/admin/console/auto_posting.html` | **新規作成** — 自動投稿ワークフローUI |
| `app/app/console/urls.py` | URL 5パス追加 + import追加 |
| `app/app/console/templates/admin/console/dashboard.html` | ダッシュボードにカード追加 |
| `app/th/management/commands/th_run_due_posts.py` | 投稿成功時に external_post_id を保存 |

#### 変更概要
1. **モデル変更**: THScheduledPost にリライト元バズ投稿FK、コンセプトプロジェクトFK、外部投稿ID、インプレッション、エンゲージメント、インサイト更新日時を追加
2. **自動投稿生成サービス**: DB/スクレイパーから参考投稿取得 → Claude Sonnet でキャラリライト → NGワードチェック → THScheduledPost(DRAFT)一括生成
3. **インサイト取得サービス**: Threads API get_media_insights でいいね/リプライ/インプレッション取得・保存
4. **管理画面**: プロジェクト選択→参考アカウント表示→生成ボタン→スケジュール一覧（インライン編集・一括承認・インサイト更新）
5. **th_run_due_posts修正**: 投稿成功時に published_id を external_post_id に保存

## 検証結果
- 全Pythonファイル構文チェック: OK（ast.parse通過）
- HTMLテンプレート: Djangoテンプレート構文確認済み

## 次のアクション
- 人間が行う作業:
  1. `git add` で対象ファイルをステージング
  2. `git commit && git push`
  3. VPSで `git pull`
  4. VPSで `docker compose exec django python manage.py makemigrations th`
  5. VPSで `docker compose exec django python manage.py migrate`
  6. VPSで `docker compose exec django python manage.py collectstatic --noinput`
  7. VPSで `docker compose restart django`
  8. `https://muitobem.top/admin/console/auto-posting/` にアクセスして動作確認
