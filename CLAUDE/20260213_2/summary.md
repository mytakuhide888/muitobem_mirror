# タスク記録
## 概要
- 背景：コンセプト設計の指南書に基づき、急成長アカウントのリサーチ精度を高めたい
- ゴール：成長スコアの妥当性検証、ヘルプ画面追加、投稿不足時の自動補完、リサーチ効率化機能の提案
- 影響範囲：急成長アカウントランキング画面、バズ投稿取得処理、ER再計算処理
- 期限/優先度：通常

## 現状（事実）
### 問題1: 投稿データ不足のまま成長スコアが算出されている
- キーワード検索時、1アカウントにつき**検索結果に出てきた1投稿**しかDB保存されない
- `update_growth_stats()` は `self.buzz_posts` の集計（Avg, Count, Min, Max）に依存
- 投稿1件の場合: `total_post_count=1`, `avg_likes=その1件のいいね数`, `earliest_post_at=その1件`
- 結果として `account_age_days` が実際より短く（=最近のみ）、`followers_per_day` が過大に、`growth_score` も実態と乖離

### 問題2: 成長スコアの計算式がコンセプト設計の目的と一部ずれている
- 現在の式: `growth_score = follower_density × eng_quality`

### 問題3: 指標の意味が画面上で説明されていない
### 問題4: 不要なアカウント情報も一律保存されている

## 実装内容

### C: ヘルプモーダル追加 ✅
- `buzz_growth_ranking.html`: タイトル横に「?」ヘルプアイコンを設置
- モーダルを左ナビ形式で実装（コンセプト設計の考え方、指標の説明、使い方ガイド）
- JS: openHelp(), closeHelp(), セクションナビゲーション、Escキー対応

### B: 成長スコア計算式の改善 ✅
- `models.py`: `_parse_joined_at()` メソッド追加（raw_json.joined_at をパース）
- `update_growth_stats()`: joined_at を account_age_days の算出に優先使用
- `_calc_growth_score()`: 新計算式
  - `eng_quality = (avg_likes + avg_replies * 2) / followers * 100` (上限50)
  - `confidence = min(post_count / 5, 1.0)` で5投稿未満は割引
  - `growth_score = follower_density * eng_quality * confidence`

### A: 深掘りスキャン機能 ✅
- `th_buzz_deep_scan.py`: 新コマンド作成
  - `total_post_count <= 3` or NULL のアカウントの過去投稿を一括取得
  - `--job-id`, `--max-authors`, `--max-scrolls`, `--include-replies` 対応
- `views/buzz.py`: `buzz_run_deep_scan` ビュー追加
- `urls.py`: `api/buzz/run-deep-scan/` URL追加
- `buzz_growth_ranking.html`: 「深掘りスキャン」ボタン + ジョブポーリングJS追加
- `buzz_growth_ranking` ビュー: `deep_scan_target_count` をコンテキストに追加

### D: コンセプト候補フラグ ✅
- `models.py`: `is_concept_candidate` BooleanField 追加
- `_evaluate_concept_candidate()` メソッド追加
  - 条件: アカウント日数 7〜90日, フォロワー 500+, フォロワー増/日 10+, 成長スコア算出済み
- `update_growth_stats()` で自動判定
- `0007_thbuzzauthor_is_concept_candidate.py` マイグレーション作成
- `buzz_growth_ranking.html`: 「候補のみ」チェックボックスフィルタ + 候補バッジ表示
- `views/buzz.py`: `candidates_only` フィルタパラメータ対応
- `admin.py`: list_display, list_filter, readonly_fields, fieldsets に追加

### E: キーワード検索時の急成長フィルタ ✅
- `th_buzz_search.py`: `--growth-filter` オプション追加
  - プロフィール取得後に `is_concept_candidate` 判定、候補外なら投稿削除
- `th_buzz_keyword_scan.py`: `--growth-filter` オプション追加
  - 同様にプロフィール取得後にフィルタ判定
- `views/buzz.py`: `buzz_run_search`, `buzz_run_keyword_scan` に `growth_filter` パラメータ伝播
- `buzz_search.html`: キーワード検索に「急成長フィルタ」チェックボックス追加
- `buzz_keyword_scan.html`: 「急成長フィルタ」チェックボックス + ヘルプテキスト追加

## 変更ファイル一覧
| ファイル | 変更種別 | 提案 |
|---------|---------|------|
| `app/th/models.py` | 編集 | B, D |
| `app/th/migrations/0007_thbuzzauthor_is_concept_candidate.py` | 新規 | D |
| `app/th/management/commands/th_buzz_deep_scan.py` | 新規 | A |
| `app/th/management/commands/th_buzz_search.py` | 編集 | E |
| `app/th/management/commands/th_buzz_keyword_scan.py` | 編集 | E |
| `app/th/admin.py` | 編集 | D |
| `app/app/console/views/buzz.py` | 編集 | A, D, E |
| `app/app/console/urls.py` | 編集 | A |
| `app/app/console/templates/admin/console/buzz_growth_ranking.html` | 編集 | C, A, D |
| `app/app/console/templates/admin/console/buzz_search.html` | 編集 | E |
| `app/app/console/templates/admin/console/buzz_keyword_scan.html` | 編集 | E |

## 追加実装: ヘルプモーダル補完 + 優良アカウント指標

### 実装内容

#### Part 1: ヘルプモーダル補完
- ナビに「機能の説明」グループ追加（コンセプト候補/深掘りスキャン/急成長フィルタ/品質スコア）
- 4つのセクション本文を追加
- howtoセクションの深掘りスキャン説明を充実化

#### Part 2: 優良アカウント（quality_score / is_quality_account）
- `models.py`: 5フィールド + 6メソッド + update_growth_stats 更新
  - quality_score, is_quality_account, good_post_ratio, recent_post_count, avg_post_interval_days
  - _update_quality_stats, _calc_engagement_quality, _calc_recency_score, _calc_frequency_score, _calc_confidence_score
- `0008_thbuzzauthor_quality_fields.py`: マイグレーション新規作成
- `admin.py`: list_display, list_filter, readonly_fields, fieldsets に品質フィールド追加
- `views/buzz.py`: quality_only フィルタ + quality_score ソート + コンテキスト追加
- `buzz_growth_ranking.html`: 紫「優良」バッジ + フィルタ + ソート + ページネーション + ヘルプ4セクション
- `buzz_author_detail.html`: 品質スコアstat + 優良バッジ + 品質スコア内訳セクション（バーチャート）

### 変更ファイル一覧
| ファイル | 変更内容 |
|---------|---------|
| `app/th/models.py` | 5フィールド + 6メソッド + update_growth_stats更新 |
| `app/th/migrations/0008_thbuzzauthor_quality_fields.py` | 新規作成 |
| `app/th/admin.py` | 品質フィールド表示追加 |
| `app/app/console/views/buzz.py` | フィルタ・ソート・コンテキスト追加 |
| `app/app/console/templates/admin/console/buzz_growth_ranking.html` | ヘルプ補完 + カード・フィルタ・ソート・バッジ |
| `app/app/console/templates/admin/console/buzz_author_detail.html` | 品質スコア + 内訳表示 |

## 次のアクション
- 人間が行う作業:
  - マイグレーション適用: `python manage.py migrate`
  - 既存アカウントの再計算: Django shell で `for a in THBuzzAuthor.objects.all(): a.update_growth_stats()`
  - 動作確認
  - git add / commit / push
