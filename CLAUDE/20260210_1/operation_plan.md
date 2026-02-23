# 急成長アカウント発見機能 - 実装Plan

## 目的
メイト氏のコンセプト設計 Step 1「直近で異常に伸びているアカウントを見つける」を
システム機能として実現する。

## 現状 → 目標

```
【現状】
キーワード検索 → 投稿一覧 → 手動でアカウントを1つずつ確認

【目標】
キーワード一括巡回 → 急成長アカウント自動検出 → ランキング表示
→ プロフィール・投稿パターンの一覧分析 → コンセプト設計の材料
```

---

## 実装内容（3段階）

### Phase A: モデル拡張 + 成長スコア算出（最優先）

#### A-1. THBuzzAuthor モデルに成長指標フィールドを追加

```python
# 追加フィールド
total_post_count     = IntegerField('総投稿数', null=True, blank=True)
earliest_post_at     = DateTimeField('最古の投稿日時', null=True, blank=True)
latest_post_at       = DateTimeField('最新の投稿日時', null=True, blank=True)
avg_likes            = FloatField('平均いいね数', null=True, blank=True)
avg_replies          = FloatField('平均リプライ数', null=True, blank=True)
growth_score         = FloatField('急成長スコア', null=True, blank=True)
account_age_days     = IntegerField('推定アカウント日数', null=True, blank=True)
followers_per_day    = FloatField('1日あたりフォロワー増', null=True, blank=True)
category_tags        = CharField('カテゴリタグ', max_length=500, blank=True, default='')
memo                 = TextField('メモ(人間用)', blank=True, default='')
```

#### A-2. 急成長スコアの計算ロジック

```python
def calculate_growth_score(author):
    """
    急成長スコア = フォロワー密度 × エンゲージメント品質

    フォロワー密度 = followers_count / account_age_days
      → 開設日数に対してフォロワーが多いほど高い

    エンゲージメント品質 = avg_likes / followers_count (× 100)
      → フォロワーに対するいいね率が高いほど高い
      → 少フォロワーで高エンゲージメント = 急成長の兆候

    異常検出の目安:
      - 開設1週間でフォロワー3000+ → growth_score > 400
      - 開設1ヶ月でフォロワー10000+ → growth_score > 300
      - いいね率10%以上 → 非常に高品質
    """
    if not author.account_age_days or author.account_age_days < 1:
        return 0
    if not author.followers_count or author.followers_count < 10:
        return 0

    # フォロワー密度（1日あたりフォロワー増加数）
    follower_density = author.followers_count / author.account_age_days

    # エンゲージメント品質（フォロワー数に対するいいね比率）
    eng_quality = 1.0
    if author.avg_likes and author.followers_count > 0:
        eng_quality = (author.avg_likes / author.followers_count) * 100
        eng_quality = min(eng_quality, 50)  # 上限50でキャップ

    # 急成長スコア = 密度 × 品質
    score = follower_density * eng_quality

    return round(score, 2)
```

#### A-3. account_age_days の推定方法

```
方法1: earliest_post_at（最古の投稿日時）を取得し、現在との差分
方法2: th_buzz_fetch_author で過去投稿を全取得した際に最古を記録
方法3: first_scraped_at からの日数（初回スクレイピング日からの差分、不正確だが参考値）
```

→ **方法1を採用**: 投稿者の過去投稿取得時に `earliest_post_at` を自動更新

#### A-4. 既存コマンドの拡張

`th_buzz_fetch_author` 完了時に以下を自動計算:
- total_post_count: 取得した投稿数
- earliest_post_at: 投稿の中で最古の日時
- latest_post_at: 投稿の中で最新の日時
- avg_likes: 投稿のいいね平均
- avg_replies: 投稿のリプライ平均
- account_age_days: (now - earliest_post_at).days
- followers_per_day: followers_count / account_age_days
- growth_score: calculate_growth_score()

**変更ファイル**:
- `app/th/models.py` - THBuzzAuthor にフィールド追加
- `app/th/admin.py` - 管理画面に新フィールド表示
- `app/th/management/commands/th_buzz_fetch_author.py` - 統計計算の追加
- `app/th/management/commands/th_buzz_search.py` - 検索結果からも初期統計計算

---

### Phase B: 急成長アカウント発見UI（高優先）

#### B-1. 急成長アカウントランキング画面

管理画面に「急成長アカウント」ビューを追加:

```
URL: /console/buzz-growth-ranking/

表示内容:
- growth_score 降順でアカウント一覧
- フォロワー数 / アカウント日数 / 平均いいね / 急成長スコア
- フィルタ: カテゴリ, 最小フォロワー数, 最小スコア, 期間
- 各アカウントの最新投稿プレビュー
- プロフィール（bio）の表示
- 「詳細分析」ボタン → 既存のbuzz_author_detail へ
```

#### B-2. キーワード一括巡回機能

管理画面から複数キーワードを一括でスキャン:

```
URL: /console/buzz-keyword-scan/

入力:
- キーワードリスト（例: 占い, タロット, 霊視, ツインレイ, 金運, 恋愛占い）
- または定義済みキーワードセット（「占い基本セット」「スピリチュアルセット」等）

処理:
1. 各キーワードで Threads 検索実行
2. 取得した投稿から新規の投稿者を発見
3. 新規投稿者のプロフィール取得
4. 急成長スコアを計算
5. 結果をランキング形式で表示

出力:
- 発見したアカウント数
- 急成長スコア上位のアカウント
- キーワードごとのヒット数
```

#### B-3. 定期巡回ジョブ（scheduler拡張）

```
docker-compose.yml の scheduler に追加:
- th_buzz_keyword_scan: 1日1回、定義済みキーワードで自動巡回
- 新規発見の急成長アカウントを自動記録
- 閾値超えたらログに通知
```

