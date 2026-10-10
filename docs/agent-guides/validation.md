# 品質コマンドと証跡

以下はリポジトリルートからのコマンド。実行前に対象のpackage.jsonと環境を確認し、現在の差分と承認済み計画に必要な検証を選ぶ。
backendの依存はuv.lockで管理し、pnpmのbackendスクリプトはuv経由で実行する。data_toolsの依存はpnpmのワークスペース設定で管理される。backendにはPython 3.14以上、data_toolsにはPython 3.12以上と対象パッケージのdev依存が必要。サービス・データ・外部APIキーが必要な検証は前提を明示し、未設定による代替応答やskipを成功としない。

## Python

| 対象 | 読み取り専用の検証 |
|---|---|
| backendテスト | `pnpm test:backend`、限定時は`pnpm --filter backend exec pytest tests/<対象>.py` |
| data_toolsテスト | `pnpm test:data`、限定時は`pnpm --filter data_tools exec pytest tests/<対象>.py` |
| backendと共通カタログlint | `pnpm --filter backend lint` |
| data_tools lint | `pnpm --filter data_tools lint` |
| backendと共通カタログformat確認 | `pnpm --filter backend exec ruff format --check . ../package_inserts` |
| data_tools format確認 | `pnpm --filter data_tools exec ruff format --check .` |
| Python型検査（Pyright） | `pnpm typecheck:python` |

`pnpm typecheck:python`はルートのpyrightconfigを使いbackend・data_tools・package_insertsを対象にする。各Pythonパッケージの`typecheck`はmypyであり、別の検証として扱う。
カタログだけの検証は`python -c "from package_inserts.catalog_loader import get_package_insert_catalog; get_package_insert_catalog()"`。実行環境を確認し、これだけで検索・プロンプト・XML経路が検証できたと扱わない。

## frontend

| 層 | 読み取り専用の検証 |
|---|---|
| lint | `pnpm --filter frontend lint` |
| lintとformat確認 | `pnpm --filter frontend exec biome check .` |
| 型 | `pnpm typecheck:frontend` |
| ビルド | `pnpm build` |
| 接続ヘルパー単体 | `node --experimental-strip-types --test frontend/app/lib/chatWebSocket.test.mjs`（対応するNodeが必要） |

ルート`pnpm test`はbackendとdata_toolsであり、frontendのNodeテストを含まない。ブラウザ・実サーバー接続も別に確認する。

## 自動修正と最終確認

ルートと各パッケージの`check`は`--write`/`--fix`やformatを含む。Evaluatorでは使わない。書き込み役も担当外の本番・テスト・既存差分を変更しないよう対象を限定し、実際の差分を確認する。
反復中は関連するテスト、全ケース後は計画とプロジェクトに必要な品質ゲートを実行する。現在の差分に有効な証跡は再利用できる。コマンド・場所・終了コード・件数・差分版を記録し、環境エラー・未実施・skip/xfailは区別する。
この資料にコマンドがあること自体は、実行成功の証跡ではない。
