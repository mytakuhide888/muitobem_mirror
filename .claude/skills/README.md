# .claude/skills — 実行エンジン（再利用可能な能力単位）

## 目的
プロジェクト固有の手順を Skill として独立配置し、AI が必要時に発動できる層。

## Skill 一覧

| Skill | カバー範囲 |
|---|---|
| `vps-deploy` | sshpass 経由の VPS 反映フロー（git pull → collectstatic → restart → migrate → 検証） |
| `docker-ops` | Docker Compose 操作（4 コンテナ構成 / restart vs up -d / logs / exec） |
| `threads-ops` | Threads（Meta API）業務（投稿・バズリサーチ・コンセプト分析・自動投稿） |
| `instagram-ops` | Instagram（Graph API）業務（Webhook・自動返信・インサイト） |
| `scheduler-ops` | 定期ジョブ運用（60 秒ループ・flock・06:00 パイプライン） |

## 書式
各 Skill は `<name>/SKILL.md` で配置。
YAML フロントマター（name / description）＋本文で構成。
description には**発動キーワード**を含める。

## 書かないもの
- 役割定義（→ `.claude/agents/`）
- 自動化フロー全体（→ `.claude/workflows/`）
- 機密情報（→ `CLAUDE/ops/server.md`）
