# タスク記録
## 概要
- 背景：Phase A（投稿パターン分析・構造化分析メモ・自動巡回パイプライン）完了後のPhase B
- ゴール：リサーチの精度向上と効率化（fortune_classifier改善、アカウント比較画面、類似アカウント自動発見）
- 影響範囲：fortune_classifier.py, buzz_compare(新規), similar_finder(新規), urls.py, テンプレート
- 期限/優先度：高

## 現状（事実）
- Phase A完了済み、Phase Bの3タスクを実装完了
- マイグレーション不要

## Plan（編集前）
- Task 1: fortune_classifier.py に3改善（URL解析/直近重み/信頼度補正）
- Task 2: アカウント比較画面（view+template+URL+ランキング画面ボタン）
- Task 3: 類似アカウント自動発見（サービス+API+URL+詳細画面ボタン）

## 調査ログ
- 2026/02/24: 対象ファイル全読み込み完了、リポジトリパスは /home/niiya/muitobem_mirror

## 実装内容
### Task 1: fortune_classifier.py 改善
- **変更ファイル**: `app/th/services/fortune_classifier.py`
- 1A: `MONETIZATION_URL_PATTERNS` 定数追加 + `_detect_monetization_urls()` ヘルパー追加
  - bio内URLのドメインパターンマッチでマネタイズ度を加算
- 1B: 投稿ループに直近重み付け（i<5: 2.0x, i<10: 1.5x, i<20: 1.0x, else: 0.7x）
  - 正規化を `num_posts` → `total_weight` に変更
- 1C: `classify_fortune_relevance()` に `followers_count`, `total_post_count` 引数追加
  - フォロワー>100 かつ 投稿数 < followers/500 で最大15点減算
  - `update_author_fortune_classification()` で新引数を渡すよう変更

### Task 2: アカウント比較画面
- **新規**: `app/app/console/views/buzz_compare.py` - 比較View
- **新規**: `app/app/console/templates/admin/console/buzz_compare.html` - 比較テンプレート
  - 横並びカラム、共通キーワードバー、Chart.jsドーナツチャート、分析メモ要約
- **変更**: `app/app/console/urls.py` - `buzz-compare/` URL追加
- **変更**: `buzz_growth_ranking.html` - 一括操作バーに「比較する」ボタン + `openCompare()` JS追加

### Task 3: 類似アカウント自動発見
- **新規**: `app/th/services/similar_finder.py`
  - `extract_search_keywords()`: genre_tags/bio/バズ投稿からキーワード抽出（トップ5）
  - `find_similar_authors()`: DB検索 + 類似度スコアリング（ジャンル/マネタイズ/bio/成長スコア）
- **変更**: `app/app/console/views/buzz.py` - `buzz_find_similar()` API追加
- **変更**: `app/app/console/urls.py` - `api/buzz/find-similar/<int:pk>/` URL追加
- **変更**: `buzz_author_detail.html` - 「類似アカウントを探す」ボタン + 結果グリッド表示エリア + `findSimilar()` JS追加

## 検証結果
- Task 1: Python単体テストでURL解析(stores.jp/lin.ee検出OK)、直近重み付け、フォロワー/投稿比率ペナルティ(少投稿56.5 vs 多投稿70.0)を確認
- Task 2, 3: 全Pythonファイルの構文チェック(py_compile) OK
- マイグレーション: 不要（DB変更なし）

## ファイル変更サマリ
| ファイル | Task | 種別 |
|---------|------|------|
| `app/th/services/fortune_classifier.py` | 1 | 変更 |
| `app/app/console/views/buzz_compare.py` | 2 | 新規 |
| `app/app/console/templates/admin/console/buzz_compare.html` | 2 | 新規 |
| `app/th/services/similar_finder.py` | 3 | 新規 |
| `app/app/console/urls.py` | 2,3 | 変更 |
| `app/app/console/views/buzz.py` | 3 | 変更 |
| `app/app/console/templates/admin/console/buzz_growth_ranking.html` | 2 | 変更 |
| `app/app/console/templates/admin/console/buzz_author_detail.html` | 3 | 変更 |

## 次のアクション
- 人間が行う作業: git add / commit / push → VPSデプロイ
- デプロイ後の検証:
  1. Django shellで既存アカウントのスコアbefore/after比較
  2. ランキング画面で2-3件チェック → 比較ボタン → 横並び表示確認
  3. お気に入りアカウント詳細 → 「類似アカウントを探す」→ 結果表示確認
