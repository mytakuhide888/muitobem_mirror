# Phase A 実装状況

> 最終更新: 2026-02-23
> 対象: リサーチ機能の効率化・自動化（機能③②①）

---

## 実装サマリ

| # | 機能 | ステータス | 変更ファイル |
|---|------|-----------|-------------|
| ③ | 自動巡回パイプライン | ✅ 完了 | 5ファイル |
| ② | 構造化分析メモ | ✅ 完了 | 4ファイル |
| ① | 投稿パターン分析ダッシュボード | ✅ 完了 | 2ファイル |

**合計変更**: 734行追加（6既存ファイル変更 + 3新規ファイル）

---

## 機能③: 自動巡回パイプライン

### 概要
登録キーワードで定期一括巡回 → 深掘りスキャン → 要注目フラグ設定を自動実行するパイプライン。

### 変更内容

**新規ファイル:**
- `app/th/management/commands/th_buzz_auto_pipeline.py` — パイプラインコマンド
- `app/th/migrations/0016_auto_pipeline_and_analysis.py` — DBマイグレーション

**変更ファイル:**
- `app/th/models.py` — `THBuzzAuthor` に3フィールド追加
  - `is_attention_needed` (Boolean) — 成長スコア + 占い適合スコアが閾値超えのアカウント
  - `attention_set_at` (DateTime) — フラグ設定日時
  - `is_analyzed` (Boolean) — 構造化分析メモ記入済みフラグ
- `docker-compose.yml` — scheduler に毎日06時（JST）の自動実行を追加
- `app/app/console/views/buzz.py` — ランキング画面に統計情報 + 手動実行API
- `app/app/console/templates/admin/console/buzz_growth_ranking.html` — パイプライン統計バナー + 実行ボタン

### パイプライン動作フロー

```
Phase 1: キーワード巡回
  → デフォルト11キーワード（占い/タロット/霊視/ツインレイ/金運占い/恋愛占い/スピリチュアル/四柱推命/数秘術/パワーストーン/波動修正）
  → 投稿取得 + 新規アカウント発見 + プロフィール取得

Phase 2: 深掘りスキャン
  → 占い適合スコア30以上 + 投稿数3件以下のアカウントを自動深掘り
  → 上限15件/回

Phase 3: 要注目フラグ更新
  → 成長スコア≧100 + 占い適合スコア≧30 → is_attention_needed = True
  → 条件を満たさなくなった未分析アカウントのフラグをクリア
```

### 使い方

```bash
# 手動実行
python manage.py th_buzz_auto_pipeline

# ドライラン（フラグ更新のみ、スクレイピングなし）
python manage.py th_buzz_auto_pipeline --dry-run

# 閾値変更
python manage.py th_buzz_auto_pipeline --growth-threshold 50 --fortune-threshold 20
```

管理画面からは「急成長ランキング」画面上部の「🔄 自動巡回パイプライン実行」ボタンでも手動起動可能。

### ランキング画面の追加要素

- **統計バナー**: 要注目数 / 今週の新規要注目 / 今週の新規発見 / 分析済み数
- **フィルタ**: 「⚠️ 要注目のみ」チェックボックス
- **バッジ**: 各アカウントカードに「⚠要注目」「📝分析済」バッジ

---

## 機能②: 構造化分析メモ

### 概要
メイト氏Step2「伸びている要因を3つ以上ピックアップ」を構造的に記録し、Step3のコンセプト設計に活かすための分析フォーム。

### 変更内容

**新規モデル: `THBuzzAuthorAnalysis`**
- `factor_profile` — プロフィール/表示名の工夫
- `factor_concept` — コンセプト（何者か、ギャップ）
- `factor_content` — 投稿内容の傾向
- `factor_format` — 投稿形式の使い分け
- `factor_frequency` — 投稿頻度・タイミング
- `factor_engagement` — エンゲージメントの取り方
- `factor_funnel` — 導線設計（bio→LINE→鑑定等）
- `factor_other` — その他の要因
- `overall_assessment` — 総合評価
- `concept_inspiration` — この垢から得たコンセプトのヒント
- `differentiation_idea` — ずらしのアイデア（Step3）
- `analyzed_at` — 分析日時

**API エンドポイント:**
- `POST /console/api/buzz/author-analysis/<pk>/` — 分析メモの保存

**UI:**
- 投稿者詳細画面に「📝 分析記録」タブを追加
- 左列: 伸びている要因8項目のテキストエリア
- 右列: 総合評価・コンセプトヒント・ずらしアイデアのテキストエリア + 分析ヒント
- 保存ボタンで即時DB保存、分析済みフラグを自動更新

---

## 機能①: 投稿パターン分析ダッシュボード

### 概要
既存の投稿データから投稿パターンを自動集計し、6種のチャートで可視化するダッシュボード。DB変更なし。

### 変更内容

**ヘルパー関数:** `_calc_post_pattern_stats()` in `views/buzz.py`
- 投稿時間帯ヒートマップ（曜日×時間帯）
- メディア形式分布（テキスト/画像/動画/カルーセル）
- テキスト長分布（短文/中文/長文）
- ER推移（直近50件の折れ線グラフ）
- 頻出ワードTop20（カタカナ3文字以上 + 漢字2文字以上を自動抽出）
- ハッシュタグTop15

**UI:**
- 投稿者詳細画面に「📊 投稿パターン分析」タブを追加
- Chart.js（CDN）による6種のインタラクティブチャート
  1. 投稿時間帯の棒グラフ（24時間）
  2. メディア形式のドーナツグラフ
  3. テキスト長分布の棒グラフ
  4. ER推移の折れ線グラフ
  5. 頻出ワードの横棒グラフ
  6. ハッシュタグの横棒グラフ
- 数値サマリ: 総投稿数 / バズ投稿数 / 平均文字数 / 週間投稿数 / バズ平均文字数

### 技術仕様
- Chart.js v4.4.1 をCDN読み込み
- チャート描画は「📊 投稿パターン分析」タブ初回表示時に遅延実行（パフォーマンス配慮）
- テキスト解析は簡易形態素解析（正規表現ベース、カタカナ・漢字パターンマッチ）

---

## タブUI構成

投稿者詳細画面のタブ構成:

| タブ | 内容 | 実装 |
|------|------|------|
| 📋 投稿一覧 | 既存の投稿フィルタ + テーブル + ページネーション | 既存（タブでラップ） |
| 📊 投稿パターン分析 | 6種のチャート + 数値サマリ | 機能① |
| 📝 分析記録 | 構造化メモフォーム（11項目） | 機能② |

---

## デプロイ手順

```bash
# 1. VPSにpull
cd ~/muitobem_mirror && git pull

# 2. マイグレーション実行
docker compose -p muitobem exec django python manage.py migrate

# 3. コンテナ再ビルド（scheduler変更のため）
docker compose -p muitobem up -d --build

# 4. 動作確認
docker compose -p muitobem exec django python manage.py th_buzz_auto_pipeline --dry-run
```

---

## 次のステップ（Phase B候補）

| # | 機能 | 優先度 | 状況 |
|---|------|--------|------|
| ④ | アカウント比較画面 | 中 | 未着手 |
| ⑤ | 類似アカウント自動発見 | 中 | 未着手 |
| — | fortune_classifier改善（URL解析、直近重み付け） | 低 | 未着手 |
