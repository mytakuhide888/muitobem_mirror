# muitobem プロジェクト指示書
## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## プロジェクト概要

占いコンテンツのSNS自動化・収益化プラットフォーム。
Django + MySQL + Docker Compose で構成。

- **ドメイン**: https://muitobem.top/admin/
- **VPS**: ConoHa VPS (160.251.140.93)
- **リポジトリ**: https://github.com/mytakuhide888/muitobem_mirror

## ⚠️ セッション開始時の必須読み込み（毎回実行すること）

**チャット開始時に必ず以下を全て読み込む。読み飛ばし禁止。**

```
docs/handover_summary.md       # SSH接続情報・デプロイ手順・引き継ぎ事項
docs/implementation_plan.md    # 実装計画履歴
docs/task.md                   # 残タスク一覧
docs/sankou/                   # 参考資料要約（全ファイル）
CLAUDE/project_overview.md     # 技術概要
CLAUDE/buzz_feature_roadmap.md # バズ機能ロードマップ
```

`docs/handover_summary.md` には **SSH接続方法・デプロイコマンド** が記載されている。
必ず読んでから作業を開始すること。読んでいない場合は作業開始前に読む。

## 必読ドキュメント（優先順）

1. **引き継ぎ資料** → `docs/handover_summary.md` ← **SSH/デプロイ情報はここ**
2. **全体戦略** → `CLAUDE/strategy/fortune_business_strategy.md`
   - 全12章構成。事業本質、顧客心理、ブランディング、コンテンツ戦略、プラットフォーム戦略、ファネル設計、価格設計、顧客対応、AI占い術、コンセプト設計、法令遵守、実装ロードマップ
3. **プロジェクト技術概要** → `CLAUDE/project_overview.md`
4. **バズ機能ロードマップ** → `CLAUDE/buzz_feature_roadmap.md`
5. **運用方針** → `CLAUDE/20260208_2/operation_strategy.md`
6. **参考資料（原文）** → `docs/sankou/`, `CLAUDE/sankou/`

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

## 開発フロー・デプロイ手順（修正・テスト工程管理）

### ローカル作業（WSL: ~/muitobem_mirror）

```bash
# ファイル修正後
git add <変更ファイル>           # 対象ファイルのみ明示的に add（git add -A は禁止）
git commit -m "feat: ..."
git push origin main
```

### VPS デプロイ（sshpass経由、パスワード認証）

```bash
# 1. git pull
sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && git pull origin main'

# 2. staticファイル収集（テンプレート/JS/CSS変更時）
sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose exec django python manage.py collectstatic --noinput'

# 3. djangoコンテナ再起動（Pythonファイル変更時）
sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose restart django'

# 4. マイグレーション（models.py変更時のみ）
sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose exec django python manage.py migrate'
```

### テスト検証工程（完了の定義）

1. **Djangoエラーゼロ確認**
   ```bash
   sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
     'cd /srv/muitobem && docker compose logs django --since 2m 2>&1 | grep -E "ERROR|Exception|Traceback|500"'
   ```
   → 出力なし = OK

2. **対象URLの HTTP 200 確認**
   ```bash
   sshpass -p '[REDACTED-PASSWORD]' ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
     'curl -s -o /dev/null -w "%{http_code}" -L https://muitobem.top/admin/console/<endpoint>/'
   ```

3. **System check 確認**（ログに `System check identified no issues` があること）

### SSH接続情報
- **ホスト**: 160.251.140.93
- **ユーザー**: django
- **パスワード**: `[REDACTED-PASSWORD]`（sshpass経由で使用）
- **アプリディレクトリ**: `/srv/muitobem`
- **ドメイン**: https://muitobem.top/admin/

## コーディング原則

- テンプレートはJazzmin管理画面のbase_site.htmlを継承
- 新機能は既存のモデル構造（social_core基底クラス）に準拠
- Threads APIは `social/services/threads_api.py` を使用
- 環境変数は `.env` で管理（docker-compose.ymlで参照）
- NGワード・法令チェックは全出力に適用（第11章参照）

## 現在のPhase

**Phase A完了（2/23）→ Phase B完了（2/24）**

- Phase A: 投稿パターン分析・構造化分析メモ・自動巡回パイプライン
- Phase B: fortune_classifier改善・アカウント比較画面・類似アカウント自動発見
- 次のPhase: `CLAUDE/buzz_feature_roadmap.md` を参照
