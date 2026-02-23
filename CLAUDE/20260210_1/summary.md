# タスク記録
## 概要
- 背景：コンセプト設計のStep1「直近で異常に伸びているアカウントを見つける」をシステム機能で支援する
- ゴール：バズ投稿リサーチ機能を強化し、急成長アカウントを効率的に発見できるようにする
- 影響範囲：th/models.py, buzz_scraper.py, console/views/buzz.py, 管理画面
- 期限/優先度：最優先

## 現状（事実）
### 既存機能
- キーワードでThreads投稿を検索（THBuzzSearchJob）
- 投稿のエンゲージメント指標取得（いいね、リプライ、リポスト、バズスコア）
- 投稿者プロフィール取得（フォロワー数、bio等）
- 投稿者の過去投稿を遡って取得
- 管理画面でフィルタ・ソート・閲覧

### 不足している機能（Step 1に必要）
1. **アカウント年齢の推定**: 開設からの日数が分からない
2. **成長率の計算**: フォロワー数/日 が算出できない
3. **定期追跡**: フォロワー数の時系列変化が記録されない
4. **急成長スコア**: 「異常に伸びている」を定量的に判定できない
5. **複数キーワード一括巡回**: 占い関連キーワードの網羅的スキャンがない
6. **Googleトレンド連携**: キーワードの需要量が分からない

## 参考資料の理解
### sankou/20260210_consept_work.md（コンセプト設計指南書 by メイト氏）
- 3ステップ: 1.急成長アカウント発見 → 2.伸びる要因抽出 → 3.少しずらしてコンセプト確定
- 「異常に伸びている」= 初投稿で10万imp、開設1週間で3000フォロワー、1ヶ月で1万フォロワー
- リサーチ方法: ジャンルキーワード検索 → 10個フォロー → おすすめ欄から発見
- 核心: 「0からオリジナルのコンセプトは作らない。市場の答えから逆算する」

### sankou/20260210_akaban.md（BAN対策 by メイト氏）
- 占い垢はBAN対象になりにくい
- 永久BAN: 一斉配信、連鎖BAN、規約違反の3パターン
- Threads注意点: 同じ文章連投禁止、「稼ぐ」等の直接ワード回避、連続投稿回避、リンクは投稿に付けない

### sankou/20260210_hou.md（法律知識 by メイト氏）
- 霊感商法禁止: 不安を煽って高額商品を売りつけるのはNG
- AI占い: 「占う」のは人間、「書く補助」がAI → この形ならOK
- 効果保証NG: 「治る」「必ず叶う」は景品表示法/薬機法に抵触
- 免責文をSTORES等に必ず掲載

## Plan（編集前）
→ operation_plan.md に詳細記載

## 実装内容（Phase A 完了）

### 変更ファイル一覧
| ファイル | 変更概要 |
|---------|---------|
| `app/th/models.py` | THBuzzAuthor に成長指標フィールド10個 + `update_growth_stats()` / `_calc_growth_score()` メソッド追加 |
| `app/th/admin.py` | THBuzzAuthorAdmin に成長指標の表示・fieldsets 追加 |
| `app/th/management/commands/th_buzz_fetch_author.py` | 投稿取得完了後に `author.update_growth_stats()` を自動呼び出し |
| `app/th/management/commands/th_buzz_search.py` | プロフィール初回取得後に `author.update_growth_stats()` を自動呼び出し |

### 追加フィールド（THBuzzAuthor）
- `total_post_count` - 総投稿数
- `earliest_post_at` - 最古の投稿日時
- `latest_post_at` - 最新の投稿日時
- `avg_likes` - 平均いいね数
- `avg_replies` - 平均リプライ数
- `growth_score` - 急成長スコア（フォロワー密度 × エンゲージメント品質）
- `account_age_days` - 推定アカウント日数
- `followers_per_day` - 1日あたりフォロワー増
- `category_tags` - カテゴリタグ（手動分類用）
- `memo` - メモ

### 急成長スコア算出ロジック
```
growth_score = follower_density × eng_quality
  follower_density = followers_count / account_age_days
  eng_quality = (avg_likes / followers_count) × 100  ※上限50
```

### 影響/副作用
1. マイグレーション未実行（人間が `makemigrations` + `migrate` を実施する必要あり）
2. 既存データへの影響なし（追加フィールドはすべて null=True/blank=True）

## 次のアクション
### 人間が行う作業
```bash
# マイグレーション作成・適用
docker compose -p muitobem exec django python manage.py makemigrations th
docker compose -p muitobem exec django python manage.py migrate

# 既存アカウントの成長指標を再計算（任意）
docker compose -p muitobem exec django python manage.py shell -c "
from th.models import THBuzzAuthor
for a in THBuzzAuthor.objects.filter(followers_count__isnull=False):
    a.update_growth_stats()
    print(f'@{a.username}: score={a.growth_score}, f/day={a.followers_per_day}')
"
```

