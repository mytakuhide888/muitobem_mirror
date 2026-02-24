# Lessons Learned

## 2026-02-24: プロジェクトディレクトリの確認
- **パターン**: 複数プロジェクト（muitobem-platform, muitobem_mirror）が存在する環境で、間違ったディレクトリに実装してしまった
- **ルール**: 作業開始前に必ず対象プロジェクトのディレクトリを確認する。`/home/niiya/` 配下には複数プロジェクトが存在する。ユーザーの指示やコンテキストから正しいプロジェクトを特定してから作業を開始すること
- **対象**: muitobem 関連は `muitobem_mirror` がメインリポジトリ

## 2026-02-24: git add 漏れに注意
- **パターン**: ローカルで新規作成したファイルを git add し忘れ、VPSデプロイ時に ModuleNotFoundError が発生
- **ルール**: 新規ファイルを作成した場合、コミット前に `git status` で未追跡ファイルがないか確認する。特にサービス層（services/）のファイルは他から import されるため、漏れると即エラーになる

## 2026-02-24: urls.py と view の整合性
- **パターン**: urls.py にURL定義を追加したが、対応するview関数がコミットされていなかった
- **ルール**: urls.py を変更する際は、参照先の全view関数が同じコミットに含まれているか確認する

## 2026-02-24: innerHTML → DOM API
- **パターン**: テンプレートで innerHTML を使用し、セキュリティフックに検出された
- **ルール**: ユーザー入力やAPI応答を表示する際は createElement + textContent を使う。innerHTML は XSS リスクがあるため禁止

## 2026-02-24: docker compose restart vs up -d
- **パターン**: `.env` に新しい環境変数を追加したが、`docker compose restart` ではコンテナに反映されなかった
- **ルール**: `.env` の変更を反映するには `docker compose up -d` を使う。`restart` は既存コンテナのプロセス再起動のみで、環境変数は再読み込みされない
