# 品質コマンドと証跡

以下はリポジトリルートからのコマンド。実行前に対象のpackage.jsonと環境を確認し、現在の差分と承認済み計画に必要な検証を選ぶ。
backendの依存はuv.lockで管理し、pnpmのbackendスクリプトはuv経由で実行する。backendにはPython 3.14以上と対象パッケージのdev依存が必要。サービス・データ・外部APIキーが必要な検証は前提を明示し、未設定による代替応答やskipを成功としない。

pnpm-workspaceの`python.enabled=false`でpnpmの別Python環境管理を停止し、Python依存はbackendのuv.lockへ一本化する。backend/pylock.tomlはuv exportの標準形式を保持する。Node依存はルートで`pnpm install --frozen-lockfile`を実行する。一時snapshotの共有node_modulesからpackage managerを実行しない。型検査の比較にはルートの実在Pyrightを直接Nodeで起動して`--project <比較対象config>`を指定できる。

## Python

| 対象 | 読み取り専用の検証 |
|---|---|
| backendテスト | `pnpm test:backend`、限定時は`pnpm --filter backend exec pytest tests/<対象>.py` |
| backendlint | `pnpm --filter backend lint` |
| backendformat確認 | `pnpm --filter backend exec ruff format --check .` |
| Python型検査（Pyright） | `pnpm typecheck:python` |

`pnpm typecheck:python`はルートのpyrightconfigを使いbackendを対象にする。各Pythonパッケージの`typecheck`はmypyであり、別の検証として扱う。
カタログだけの検証は`python -c "from backend.infrastructure.package_insert_definitions.loader import get_package_insert_definitions; get_package_insert_definitions()"`。実行環境を確認し、これだけで検索・プロンプト・XML経路が検証できたと扱わない。

## frontend

| 層 | 読み取り専用の検証 |
|---|---|
| lint | `pnpm --filter frontend lint` |
| lintとformat確認 | `pnpm --filter frontend exec biome check .` |
| 型 | `pnpm typecheck:frontend` |
| ビルド | `pnpm build` |
| 接続ヘルパー単体 | `node --experimental-strip-types --test frontend/app/lib/chatWebSocket.test.mjs`（対応するNodeが必要） |
| チャット画面（Playwright / Chromium） | 初回は`pnpm --filter frontend exec playwright install chromium`、実行は`pnpm test:e2e` |

ルート`pnpm test`はbackend（旧data_toolsテスト移行済み）であり、frontendのNodeテストを含まない。ブラウザ・実サーバー接続も別に確認する。
`pnpm test:e2e`は通常devのdotenvと設定解決を保持し、configured検索索引のread-only readiness→実`backend.main:app` OS health（3212）→モックChromium→実接続Chromiumの順に検証する。どの必須層の非0も全体非0とし、未準備/staleをfresh fixture成功で代替しない。configured要求はhealthだけで、索引の自動更新・LLM質問・Web保存をしない。占有portは拒否し、試験所有processだけを終了する。
モック層はチャット画面とイベントを検証する。実接続層は一時DB・実backendを使い、外部LLM/検出SDKの固定ダブルは実通信として扱わない。

明示的な単独実行は`pnpm --filter frontend test:e2e:mock`/`test:e2e:real`。実接続は専用Next/backendと一時SQLite/import rootを使い、APIをinterceptせず、登録・同YJ置換・一部旧版保持・参照0旧ファイル削除・同原本再送の非復活・OS再起動後GET/候補/検索の維持を検証する。更新対象の一時DBと、変更してはいけない運用DB/原物/backupを区別する。fresh prepared正常系に加えて、実旧manifest DBの整合copy→明示Alembic/初期登録CLI→同copy実browserの回帰を維持する。copy suiteでは外部LLM keysを空・dotenv無効にし、configured smokeへ漏らさない。Next試験出力は`.next-e2e-mock`/`.next-e2e-real`（必要時buildは`.next-e2e-build`）で通常`.next`と分離する。

## 自動修正と最終確認

ルートと各パッケージの`check`は`--write`/`--fix`やformatを含む。Evaluatorでは使わない。書き込み役も担当外の本番・テスト・既存差分を変更しないよう対象を限定し、実際の差分を確認する。
反復中は関連するテスト、全ケース後は計画とプロジェクトに必要な品質ゲートを実行する。現在の差分に有効な証跡は再利用できる。コマンド・場所・終了コード・件数・差分版を記録し、環境エラー・未実施・skip/xfailは区別する。
この資料にコマンドがあること自体は、実行成功の証跡ではない。
