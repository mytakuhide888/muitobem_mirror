# タスク記録
## 概要
- 背景：急成長ランキングで深堀スキャン後もプロフィール画像・投稿サムネが取得されない問題
- ゴール：バズ投稿取得・深堀スキャン時に個別アカウント情報を自動収集、UI上でON/OFF制御
- 影響範囲：th/management/commands/, app/console/views/buzz.py, templates
- 期限/優先度：高

## 現状（事実）
- 深堀スキャンは total_post_count ≦ 3 のアカウントのみ対象 → ランキング上位（投稿4件以上）は対象外
- profile_pic_url が空でも深堀スキャン対象外になる（更新されない）
- th_buzz_deep_scan.py 69-71行: text_content が空の投稿をスキップ → 画像・リール投稿のサムネを捨てている
- キーワード検索・一括巡回では fetch_author_posts() を呼ばない（過去投稿取得なし）

## Plan（修正6箇所）

### Fix A: th_buzz_deep_scan.py — 対象条件に profile_pic_url 空を追加
- `profile_pic_url = ''` のアカウントも深堀スキャン対象に含める
- POSTS_THRESHOLD を 3→5 に拡大（より多くの投稿不足アカウントを対象に）

### Fix B: th_buzz_deep_scan.py — テキストなし投稿スキップを修正
- `if not text: continue` → テキストなしでも post_url があれば保存

### Fix C: th_buzz_search.py — --fetch-posts オプション追加
- ON時: プロフィール取得後に fetch_author_posts() も実行

### Fix D: th_buzz_keyword_scan.py — --fetch-posts オプション追加
- Step2のプロフィール取得後に fetch_author_posts() も実行

### Fix E: app/console/views/buzz.py — fetch_posts を各コマンドに渡す + deep_scan対象カウント修正
- buzz_run_search / buzz_run_keyword_scan でPOSTパラメータを受け取り --fetch-posts を渡す
- buzz_run_deep_scan の target_count に profile_pic_url='' 条件を追加

### Fix F: テンプレート — チェックボックス追加
- buzz_search.html: 「投稿者の過去投稿も取得する」チェックボックス
- buzz_keyword_scan.html: 同様

## 調査ログ
- 2026/02/26: コード調査完了
  - deep_scan: POSTS_THRESHOLD=3 で投稿4件以上は対象外（ランキング上位が抜ける）
  - deep_scan: text_contentが空の投稿スキップ = 画像投稿のmedia_urlsが捨てられる
  - th_buzz_search/keyword_scan: fetch_author_posts()を呼んでいない

## 実装内容

### 変更ファイル（5件）
| ファイル | 変更内容 |
|---------|---------|
| `th/management/commands/th_buzz_deep_scan.py` | POSTS_THRESHOLD 3→5、テキスト空投稿スキップ修正、profile_pic_url空を対象条件に追加 |
| `th/management/commands/th_buzz_search.py` | `--fetch-posts` オプション追加、`_save_author_posts()` メソッド追加 |
| `th/management/commands/th_buzz_keyword_scan.py` | `--fetch-posts` オプション追加、`_fetch_and_save_posts()` メソッド追加 |
| `app/console/views/buzz.py` | fetch_posts をコマンドに渡す処理追加、deep_scan の target_count にprofile_pic_url空条件追加 |
| `templates/buzz_search.html` | 「投稿者情報を詳細取得」チェックボックス追加（JS送信含む） |
| `templates/buzz_keyword_scan.html` | 同上 |

## 検証結果

- Python構文チェック: 4ファイルすべてOK
## 次のアクション
- [ ] 実装完了後: git add/commit/push（人間が実施）
- [ ] VPS: git pull → docker restart
