# タスク記録
## 概要
- 背景：Phase B残タスク（NGワードチェッカー）+ Phase C（集客自動化）
- ゴール：NGワードチェッカー実装 → Phase C計画・実装・デプロイ
- 影響範囲：ng_word_checker(新規), content_generator(新規), scheduled_posts(新規), views, urls, テンプレート, settings, requirements
- 期限/優先度：高

## 現状（事実）
- Phase B: fortune_classifier改善・比較画面・類似発見 完了済み
- 残：NGワードチェッカー（★☆☆）→ 完了
- Phase C: 投稿文AI生成 + 予約投稿管理 → 完了

## Plan（編集前）
- Task 1: NGワードチェッカーサービス＋画面＋API実装
- Task 2: Phase C 計画策定（plan mode）
- Task 3: Phase C 実装（4サブタスク）

## 調査ログ
- 2026/02/24: ロードマップ・戦略文書（第11章法令遵守）確認済み
- NGワード対象: 霊感商法表現、確実性表現、薬機法違反、景品表示法違反、対象外相談事項、AI表示義務
- Phase C既存基盤確認: social/services/threads_api.py, th/models.py(THScheduledPost), th/management/commands/th_run_due_posts.py

## 実装内容

### Task 1: NGワードチェッカー
- `app/th/services/ng_word_checker.py` — 6カテゴリのNGワード辞書 + `check_ng_words()` 関数
- `app/app/console/views/buzz.py` — `buzz_ng_checker()`, `buzz_ng_check_api()` 追加
- `app/app/console/templates/admin/console/buzz_ng_checker.html` — NGチェック画面
- `app/app/console/urls.py` — NGチェッカー用URL 2本追加

### Task 2: Phase C 計画
- plan mode で Phase C 実装計画書を策定
- 4タスク構成: 環境設定 → AI生成サービス → 生成画面 → 予約投稿管理画面

### Task 3: Phase C 実装

#### 新規ファイル（5件）
| ファイル | 概要 |
|---------|------|
| `app/th/services/content_generator.py` | Claude API連携の投稿文生成サービス。SYSTEM_PROMPT, STYLE_PRESETS(3種), TOPIC_PRESETS(5種), `generate_post()` |
| `app/app/console/views/content_gen.py` | 投稿文生成View: `content_generator`, `content_generate_api`, `content_schedule_api` |
| `app/app/console/templates/admin/console/content_generator.html` | 2カラムレイアウト。入力(左)+結果(右)。NGチェック結果バッジ表示。予約投稿追加モーダル |
| `app/app/console/views/scheduled_posts.py` | 予約投稿管理View: `scheduled_posts`, `scheduled_post_action_api`, `scheduled_post_create_api` |
| `app/app/console/templates/admin/console/scheduled_posts.html` | ステータス別タブ。承認/日時変更/削除/新規作成 |

#### 変更ファイル（3件）
| ファイル | 変更内容 |
|---------|---------|
| `app/app/console/urls.py` | Phase C用URL 6本 + NGチェッカーURL 2本追加 |
| `app/app/settings.py` | `ANTHROPIC_API_KEY` 環境変数追加、Jazzmin topmenu_links に「投稿文AI生成」「予約投稿管理」追加 |
| `app/requirements.txt` | `anthropic>=0.40.0` 追加 |

#### VPS設定
- `/srv/muitobem/.env` に `ANTHROPIC_API_KEY` 追加済み

## 検証結果

### Git コミット（3件）
1. `df87740` - feat: Phase C 投稿文AI生成 + 予約投稿管理（メイン実装）
2. `7421d1a` - fix: ng_word_checker.py を git 追跡に追加
3. `f2f3a76` - fix: NGワードチェッカー view/template を追加

### VPS デプロイ検証
- `git pull origin main` → 成功
- `pip install anthropic` → 成功
- `collectstatic --noinput` → 成功
- `docker compose restart django scheduler` → 成功

### HTTP 200 確認
- `content-generator/` → **200** ✅
- `scheduled-posts/` → **200** ✅
- `buzz-ng-checker/` → **200** ✅

### System check
- `System check identified no issues (0 silenced).` ✅

### エラーログ
- django コンテナログに ERROR/Exception/Traceback なし ✅

## トラブルシュート記録

### 1. プロジェクトディレクトリ間違い
- **事象**: 最初 `muitobem-platform` に実装してしまった
- **原因**: ユーザー指示を確認せず進行
- **対処**: muitobem-platform の変更を revert し、`muitobem_mirror` に再実装
- **教訓**: 作業開始前に対象プロジェクトを必ず確認する

### 2. ng_word_checker.py 未追跡
- **事象**: VPSで ModuleNotFoundError: th.services.ng_word_checker
- **原因**: ローカルにファイルは存在したが git add されていなかった
- **対処**: git add + commit + push → VPSでgit pull

### 3. NGチェッカーView未コミット
- **事象**: VPSで AttributeError: buzz.buzz_ng_checker
- **原因**: urls.py にNGチェッカーURLがあるが、対応するview関数がコミットされていなかった
- **対処**: buzz.py の変更 + buzz_ng_checker.html を commit + push

### 4. XSS セキュリティフック
- **事象**: content_generator.html で innerHTML 使用がセキュリティフックに検出された
- **対処**: DOM API（createElement, textContent）に書き換え

## 次のアクション
- [ ] ANTHROPIC_API_KEY の動作テスト（実際にAI生成を実行）
- [ ] Phase C 残機能検討（Instagram Graph API連携、パフォーマンス分析、リール生成）
- [ ] tasks/lessons.md にプロジェクトディレクトリ間違いの教訓を記録
