---
name: scheduler-ops
description: scheduler コンテナによる定期ジョブ運用（60 秒間隔の `th_run_due_posts` / `th_buzz_run_scheduled` / 06:00 1 回の `th_buzz_auto_pipeline`）を扱うときに使用。`flock` による多重起動防止、ジョブ追加手順、ログ追跡、トラブルシュートをガイドする。「scheduler」「定期ジョブ」「予約投稿」「flock」「th_run_due_posts」「th_buzz_auto_pipeline」のキーワードで発動。
---

# scheduler-ops

定期ジョブ運用の能力単位。本体は `docker-compose.yml` の `scheduler` サービスで定義されている（60 秒間隔ループ）。

## 構成（現状）
`scheduler` コンテナは無限ループで以下を走らせる：

| 頻度 | コマンド | 用途 |
|---|---|---|
| 60 秒毎 | `th_run_due_posts` | Threads 予約投稿の実行 |
| 60 秒毎 | `th_buzz_run_scheduled` | バズリサーチ・スケジュール実行 |
| 06:00（1 日 1 回） | `th_buzz_auto_pipeline` | バズ自動巡回パイプライン |

各ジョブは **`flock`** で多重起動を防止（`/tmp/th_scheduler.lock` 等）。
06:00 の 1 日 1 回ジョブは `/tmp/pipeline_done_today` センチネルで重複実行を回避。

## いつ使うか
- 予約投稿が動かない／遅延しているとき
- 新しい定期ジョブを追加したいとき
- scheduler コンテナのログを追跡したいとき
- ジョブ実行間隔を変更したいとき

## 主要操作

### ログ確認
```bash
docker compose -p muitobem logs --tail=200 scheduler
docker compose -p muitobem logs --since 5m scheduler | grep -E "ERROR|Exception|Traceback"
```

### scheduler 単独再起動
```bash
docker compose -p muitobem restart scheduler
```

### 手動トリガ（scheduler を待たずに実行）
```bash
docker compose -p muitobem exec django python manage.py th_run_due_posts -v 2
docker compose -p muitobem exec django python manage.py th_buzz_run_scheduled -v 2
docker compose -p muitobem exec django python manage.py th_buzz_auto_pipeline -v 2
```

### ロック状態確認
```bash
docker compose -p muitobem exec scheduler ls -la /tmp/*.lock /tmp/pipeline_done_today
```

## ジョブ追加手順
1. `app/<app>/management/commands/<new_command>.py` を作成
2. `docker-compose.yml` の `scheduler` サービスの `command:` に
   `flock -n /tmp/<name>.lock -c "python manage.py <new_command>" || true;` を追記
3. `docker compose -p muitobem up -d scheduler`（restart ではなく up -d。コマンド変更は再生成が必要）
4. `logs --tail=20 scheduler` で初回起動を確認

## トラブルシュート

### 予約投稿が走らない
- `THScheduledPost.status` が `SCHEDULED` か確認
- `scheduled_at` が過去日時か確認
- `docker compose logs scheduler | grep th_run_due_posts` で実行履歴を確認
- `/tmp/th_scheduler.lock` が残ったままなら（前回プロセスが停止していない可能性）削除

### 06:00 ジョブが今日走ったか確認
```bash
docker compose -p muitobem exec scheduler test -f /tmp/pipeline_done_today && echo "実行済" || echo "未実行"
```

## 制約・注意
- scheduler は **django コンテナと別プロセス** → コード変更時は **両方再起動が必要**
- `/tmp/pipeline_done_today` はコンテナ再起動で消える（再起動した日は 06:00 に再実行され得る）
- 複数 scheduler コンテナを誤って立ち上げない（flock があるが二重作成は無駄）

## 関連
- Threads ジョブ: [`threads-ops`](../threads-ops/SKILL.md)
- Docker 操作: [`docker-ops`](../docker-ops/SKILL.md)
- VPS 反映: [`vps-deploy`](../vps-deploy/SKILL.md)
