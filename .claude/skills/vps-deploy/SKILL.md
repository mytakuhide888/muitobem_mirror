---
name: vps-deploy
description: ローカル → GitHub → VPS への反映フロー（git pull、collectstatic、django コンテナ再起動、migrate、HTTP 200 検証）を扱うときに使用。本番アプリパス `/srv/muitobem`、Docker Compose 構成、`sshpass` 経由の SSH 接続をガイドする。SSH 情報は `CLAUDE/ops/server.md`（git 管理外）に集約。「VPS」「デプロイ」「git pull」「collectstatic」「migrate」「docker compose restart」「muitobem.top」のキーワードで発動。
---

# vps-deploy

VPS 反映フローの能力単位。SSH 情報・パスワード等の機密は [`CLAUDE/ops/server.md`](../../../CLAUDE/ops/server.md) を参照（git 管理外）。

## いつ使うか
- ローカルでの編集を VPS に反映したい
- マイグレーションを本番 DB に適用したい
- django コンテナを再起動したい
- 反映後の HTTP 200 確認を行いたい

## 何ができるか
1. **コード反映フロー**: `git pull` → collectstatic → django 再起動 → migrate
2. **再起動の使い分け**: Python 変更時は `docker compose restart django`、テンプレート/JS/CSS 変更時は `collectstatic`
3. **マイグレーション**: `makemigrations` → `migrate`（**VPS のみ**、ローカル WSL では Django 起動不可）
4. **検証**: docker logs ERROR grep ／ HTTP 200 確認 ／ System check 確認

## 実行（VPS のみ — sshpass 経由）

> 全コマンドのテンプレート・パスワード抽出は [`CLAUDE/ops/server.md`](../../../CLAUDE/ops/server.md) を参照。

### 標準フロー（コード変更）
```bash
# 1. git pull
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && git pull origin main'

# 2. テンプレート/JS/CSS 変更時のみ
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose exec django python manage.py collectstatic --noinput'

# 3. Python ファイル変更時
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose restart django'

# 4. models.py 変更時
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose exec django python manage.py migrate'
```

## 検証（完了の定義）

### Django エラーゼロ確認
```bash
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'cd /srv/muitobem && docker compose logs django --since 2m 2>&1 | grep -E "ERROR|Exception|Traceback|500"'
```
→ 出力なし = OK

### HTTP 200 確認
```bash
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no django@160.251.140.93 \
  'curl -s -o /dev/null -w "%{http_code}" -L https://muitobem.top/admin/console/<endpoint>/'
```

### System check 確認
ログに `System check identified no issues` が出ていること。

## 制約・注意
- ローカル WSL では Django 起動不可 → **migrate / makemigrations / runserver は VPS のみ**
- `.env` を変更した場合は `docker compose restart` ではなく `docker compose up -d`（教訓: `.claude/memory/lessons.md`）
- `umbrella §0`：git add / commit / push は人間が実施。AI は `git pull`（読み取り）と `git status` / `git diff` / `git log` のみ。

## 関連
- 機密情報: [`CLAUDE/ops/server.md`](../../../CLAUDE/ops/server.md)
- 教訓: [`.claude/memory/lessons.md`](../../memory/lessons.md)
- Skill: [`docker-ops`](../docker-ops/SKILL.md)