**変更ファイル**:
- `app/app/console/views/buzz.py` - ランキング画面、一括巡回画面を追加
- `app/app/console/urls.py` - URL追加
- `app/app/console/templates/admin/console/buzz_growth_ranking.html` - 新規テンプレート
- `app/app/console/templates/admin/console/buzz_keyword_scan.html` - 新規テンプレート
- `app/app/settings.py` - メニューに項目追加
- `app/th/management/commands/th_buzz_keyword_scan.py` - 一括巡回コマンド（新規）

---

### Phase C: Googleトレンド連携（中優先）

#### C-1. pytrends によるキーワードボリューム取得

```python
# requirements.txt に追加
pytrends>=4.9.0

# 新規サービス
# app/th/services/trend_analyzer.py

from pytrends.request import TrendReq

class TrendAnalyzer:
    def get_keyword_interest(self, keywords, timeframe='today 3-m', geo='JP'):
        """キーワードの検索ボリューム推移を取得"""
        pytrends = TrendReq(hl='ja-JP', tz=540)
        pytrends.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
        return pytrends.interest_over_time()

    def get_related_queries(self, keyword, geo='JP'):
        """関連キーワードを取得"""
        pytrends = TrendReq(hl='ja-JP', tz=540)
        pytrends.build_payload([keyword], geo=geo)
        return pytrends.related_queries()

    def compare_keywords(self, keywords, geo='JP'):
        """キーワード間の検索ボリューム比較"""
        pytrends = TrendReq(hl='ja-JP', tz=540)
        pytrends.build_payload(keywords[:5], geo=geo)
        return pytrends.interest_over_time()
```

#### C-2. 管理画面にトレンド分析画面を追加

```
URL: /console/buzz-trends/

機能:
- キーワード入力 → Googleトレンドのグラフ表示
- 関連キーワード一覧
- キーワード間の比較
- 「このキーワードで検索」ボタン → バズ検索へ連携
```

**変更ファイル**:
- `app/requirements.txt` - pytrends追加
- `app/th/services/trend_analyzer.py` - 新規
- `app/app/console/views/buzz.py` - トレンド分析ビュー追加
- `app/app/console/urls.py` - URL追加
- `app/app/console/templates/admin/console/buzz_trends.html` - 新規テンプレート

---

## 全体の変更ファイル一覧

### Phase A（最優先）
| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `app/th/models.py` | 編集 | THBuzzAuthor にフィールド追加 |
| `app/th/admin.py` | 編集 | 新フィールドの管理画面表示 |
| `app/th/management/commands/th_buzz_fetch_author.py` | 編集 | 統計計算の追加 |
| `app/th/management/commands/th_buzz_search.py` | 編集 | 初期統計計算の追加 |

### Phase B（高優先）
| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `app/app/console/views/buzz.py` | 編集 | ランキング画面、一括巡回画面 |
| `app/app/console/urls.py` | 編集 | URL追加 |
| `app/app/console/templates/admin/console/buzz_growth_ranking.html` | **新規** | ランキング画面 |
| `app/app/console/templates/admin/console/buzz_keyword_scan.html` | **新規** | 一括巡回画面 |
| `app/app/settings.py` | 編集 | メニュー追加 |
| `app/th/management/commands/th_buzz_keyword_scan.py` | **新規** | 一括巡回コマンド |

### Phase C（中優先）
| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `app/requirements.txt` | 編集 | pytrends追加 |
| `app/th/services/trend_analyzer.py` | **新規** | Googleトレンド連携 |
| `app/app/console/views/buzz.py` | 編集 | トレンド分析ビュー |
| `app/app/console/urls.py` | 編集 | URL追加 |
| `app/app/console/templates/admin/console/buzz_trends.html` | **新規** | トレンド分析画面 |

---

## 検証方法

### Phase A
```bash
# マイグレーション
docker compose -p muitobem exec django python manage.py makemigrations th
docker compose -p muitobem exec django python manage.py migrate

# 既存アカウントの統計再計算
docker compose -p muitobem exec django python manage.py shell
>>> from th.models import THBuzzAuthor, THBuzzPost
>>> for a in THBuzzAuthor.objects.all():
...     posts = a.buzz_posts.all()
...     # 統計計算
...     print(f"@{a.username}: {a.followers_count}f, score={a.growth_score}")

# 新規検索 → 統計確認
docker compose -p muitobem exec django python manage.py th_buzz_search -k "霊視占い"
docker compose -p muitobem exec django python manage.py th_buzz_fetch_author --username <発見したユーザー>
```

### Phase B
```bash
# 管理画面で確認
# https://muitobem.top/console/buzz-growth-ranking/
# https://muitobem.top/console/buzz-keyword-scan/

# 一括巡回テスト
docker compose -p muitobem exec django python manage.py th_buzz_keyword_scan \
    -k "占い" -k "タロット" -k "霊視" -k "ツインレイ" -k "金運占い"
```

### Phase C
```bash
# Googleトレンドテスト
docker compose -p muitobem exec django python manage.py shell
>>> from th.services.trend_analyzer import TrendAnalyzer
>>> ta = TrendAnalyzer()
>>> ta.get_keyword_interest(["占い", "タロット", "霊視"])
```

---

## ロールバック案
- Phase A: マイグレーションのrollback (`python manage.py migrate th <前のマイグレーション番号>`)
- Phase B: 追加したURL/View/テンプレートを削除
- Phase C: pytrends削除、関連ファイル削除

## 影響/副作用
1. THBuzzAuthor のマイグレーションでカラム追加（既存データに影響なし、null許可）
2. 一括巡回のスクレイピング負荷（レート制限に注意）
3. Googleトレンドは無料APIだがレート制限あり（1日数百リクエスト程度）
