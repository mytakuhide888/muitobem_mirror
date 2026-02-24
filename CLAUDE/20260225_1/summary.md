# タスク記録
## 概要
- 背景：Phase C 集客自動化 — ANTHROPIC_API_KEY動作確認済み。残機能（Instagram Graph API実装・投稿パフォーマンス分析・リール3択タロット生成）の設計・実装
- ゴール：Instagram投稿管理コンソール + パフォーマンス分析画面 + タロットリール生成 を実装
- 影響範囲：ig/services, app/console/views, app/console/templates, urls.py, management/commands
- 期限/優先度：中〜高

## 現状（事実）

### 既存実装（使える資産）
| ファイル | 内容 |
|---------|------|
| `ig/models.py` | InstagramBusinessAccount, IGPost, IGScheduledPost 定義済み |
| `ig/services/instagram_api.py` | stub（ログのみ） |
| `social/services/ig_api.py` | Graph API実装済み: create_media, publish_media, fetch_insights_ig_user, fetch_insights_media, send_dm, fetch_comments, reply_comment |
| `social/services/meta_tokens.py` | トークン管理 (ensure_fresh_page_token_by_igbiz) |
| `th/services/content_generator.py` | Claude API投稿文生成（Threads版、参照モデル）|
| `app/console/views/content_gen.py` | 投稿文生成View（Threads版、参照モデル）|
| `app/console/views/scheduled_posts.py` | 予約投稿管理View（Threads版、参照モデル）|

### 未実装（今回対象）
- Instagram用 投稿管理コンソール画面
- IGPost への定期インサイト取得 → 分析画面
- タロットリール生成（Claude API → IGScheduledPost）

## Plan（設計）

### Task 1: Instagram投稿管理コンソール（ig_post_manager）

**目的**: Instagramに画像/リールを投稿・管理できる管理画面

#### 新規ファイル
| ファイル | 内容 |
|---------|------|
| `ig/services/ig_poster.py` | Graph API連携の投稿サービス。`post_image()`, `post_reel()`, `sync_posts()` |
| `app/console/views/ig_posts.py` | View: `ig_post_manager`, `ig_post_api`, `ig_posts_sync_api` |
| `app/console/templates/admin/console/ig_post_manager.html` | 2カラム: 投稿フォーム(左) + 投稿一覧(右) |

#### 変更ファイル
| ファイル | 変更 |
|---------|------|
| `app/console/urls.py` | URL 3本追加: `ig-posts/`, `api/ig/post/`, `api/ig/posts-sync/` |
| `app/app/settings.py` | Jazzmin topmenu_links に「IG投稿管理」追加 |

#### ig_poster.py の主要関数
```
post_image(account, caption, image_url) → IGPost
post_reel(account, caption, video_url) → IGPost
sync_posts(account) → int  # DBに保存した件数
```

#### 投稿フロー（Instagram Graph API）
```
1. POST /{ig_user_id}/media  → creation_id取得
   params: caption, image_url or video_url, media_type(IMAGE/REELS)
2. POST /{ig_user_id}/media_publish → 公開
   params: creation_id
3. IGPostに保存
```

---

### Task 2: 投稿パフォーマンス分析

**目的**: 自分のIG投稿のER・インプレッション・フォロワー変化を自動追跡し可視化

#### 新規ファイル
| ファイル | 内容 |
|---------|------|
| `ig/services/insights_fetcher.py` | インサイト取得サービス。`fetch_post_insights()`, `fetch_account_insights()` |
| `app/console/views/post_analytics.py` | View: `post_analytics`, `post_insights_refresh_api` |
| `app/console/templates/admin/console/post_analytics.html` | Chart.js グラフ + 投稿テーブル |
| `ig/management/commands/ig_fetch_insights.py` | 管理コマンド（定期実行用）|

#### 変更ファイル
| ファイル | 変更 |
|---------|------|
| `ig/models.py` | IGPostInsight モデル追加（投稿IDに紐づくスナップショット）|
| `ig/migrations/` | 0005_igpostinsight.py |
| `app/console/urls.py` | URL 2本追加 |
| `app/app/settings.py` | Jazzmin topmenu_links に「パフォーマンス分析」追加 |

#### IGPostInsight モデル（新規）
```python
class IGPostInsight(models.Model):
    post = ForeignKey(IGPost)
    impressions = IntegerField(null=True)
    reach = IntegerField(null=True)
    likes = IntegerField(null=True)
    comments = IntegerField(null=True)
    shares = IntegerField(null=True)
    saved = IntegerField(null=True)
    recorded_at = DateTimeField(auto_now_add=True)
```

#### 分析画面の構成
- 上段: アカウントサマリ（直近7日インプレッション/リーチ/フォロワー増）
- 中段: Chart.js折れ線グラフ（インプレッション/ER推移）
- 下段: 投稿テーブル（ER・いいね・インプレッション降順、NGチェッカーリンク付き）

---

### Task 3: リール3択タロット生成

**目的**: Claude APIで「今日の3択タロット」投稿文を生成→IGScheduledPostに登録→Instagram投稿

#### 新規ファイル
| ファイル | 内容 |
|---------|------|
| `ig/services/tarot_generator.py` | Claude APIラッパー。`generate_tarot_options(theme)` → 3択テキスト+解説 |
| `app/console/views/tarot_reel.py` | View: `tarot_reel_gen`, `tarot_generate_api`, `tarot_schedule_api` |
| `app/console/templates/admin/console/tarot_reel_gen.html` | 生成UI: テーマ入力→3択プレビュー→予約登録 |

#### 変更ファイル
| ファイル | 変更 |
|---------|------|
| `app/console/urls.py` | URL 3本追加 |
| `app/app/settings.py` | Jazzmin topmenu_links に「タロットリール生成」追加 |

#### 生成フォーマット（Claude出力）
```
今日の#タロット占い🃏

あなたが引くカードは…

🅰️ [カードA名]
🅱️ [カードB名]
🅲️ [カードC名]

どれを選んだ？コメントで教えて✨

---解説（後から返信用）---
🅰️ [カードA意味・今週のメッセージ]
🅱️ [カードB意味・今週のメッセージ]
🅲️ [カードC意味・今週のメッセージ]
```

#### テーマプリセット（5種）
- 恋愛運 / 金運 / 仕事運 / 全体運 / 人間関係

---

## 実装順序

```
Task 1 (IG投稿管理) → Task 3 (タロット生成) → Task 2 (パフォーマンス分析)
```

**理由**:
- Task 2 はIGPost実データが必要 → Task 1 完了後に価値が出る
- Task 3 は content_generator.py がモデルになり実装しやすい
- Task 1・3 はインサイトAPIトークン不要（投稿トークンのみ）で独立して動作確認可能

## 調査ログ
- 2026/02/25: 既存実装確認完了
  - social/services/ig_api.py に create_media / publish_media / fetch_insights_media など主要API実装済み
  - ig/models.py に IGPost / IGScheduledPost 定義済み
  - ig/services/instagram_api.py は stub のまま（今回 ig_poster.py を新規作成して ig/services 内に追加）
  - content_generator.py / scheduled_posts.py を Threads版モデルとして流用可能

## 実装内容（追記予定）

## 検証結果（追記予定）

## 次のアクション
- [ ] Plan 承認後 → Task 1 実装開始
