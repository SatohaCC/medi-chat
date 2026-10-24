# 開発ツールと品質検査

テスト本体とlint・型検査設定は`backend/`・`frontend/`が所有する。共有の実行入口は`checks/quality.mjs`。手動・CI・Codex hooksはこの入口から同じパッケージコマンドを呼ぶ。

| 場所 | 責務 |
| --- | --- |
| `checks/` | 品質検査の実行とApplication・Domainの構造検査 |
| `hooks/` | Codexイベントの解析、編集ファイル判定、整形、検査結果の返却と重複実行防止 |
| `postgres/` | PostgreSQLの初期化 |
| 直下のスクリプト | 開発サーバー起動、環境解決、生成データの出力 |

## 共通コマンド

ルートから実行する。いずれも検査対象のソースを自動修正しない。

```sh
pnpm quality                  # backend・frontend・開発ツール
pnpm quality:backend
pnpm quality:frontend
pnpm quality:scripts
pnpm typecheck:scripts        # 開発ツールのPyright・mypy
pnpm quality:changed          # HEADとの差分と未追跡ファイルから選択
pnpm quality:changed --phase quick
pnpm quality:changed --list   # 実行計画だけ表示
```

`full`は対象側のlint・format確認・型検査・単体テストを実行し、backendでは構造検査も含む。`scripts`ではツールの回帰と生成物の整合性も検査する。`quick`はlint・実行入口の構文確認に絞る。失敗・起動不能・タイムアウトは非0で終了し、他の検査も続けて結果を表示する。一時ファイルとuvキャッシュはプロジェクト内のGit管理外領域を使う。

実PostgreSQL・ブラウザ・外部APIは自動選択に含めない。必要な別コマンドと前提は[検証手順](../docs/development/validation.md)を参照する。CIは共通のbackend・scripts検査に加え、実PostgreSQL契約を実行する。

## Codex hooks

[.codex/hooks.json](../.codex/hooks.json)が登録先。

- `PostToolUse`: ファイル編集ツールの入力を解析し、編集されたPythonだけをRuff整形した後、対象側のquick検査を実行する。シェル経由の編集は終了時の差分検査で拾う。
- `Stop`: staged・unstaged・削除・未追跡を含む変更範囲のfull検査を実行する。文書のみの変更ではコード検査を起動しない。
- 同一ターン・同一内容の成功結果は再利用する。検査中に内容が変わった場合は成功を認定しない。
- 失敗時は修正を要求する。同じ内容で既に継続した場合は再度継続させず、失敗の報告を促す。環境不足を成功と扱わない。
- 結果とログは`.agents/work/.hooks/`へ保存し、Git管理しない。

hooks定義の変更後はCodex側で定義を確認・信頼する操作が必要。登録ファイルの存在と実際の自動発火は別々に確認する。[公式仕様](https://learn.chatgpt.com/docs/hooks)
