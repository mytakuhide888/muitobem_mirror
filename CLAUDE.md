# muitobem プロジェクト指示書

## プロジェクト概要

占いコンテンツのSNS自動化・収益化プラットフォーム。
Django + MySQL + Docker Compose で構成。

- **ドメイン**: https://muitobem.top/admin/
- **VPS**: ConoHa VPS (160.251.140.93)
- **リポジトリ**: https://github.com/mytakuhide888/muitobem_mirror

## 必読ドキュメント（優先順）

1. **全体戦略** → `CLAUDE/strategy/fortune_business_strategy.md`
   - 全12章構成。事業本質、顧客心理、ブランディング、コンテンツ戦略、プラットフォーム戦略、ファネル設計、価格設計、顧客対応、AI占い術、コンセプト設計、法令遵守、実装ロードマップ
2. **プロジェクト技術概要** → `CLAUDE/project_overview.md`
3. **バズ機能ロードマップ** → `CLAUDE/buzz_feature_roadmap.md`
4. **運用方針** → `CLAUDE/20260208_2/operation_strategy.md`
5. **参考資料（原文）** → `docs/sankou/`, `CLAUDE/sankou/`

## アーキテクチャ

```
Docker Compose (4コンテナ):
  django  - メインアプリ (Python 3.12 / Django 5.2.4)
  db      - MySQL 8.0
  caddy   - リバースプロキシ (HTTPS自動)
  scheduler - 定期ジョブ (60秒間隔)
```

### Djangoアプリ構成

| アプリ | 役割 | 完成度 |
|--------|------|--------|
| th/ | Threads API連携・バズリサーチ | 80% |
| ig/ | Instagram機能 | 20% |
| social/ | SNS共通基盤・Threads API | — |
| social_core/ | ベースモデル定義 | — |
| sns_core/ | Metaトークン管理 | — |
| webhooks/ | Webhook受信 | — |
| app/console/ | カスタム管理画面 | — |

## 開発フロー

```bash
# ローカル (WSL)
cd ~/muitobem_mirror && git add . && git commit -m "msg" && git push

# VPS デプロイ
ssh muitobem-vps
cd ~/muitobem_mirror && git pull
docker compose -p muitobem up -d --build
docker compose -p muitobem exec django python manage.py migrate
```

## コーディング原則

- テンプレートはJazzmin管理画面のbase_site.htmlを継承
- 新機能は既存のモデル構造（social_core基底クラス）に準拠
- Threads APIは `social/services/threads_api.py` を使用
- 環境変数は `.env` で管理（docker-compose.ymlで参照）
- NGワード・法令チェックは全出力に適用（第11章参照）

## 現在のPhase

**Phase 1完了 → Phase A（コンセプト分析強化）に着手可能**

詳細は `CLAUDE/strategy/fortune_business_strategy.md` 第12章を参照。
