# タスク記録
## 概要
- 背景：Phase C完了後のPhase D設計・実装着手
- ゴール：AI鑑定文生成（管理画面）+ DM受信管理 + DM自動初回返信
- 影響範囲：ig/services, social/views, social/management, app/console/views, templates, urls
- 期限/優先度：高

## 現状（既存実装の調査結果）

### 使える資産（実装済み）
| 資産 | 場所 | 内容 |
|-----|------|------|
| DMMessage保存 | social/views.py + social/models.py | Webhook→DMMessage.create()は動作中 |
| send_dm / send_dm_flexible | social/services/ig_api.py | 完全実装済み |
| Job/social_worker | social/models.py + management/commands/ | キュー基盤あり（REPLY処理が未完） |
| IGDMReplyLog | ig/models.py | 送信ログモデル定義済み |
| Claude API統合 | ig/services/tarot_generator.py | 参照モデルとして流用可 |
| _schedule_auto_reply() | social/views.py | キーワードマッチはあるが args 不完全 |

### スタブ（補完が必要）
| 箇所 | 問題 |
|------|------|
| social_worker REPLY処理 | Job.args に access_token/recipient_id が未設定 |
| ig_autoreply_worker | 完全スタブ（使わない方針） |
| _schedule_auto_reply() | Job.args に token/recipient_id を追加する必要あり |

---

## Plan（設計）

### ビジネスフロー（実装する範囲）
```
[DM受信] Webhook → DMMessage保存（既存）
    ↓
[管理画面] DM受信管理 → 未読一覧 → 顧客を選択
    ↓
[AI鑑定文生成] 生年月日・悩みを入力 → Claude API → 鑑定文
    ↓
[手動送信] 「このDMに返信」ボタン → send_dm_flexible()
    ↓
[自動初回返信] キーワードトリガー → ヒアリングDMを自動送信
```

---

### Task 1: AI鑑定文生成コンソール（appraisal-gen/）★★★

**目的**: 顧客の生年月日・悩みを入力 → Claude APIで鑑定文生成 → DM手動送信

#### 新規ファイル
| ファイル | 内容 |
|---------|------|
| `ig/services/appraisal_generator.py` | Claude API連携。`generate_appraisal(birthdate, concern, divination, character_desc)` → 鑑定文テキスト |
| `console/views/appraisal.py` | View: `appraisal_gen`(GET), `appraisal_generate_api`(POST), `appraisal_send_dm_api`(POST) |
| `console/templates/appraisal_gen.html` | 2カラム: 入力フォーム(左) + 生成結果+送信フォーム(右) |

#### appraisal_generator.py の主要関数
```python
generate_appraisal(
    birthdate: str,        # 生年月日 (例: 1990/05/15)
    concern: str,          # 悩み (自由入力)
    divination: str,       # 占術 (tarot/western/numerology/shichu/seimei)
    character_desc: str,   # キャラ設定 (任意)
) -> dict  # { ok, appraisal_text, error }
```

#### 占術プリセット（5種）
| キー | 占術 |
|-----|------|
| tarot | タロット占い |
| western | 西洋占星術 |
| numerology | 数秘術 |
| shichu | 四柱推命 |
| seimei | 姓名判断 |

#### 画面構成
- 左: 生年月日・悩み・占術・キャラクター設定 + 「生成」ボタン
- 右: 生成テキスト（編集可） + 「DM送信相手」選択 + 「このDMに返信」ボタン

---

### Task 2: DM受信管理画面（dm-inbox/）★★★

**目的**: 受信DM一覧 → 顧客との会話 → AI鑑定・手動返信をワンストップで

#### 新規ファイル
| ファイル | 内容 |
|---------|------|
| `console/views/dm_inbox.py` | View: `dm_inbox`(GET), `dm_reply_api`(POST) |
| `console/templates/dm_inbox.html` | DM一覧テーブル + 会話詳細パネル + 返信フォーム |

#### 画面構成
- 左ペイン: DMMessage一覧（IG user_id別グループ・最新メッセージ・日時）
- 右ペイン: 選択した相手との会話履歴 + 返信テキスト入力 + 「鑑定文生成」リンク

#### dm_reply_api
```
POST {user_id, text, account_id}
→ DMContactから thread_key/psid を解決
→ send_dm_flexible(token, text)
→ DMMessage.objects.create(direction=OUT, ...)
→ IGDMReplyLog.objects.create(...)
```

---

### Task 3: DM自動初回返信（_schedule_auto_reply() 修正）★★☆

**目的**: DM受信時にキーワードマッチ → ヒアリングDMを自動送信

#### 変更ファイル
| ファイル | 変更内容 |
|---------|---------|
| `social/views.py` | `_schedule_auto_reply()` に account_id + access_token + recipient_id を追加 |
| `social/management/commands/social_worker.py` | REPLY 処理で token/recipient_id を Job.args から取得して send_dm() |
| `console/views/auto_reply_settings.py` (新規) | 自動返信テンプレート管理画面 |
| `console/templates/auto_reply_settings.html` (新規) | テンプレートCRUD + ON/OFF |

#### 修正内容（social/views.py）
```python
# 現在: Job.args = {"text": rule.reply_template.reply_text}
# 修正後:
Job.objects.create(
    job_type=Job.Type.REPLY,
    platform=platform,
    args={
        "text": rule.reply_template.reply_text,
        "access_token": account.best_send_token,  # ← 追加
        "recipient_id": user_id,                  # ← 追加
    },
    run_at=run_at,
)
```

---

### 実装順序
```
Task 2 (DM管理) → Task 1 (AI鑑定文) → Task 3 (自動返信)
```

**理由**:
- Task 2 はDM送信機能（手動）の基盤 → Task 1 のDM送信ボタンが依存
- Task 1 は独立して価値あり（生成→コピー→手動送信でも十分）
- Task 3 はTask 2 の DM管理が動いてから動作確認しやすい

### 変更ファイルサマリ
| 種別 | ファイル |
|-----|---------|
| 新規 | `ig/services/appraisal_generator.py` |
| 新規 | `console/views/appraisal.py` |
| 新規 | `console/views/dm_inbox.py` |
| 新規 | `console/views/auto_reply_settings.py` |
| 新規 | `console/templates/appraisal_gen.html` |
| 新規 | `console/templates/dm_inbox.html` |
| 新規 | `console/templates/auto_reply_settings.html` |
| 変更 | `social/views.py` |
| 変更 | `social/management/commands/social_worker.py` |
| 変更 | `console/urls.py` (URL 8本追加) |
| 変更 | `app/settings.py` (Jazzminメニュー追加) |

## 調査ログ
- 2026/02/25: 既存実装調査完了（Exploreサブエージェント）
  - DMMessage保存は既存Webhookで動作中
  - send_dm系APIは完全実装済み
  - _schedule_auto_reply()は args 不完全で実質未動作
  - Job/social_workerキューは基盤あり（REPLY部分だけ補完が必要）

## 実装内容（追記予定）
## 検証結果（追記予定）
## 次のアクション
- [ ] Plan 承認後 → Task 2 実装開始
