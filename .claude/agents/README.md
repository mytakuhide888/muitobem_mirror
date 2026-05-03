# .claude/agents — 思考の分割（役割別）

## 目的
単一のモデルがすべてを行う「浅い推論」を避け、責任を役割に分ける層。

## エージェント

| エージェント | 主な責務 | 発動条件の目安 |
|---|---|---|
| `architect` | システム設計／影響範囲評価 | 「設計」「アーキ」発話、3+ ファイル影響 |
| `coder` | 実装（Surgical Changes 厳守） | 単機能実装、明確な仕様 |
| `reviewer` | diff レビュー（Karpathy 4 原則を採点項目化） | PR/diff レビュー依頼 |
| `optimizer` | 性能・可読性の改善 | 既に動くコードの改善依頼 |

## 書式
各エージェントは独立 `.md` ファイルとして配置。
YAML フロントマター（name/description/tools 等）＋システムプロンプト。

## 書かないもの
- 個別の手順（→ `.claude/skills/`）
- 設計の全体像（→ `CLAUDE/project_overview.md`）