## 実装内容（Phase B 完了）

### 変更・新規ファイル一覧
| ファイル | 種別 | 変更概要 |
|---------|------|---------|
| `app/app/console/views/buzz.py` | 編集 | `buzz_growth_ranking`, `buzz_keyword_scan`, `buzz_run_keyword_scan` ビュー追加 |
| `app/app/console/urls.py` | 編集 | `buzz-growth-ranking/`, `buzz-keyword-scan/`, `api/buzz/run-keyword-scan/` パス追加 |
| `app/app/settings.py` | 編集 | topmenu_links に「急成長ランキング」「一括巡回」メニュー追加 |
| `app/app/console/templates/admin/console/buzz_growth_ranking.html` | **新規** | 急成長ランキング画面（カード形式、フィルタ、ソート、ページネーション） |
| `app/app/console/templates/admin/console/buzz_keyword_scan.html` | **新規** | 一括巡回画面（キーワード入力、プリセット、ジョブ履歴、ポーリング） |
| `app/th/management/commands/th_buzz_keyword_scan.py` | **新規** | 一括巡回コマンド（検索→プロフィール取得→スコア計算を統合） |

### 画面構成
- `/console/buzz-growth-ranking/` - 急成長アカウントランキング
  - growth_score 降順のカード形式一覧
  - フィルタ: 検索、最小フォロワー数、最小スコア、最大アカウント日数、カテゴリ
  - ソート: 成長スコア、F/日、フォロワー数、アカウント日数、平均いいね、更新日時
- `/console/buzz-keyword-scan/` - キーワード一括巡回
  - キーワード入力（カンマ/改行区切り）
  - 定義済みプリセット（占い基本セット、ツインレイ・恋愛セット、金運・開運セット、仕事・転職セット）
  - ジョブ履歴テーブル + ポーリングによるステータス更新

### th_buzz_keyword_scan コマンドの処理フロー
1. 各キーワードで Threads 検索実行
2. 投稿を保存（重複チェックあり）
3. プロフィール未取得のアカウントを最大20件取得
4. 各アカウントの成長指標を自動計算
5. growth_score 未計算の既存アカウントも更新

## 実装内容（Phase C 完了）

### 変更・新規ファイル一覧
| ファイル | 種別 | 変更概要 |
|---------|------|---------|
| `app/requirements.txt` | 編集 | `pytrends>=4.9.0` 追加 |
| `app/th/services/trend_analyzer.py` | **新規** | TrendAnalyzer クラス（検索ボリューム推移、関連クエリ、関連トピック取得） |
| `app/app/console/views/buzz.py` | 編集 | `buzz_trends`, `buzz_trends_api` ビュー追加 |
| `app/app/console/urls.py` | 編集 | `buzz-trends/`, `api/buzz/trends/` パス追加 |
| `app/app/settings.py` | 編集 | topmenu_links に「トレンド分析」メニュー追加 |
| `app/app/console/templates/admin/console/buzz_trends.html` | **新規** | トレンド分析画面（Chart.jsグラフ、関連KW、プリセットボタン） |

### 画面構成
- `/console/buzz-trends/` - Googleトレンド分析
  - キーワード入力（最大5個、カンマ区切り）
  - 期間選択（7日/1ヶ月/3ヶ月/12ヶ月/5年）
  - プリセット5種（占い系、恋愛系、金運系、仕事系、AI占い系）
  - Chart.js による検索ボリューム推移グラフ
  - 関連キーワード（TOP / 急上昇）テーブル
  - キーワード追加ボタン → トレンド比較に連携

### TrendAnalyzer サービス
- `get_keyword_interest(keywords, timeframe, geo)` - 検索ボリューム推移
- `get_related_queries(keyword, geo)` - 関連キーワード（top / rising）
- `get_related_topics(keyword, geo)` - 関連トピック（top / rising）

## 次のアクション
### 人間が行う作業
```bash
# pytrends インストール
docker compose -p muitobem exec django pip install pytrends>=4.9.0

# または requirements.txt から一括インストール
docker compose -p muitobem exec django pip install -r requirements.txt
```

### 全Phase完了後の確認URL
- `/console/buzz-search/` - バズ投稿取得（既存）
- `/console/buzz-growth-ranking/` - 急成長アカウントランキング（Phase B）
- `/console/buzz-keyword-scan/` - キーワード一括巡回（Phase B）
- `/console/buzz-trends/` - Googleトレンド分析（Phase C）

### 今後の拡張案
- 定期巡回ジョブ（scheduler拡張）: 毎日自動でキーワードスキャン
- トレンド×バズ検索の自動連携: 急上昇キーワードで自動検索
- フォロワー数の時系列追跡: 成長推移グラフ
