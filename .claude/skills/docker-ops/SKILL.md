---
name: docker-ops
description: muitobem_mirror の Docker Compose 操作（コンテナ状態確認・ログ閲覧・コンテナ内 exec・再起動・rebuild）を扱うときに使用。4 コンテナ構成（django / db / caddy / scheduler）の役割と、`restart` vs `up -d` の使い分け、ログ追跡パターンをガイドする。「docker compose」「コンテナ」「ログ確認」「rebuild」「container」のキーワードで発動。
---

# docker-ops

muitobem_mirror の Docker Compose 操作の能力単位。VPS デプロイは [`vps-deploy`](../vps-deploy/SKILL.md) を参照。

## コンテナ構成（VPS `/srv/muitobem` 上）

| サービス | 役割 | イメージ |
|---|---|---|
| `django` | Django アプリ本体（Python 3.12 / Django 5.2.4） | カスタム Dockerfile |
| `db` | MySQL 8.0 | mysql:8.0 |
| `caddy` | HTTPS リバースプロキシ | caddy:2-alpine |
| `scheduler` | 定期ジョブ実行（60 秒間隔） | カスタム Dockerfile |

## いつ使うか
- コンテナの状態を確認したい（`ps`）
- エラーログを追跡したい（`logs`）
- コンテナ内で管理コマンドを実行したい（`exec`）
- コードを反映したい（`restart` or `up -d`）
- Dockerfile / requirements を変更してビルドし直したい（`build`）

## 主要コマンド（プロジェクト名 `muitobem`）

### 状態確認
```bash
docker compose -p muitobem ps
docker compose -p muitobem logs --tail=100 django
docker compose -p muitobem logs --since 5m django | grep -E "ERROR|Exception|Traceback"
```

### コンテナ内実行
```bash
docker compose -p muitobem exec django python manage.py <command>
docker compose -p muitobem exec django python manage.py shell
docker compose -p muitobem exec db mysql -u root -p
```

### 反映（**重要：使い分け**）
```bash
# Python ファイル変更（settings.py / views.py / models.py 等）
docker compose -p muitobem restart django

# .env / docker-compose.yml の環境変数変更
# → restart では再読み込みされない！
docker compose -p muitobem up -d

# Dockerfile / requirements.txt 変更
docker compose -p muitobem build django
docker compose -p muitobem up -d django
```

## 制約・注意
- 本番では **`-p muitobem` プロジェクト名指定が必須**（複数 compose プロジェクトと衝突を避ける）
- `.env` 変更時に `restart` は効かない（教訓: 2026-02-24）
- `db` コンテナは安易に再起動しない（接続中の djangoでエラーが出る可能性）

## 関連
- VPS デプロイ: [`vps-deploy`](../vps-deploy/SKILL.md)
- 教訓: [`.claude/memory/lessons.md`](../../memory/lessons.md)
