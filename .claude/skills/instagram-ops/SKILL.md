---
name: instagram-ops
description: Instagram（Meta Graph API）の業務オペレーション（Webhook 受信・購読確認・自動返信・インサイト取得）を扱うときに使用。`ig_webhook_*` / `ig_autoreply_worker` / `ig_fetch_insights` 管理コマンド、`ig/services/` 配下の API クライアント、`webhooks/` の署名検証をガイドする。実装完成度は 20%（モデル・Webhook のみ、API はスタブ）。「Instagram」「インスタ」「ig_webhook」「ig_autoreply」「graph API」「IGAccount」のキーワードで発動。
---

# instagram-ops

Instagram 業務の能力単位。設計概要は [`CLAUDE/project_overview.md`](../../../CLAUDE/project_overview.md) を、機能仕様は [`Insta_func.md`](../../../Insta_func.md) を参照。

## 完成度
**約 20%**：モデル定義・Webhook 受信・自動返信ワーカーは実装済。
ただし **`ig/services/` の API はスタブ多数**。実投稿・実取得は未実装。

## いつ使うか
- Webhook 受信・購読の確認をしたい
- 自動返信ワーカーを動かしたい
- インサイトを取得したい（実装は SP-API より先）

## 主要モジュール

### サービス層（`app/ig/services/`）
- API クライアント（多くがスタブ実装）

### 管理コマンド（`app/ig/management/commands/`）
| コマンド | 用途 |
|---|---|
| `ig_webhook_check` | Webhook 購読状況の確認 |
| `ig_webhook_subscribe` | Webhook 購読 |
| `ig_autoreply_worker` | 自動返信ワーカー |
| `ig_fetch_insights` | インサイト取得 |
| `ig_seed_autoreplies` | 自動返信テンプレ初期投入 |

### Webhook（`app/webhooks/`）
- `views.py`: Meta Webhook 受信エンドポイント（署名検証必須）
- `urls.py`: ルーティング

## 実行（VPS のみ）

```bash
# Webhook 状態確認
docker compose -p muitobem exec django python manage.py ig_webhook_check

# 自動返信ワーカー（通常は scheduler コンテナで定期実行）
docker compose -p muitobem exec django python manage.py ig_autoreply_worker

# インサイト取得
docker compose -p muitobem exec django python manage.py ig_fetch_insights
```

## モデル（`app/ig/models.py`）
Threads と対称構造：
- `IGAccount`
- `IGPost` / `IGScheduledPost`
- `IGDMThread` / `IGDMMessage`
- `IGAutoReplyTemplate` / `IGAutoReplyRule`
- `IGWebhookEvent`

## 制約・注意
- **Webhook 署名検証必須**：`webhooks/views.py` の検証ロジックを外さない。
- **APIスタブ**：`ig/services/` の関数を呼んでも実際の Graph API へは行かない場合がある → 実装前に該当関数を Read で確認すること。
- **NG ワードチェック必須**：Threads と同様に全出力に通す。
- **トークン管理**：`sns_core/` の Meta トークンモデルを使う（Threads と共通）。

## 関連
- 機能仕様: [`Insta_func.md`](../../../Insta_func.md)
- Threads（参考実装）: [`threads-ops`](../threads-ops/SKILL.md)
- Webhook 受信元: [`webhooks/`](../../../app/webhooks/)
