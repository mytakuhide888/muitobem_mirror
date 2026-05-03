# .claude/workflows — 自動化レイヤー（フロー定義）

## 目的
Plan → Build → Review → Test → Ship のような完全なフローを定義する層。
各ステップは skill または agent に委譲する。

## ワークフロー
- `plan-build-review-test-ship.md` — メインフロー（汎用）

## 書式
各ワークフローは独立 `.md` ファイル。
- 入力（トリガー条件）
- 各ステップとその検証
- 各ステップで呼ぶ skill / agent
- 失敗時の分岐

## 書かないもの
- 個別コマンドの詳細（→ skill から呼ぶ）
- 役割定義（→ agent）
