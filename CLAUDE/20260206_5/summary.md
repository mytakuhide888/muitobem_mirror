# タスク記録
## 概要
- 背景：投稿取得で件数が大幅に増え、レコードの絞り込みが必要
- ゴール：いいね数、リプライ数、スコア、ER の範囲指定フィルタを追加
- 影響範囲：views/buzz.py, buzz_search.html
- 期限/優先度：高

## 現状（事実）
- 既存フィルタ: 投稿者、キーワード、バズのみ、日付範囲、ソート
- 数値による範囲絞り込みがない

## Plan（編集前）
- views/buzz.py: 8パラメータ（like_min/max, reply_min/max, score_min/max, er_min/max）追加
- buzz_search.html: フィルタフォームに範囲入力欄追加、ページネーションリンク更新

## 実装内容
### 変更ファイル一覧

1. **app/app/console/views/buzz.py**
   - 8つの GET パラメータ追加: `like_min`, `like_max`, `reply_min`, `reply_max`, `score_min`, `score_max`, `er_min`, `er_max`
   - QuerySet に `__gte` / `__lte` フィルタ適用（int/float 変換エラーは無視）
   - コンテキストに `current_like_min` 等 8変数追加

2. **app/app/console/templates/admin/console/buzz_search.html**
   - CSS: `.range-group`, `.range-sep` スタイル追加
   - フィルタフォームに4つの範囲入力グループ追加（いいね数、リプライ数、スコア、ER%）
   - 各グループは min〜max の number input ペア
   - ページネーションリンク: `{% with %}` タグで全パラメータを結合し、4箇所のリンクを簡潔化

### マイグレーション不要

## 検証結果
- ローカルでのコード確認のみ（実環境テストはデプロイ後）

## 次のアクション
- 人間が行う作業:
  1. git add / commit / push
  2. Docker ビルド・デプロイ
  3. `/console/buzz-search/` で範囲フィルタの動作確認
  4. ページネーションでフィルタ値が保持されることを確認
