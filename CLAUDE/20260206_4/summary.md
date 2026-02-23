# タスク記録
## 概要
- 背景：参加日取得が失敗（セレクタ不一致）、少投稿アカウントで無駄スクロール
- ゴール：(1) 参加日取得のセレクタ改善＋SSR JSONフォールバック (2) スクロール早期終了改善
- 影響範囲：buzz_scraper.py
- 期限/優先度：高

## 現状（事実）
- `[aria-label="その他"]` 等で「...」ボタンが見つからない
- @okami_uranai_kasumi: 3件しかないのに10回スクロールして全てAPI=0
- @akaikarasu666: API傍受は正常動作（4→174件）

## Plan（編集前）
- 修正1: `_extract_join_date()` セレクタ拡張＋SVGフォールバック＋SSR JSONフォールバック＋デバッグログ
- 修正2: スクロール早期終了条件の緩和（no_new_count >= 3 で打ち切り）
- 変更ファイル: buzz_scraper.py のみ

## 調査ログ
- ログ分析: 参加日は2回とも `'...'ボタンが見つかりません` で失敗
- @okami_uranai_kasumi: API=0 × 10回、height変化なし判定が効いていない可能性

## 実装内容
### 変更ファイル一覧

1. **app/th/services/buzz_scraper.py**
   - `_extract_join_date()` を大幅改善:
     - **方法1（新規）**: SSR JSON 内の `date_joined` / `created_at` / `joined` フィールドを正規表現で検索（モーダル操作不要）
     - **方法2（aria-label 拡張）**: 候補を7つに拡張（`その他`, `More options`, `More`, `もっと見る`, `その他のオプション`, `Menu`, `Options`）
     - **方法3（新規・SVGフォールバック）**: aria-label で見つからない場合、`role="button"` + SVG を含む小さいボタン要素を CSS セレクタで検索（`header [role="button"]:has(svg)`, `[role="button"]:has(svg circle)`, `div[role="button"] svg`）
     - **デバッグ改善**: ボタンが見つからない場合、ページ上の `role="button"` 要素一覧（tag, aria-label, text, hasSvg）をログに出力
     - `get_by_text` に `exact=False` を追加、`About this account` も候補に追加
   - スクロール早期終了条件の緩和（`search_keyword` と `fetch_author_posts` の両方）:
     - 旧: `no_new_count >= 2 and new_height == prev_height`
     - 新: `no_new_count >= 3 or (no_new_count >= 2 and new_height == prev_height)`
     - 終了時にログ出力追加（連続回数と height 変化の有無）

## 検証結果
- @akaikarasu666 で参加日 `2025年10月` 取得成功
- 投稿164件取得成功（API傍受経由）
- ボタン試行: 4候補中 index=8 で「このプロフィールについて」メニュー発見
  - index=2: 「列として追加」→ スキップ
  - index=7: 通知メニュー → スキップ
  - index=8: 正解（「このプロフィールについて」）

## 次のアクション
- 定期ジョブで他のアカウントでも参加日が取得されるか経過観察
- 管理画面で参加日表示を確認（`author.raw_json.joined_at`）
