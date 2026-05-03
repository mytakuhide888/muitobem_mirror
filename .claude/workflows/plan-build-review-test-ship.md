# Workflow: Plan → Build → Review → Test → Ship

メインフロー。非自明な変更（3+ ファイル・仕様影響・新機能・複数解釈あり）はこのフローを踏む。
軽微な bug 修正（umbrella §6 自走の境界内）は Build から開始してよい。

## トリガー
- 新機能の依頼（「〜を追加して」）
- 仕様変更を含む依頼（「〜の挙動を変えて」）
- 影響範囲が不明な依頼（「〜が遅い／壊れている／統合したい」）

---

## Step 1. Plan（architect）
**呼ぶ**: `agents/architect.md`

**入力**: 要求（自然文）／関連ファイル位置／背景

**やること**:
1. 要求の言い換え（仮定を明示／不明点は AskUserQuestion）
2. 影響範囲の特定（files／DB／外部 API／UI）
3. 選択肢を最大 3 件、trade-off 表で提示
4. 推奨案＋実行ステップ（Step → verify 形式）＋ロールバック

**verify（Plan 自体の検証）**:
- [ ] 仮定が明示されているか
- [ ] 影響範囲に **全変更対象** が含まれているか
- [ ] 各 Step に検証コマンドが付いているか
- [ ] ロールバック手段が書かれているか

**出力**: `CLAUDE/<日付>_<連番>/summary.md` の「Plan」セクション

**ゲート**: 人間の承認（OK が出るまで Build に進まない）

---

## Step 2. Build（coder）
**呼ぶ**: `agents/coder.md`

**入力**: 承認済み Plan

**やること**:
1. Plan の Step を 1 つずつ最小差分で実装
2. 各 Step 完了時にローカルで構文チェック（`python3 -c "import ast; ast.parse(open('x.py').read())"`）
3. orphan の整理は自分が作った分のみ
4. 機密情報（SSH パスワード等）を残さない（`CLAUDE/ops/server.md` 経由で参照）

**verify（Build 中の検証）**:
- [ ] 全変更行が要求にトレース可能か
- [ ] 「ついで改善」が混入していないか
- [ ] ローカル構文チェック合格
- [ ] 該当 Skill（vps-deploy / docker-ops / threads-ops / instagram-ops / scheduler-ops）の手順に従ったか

**出力**:
- 変更ファイル
- `summary.md` の「実装内容」セクション

**ゲート**: 構文チェック合格＋ post-edit-pyflake hook で WARN なし

---

## Step 3. Review（reviewer）
**呼ぶ**: `agents/reviewer.md`

**入力**: 変更 diff（`git diff` 出力可）

**やること**:
1. Karpathy 4 原則を採点項目化して評価
2. プロジェクト固有チェック（機密混入・umbrella §0 違反・innerHTML 等）
3. Block / Needs work / Approve の判定

**verify**:
- [ ] 全採点項目に評価が入っているか
- [ ] 機密情報が混入していないか（`grep -r "Kuurie338" .` で 0 件）
- [ ] git 操作（add/commit/push）が AI から実行されていないか

**出力**: `summary.md` の「レビュー所見」セクション

**ゲート**: Block 指摘がない／Needs work が解消されている

---

## Step 4. Test（VPS 反映前のローカル検証 ＋ VPS 反映後の検証）
**呼ぶ**: `skills/vps-deploy/SKILL.md`

**人間が行う**: `git add` / `commit` / `push`（AI からは実行しない — umbrella §0）

**AI がやること（push 後）**:
1. VPS で `git pull`
2. 変更内容に応じて collectstatic / restart django / migrate
3. 検証コマンドを実行：
   - Django エラーゼロ確認: `docker compose logs django --since 2m | grep -E "ERROR|Exception|Traceback|500"` → 出力なし
   - HTTP 200 確認: `curl -s -o /dev/null -w "%{http_code}" -L https://muitobem.top/admin/console/<endpoint>/`
   - System check: `System check identified no issues` がログに出ているか

**verify**:
- [ ] エラーゼロ
- [ ] HTTP 200
- [ ] System check OK
- [ ] 該当機能の手動動作確認（UI 操作）

**出力**: `summary.md` の「検証結果」セクション（hook の `stop-summary-required` で空欄チェック）

**ゲート**: 全 verify 合格

---

## Step 5. Ship（記録 → 次アクション）

**やること**:
1. `summary.md` の「次のアクション」を埋める
2. 教訓があれば `.claude/memory/lessons.md` に追記（高シグナルのみ）
3. 人間に「git tag / リリースノート」要否を確認

**verify**:
- [ ] summary.md の全セクションが埋まっている
- [ ] lessons.md に転記すべき教訓がないか確認した

**ゲート**: なし（記録系）

---

## 失敗時の分岐

| Step | 失敗 | 対処 |
|---|---|---|
| Plan | 不明点あり | AskUserQuestion で確認、Plan を更新 |
| Build | 構文エラー | post-edit-pyflake の指摘箇所を修正 |
| Build | 影響範囲が想定外 | Plan に戻す（architect へ） |
| Review | Block 指摘 | Build に戻す（指摘範囲のみ修正） |
| Test | エラー検出 | エラーログから原因特定 → Build に戻す |
| Test | 503/500 | 即時ロールバック（前バージョンに git reset & restart） |

---

## 関連
- Karpathy 4 原則: umbrella `/home/niiya/CLAUDE.md` ／ `~/.claude/skills/karpathy-guidelines/SKILL.md` ／ `.cursor/rules/karpathy-guidelines.mdc`
- 教訓: [`.claude/memory/lessons.md`](../memory/lessons.md)
- セッション記録テンプレ: umbrella §1.2
