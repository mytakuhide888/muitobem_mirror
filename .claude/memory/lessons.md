# lessons.md — 重要な学び（時系列）

高シグナル知見のみ。一般論や手順は書かない。
詳細手順は `.claude/skills/`、設計の全体像は `CLAUDE/project_overview.md`、生ログは `CLAUDE/<日付>_<連番>/summary.md` へ。

---

## 2026-02-24 — 複数プロジェクト混在環境での誤配置
- **学び**: `/home/niiya/` 配下に muitobem_mirror / muitobem-platform / netsea / sakura-ama-wowma / meta-dev.git が混在。直近の似た名前で誤って別ディレクトリに実装したことがあった。
- **回避**: 作業開始前に必ず対象プロジェクトのディレクトリを確認する。muitobem 関連は **`muitobem_mirror` がメインリポジトリ**。
- **再利用**: 似た名前のプロジェクトが並ぶ環境では「ユーザー指示の名称」と「実ディレクトリ」を最初に紐付ける。

## 2026-02-24 — git add 漏れで VPS デプロイ時 ModuleNotFoundError
- **学び**: ローカルで新規作成した `services/` 配下のファイルを `git add` し忘れ、VPS で `git pull` 後に import エラー。
- **回避**: 新規ファイル作成後は必ず `git status` で未追跡を確認。サービス層は他から import されるため漏れると即エラーになる。
- **適用**: `git add -A` は禁止（umbrella §0、機密混入防止）。**対象ファイルを明示的に指定する**ため、漏れチェックが特に重要。

## 2026-02-24 — urls.py と view の不整合
- **学び**: `urls.py` に URL 定義を追加したが、対応する view 関数を含めずコミット → 500 エラー。
- **回避**: `urls.py` 変更時は、参照先の view 関数が **同一コミット**に含まれるか確認する。

## 2026-02-24 — innerHTML は XSS リスク
- **学び**: テンプレートで `innerHTML` を使用し、セキュリティチェックで検出された。
- **回避**: ユーザー入力／API 応答を DOM に挿入する際は **`createElement` + `textContent`** を使う。`innerHTML` は禁止。
- **適用**: Threads / Instagram のテンプレートで API 応答を表示する箇所すべて。

## 2026-02-24 — `docker compose restart` は `.env` を再読み込みしない
- **学び**: `.env` に新環境変数を追加し `docker compose restart` で反映を試みたが、コンテナに変数が渡らなかった。
- **回避**: **`.env` 変更は `docker compose up -d`** を使う。`restart` は既存プロセス再起動のみ。
- **適用**: `vps-deploy` Skill の手順に組み込み済。

## 2026-05-31 — Threads リサーチ垢が凍結（research-browser + proxy 経由）
- **学び**: `research-browser/`（linuxserver/chromium、UA = Linux + Chrome）で IPRoyal 尼崎 proxy 経由ログイン → Meta が即「Linux からログイン」警告。その後 proxy 経由のフォロー連打 → 物理的に離れたスマホ実機（宝塚）からの同時アクセス → bot 検証 → SMS / 顔写真認証 → **凍結**。
- **複合要因**: ①Linux UA 露見 ②物理離隔 IP の混在（VPS proxy + 実機） ③ウォームアップ未完了で頻度上昇 ④proxy 認証ダイアログのキャンセル時に直 IP 漏れの懸念 ⑤占いアカウントへのフォロー連打。
- **回避**:
  1. リサーチ垢は **ウォームアップ期間（既定 14 日）を絶対に破らない**。`ResearchAccount.warmup_started_at` と `days_in_warmup()` を確認してから操作する。
  2. **proxy 経由ブラウザと実機を同一アカウントで同時刻に触らない**。`ResearchAccount` に運用モード（VPS/MOBILE 排他）の概念を導入する設計を別途検討。
  3. 凍結 / 警告検知時は **同端末・同指紋で次アカウントを使わない**（顔データ・端末指紋が紐づき連鎖 BAN）。Chromium プロファイル `/srv/muitobem/research-browser-config/` ごと退避してから新規セッションを作る。
  4. リサーチ用 `linuxserver/chromium` は UA 偽装だけでは Meta の指紋検知に勝てない。**能動的アクション（フォロー・いいね・投稿）はスマホ実機に寄せ、`research-browser/` は閲覧専用とする**。
- **適用**: `.claude/skills/threads-ops/SKILL.md`「垢バン回避ルール（厳守）」セクションを参照。`CLAUDE/20260531_2/summary.md` に詳細インシデント記録。

---

## 進行中作業の参照
状態スナップショット（現状ステータス・次アクション候補）は本ファイルに書かない。
- 全体像: `CLAUDE/project_overview.md`
- ロードマップ: `CLAUDE/buzz_feature_roadmap.md`
- セッション記録: `CLAUDE/<日付>_<連番>/summary.md`

本ファイルは「教訓」のみを蓄える。
