# .claude/memory — 長期知能

## 目的
教訓・パターン・回避策を高シグナルのみ蓄積する層。
状態スナップショットや進行中作業は書かない（それらは `CLAUDE/<日付>/summary.md` や `CLAUDE/project_overview.md` へ）。

## ファイル
- `lessons.md` — 時系列の教訓ログ。

## 書く基準
- 「次回も同じミスを繰り返しそうな知見」
- 「コードを読むだけでは分からない背景・経緯」
- 「再発防止のためのルール」

## 書かない基準
- 一般論（「テストを書こう」等）
- 手順（→ `.claude/skills/`）
- 設計（→ `CLAUDE/project_overview.md`）
- 進行中タスク（→ `CLAUDE/<日付>/summary.md`）
