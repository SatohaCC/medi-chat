# 品質コマンドと証跡

以下はリポジトリルートからのコマンド。実行前に対象のpackage.jsonと環境を確認し、現在の差分と承認済み計画に必要な検証を選ぶ。
backendの依存はuv.lockで管理し、pnpmのbackendスクリプトはuv経由で実行する。backendにはPython 3.14以上と対象パッケージのdev依存が必要。通常のローカルpytestは実DB試験を除外し、DB接続・dotenv・認証情報を隔離する。実PostgreSQLはGitHub Actionsの`pnpm test:postgres`で検証する。サービス・データ・外部APIキーが必要な検証は前提を明示し、未設定による代替応答やskip・deselectedを成功としない。

pnpm-workspaceの`python.enabled=false`でpnpmの別Python環境管理を停止し、Python依存はbackendのuv.lockへ一本化する。backend/pylock.tomlはuv exportの標準形式を保持する。Node依存はルートで`pnpm install --frozen-lockfile`を実行する。一時snapshotの共有node_modulesからpackage managerを実行しない。型検査の比較にはルートの実在Pyrightを直接Nodeで起動して`--project <比較対象config>`を指定できる。

## Python

| 対象 | 読み取り専用の検証 |
|---|---|
| backendテスト | `pnpm test:backend`、限定時は`pnpm --filter backend exec pytest tests/<対象>.py` |
| 実PostgreSQL（CI） | `pnpm test:postgres`（`postgres and not source_data`。接続設定不足は失敗） |
| backendlint | `pnpm --filter backend lint` |
| backendformat確認 | `pnpm --filter backend exec ruff format --check .` |
| Python型検査（Pyright） | `pnpm typecheck:python` |

`pnpm typecheck:python`はルートのpyrightconfigによるPyrightとbackendのmypyを順に実行する。どちらか片方だけの成功を全体成功として扱わない。
カタログだけの検証は`python -c "from backend.infrastructure.package_insert_definitions.loader import get_package_insert_definitions; get_package_insert_definitions()"`。実行環境を確認し、これだけで検索・プロンプト・XML経路が検証できたと扱わない。

## frontend

| 層 | 読み取り専用の検証 |
|---|---|
| lint | `pnpm --filter frontend lint` |
| lintとformat確認 | `pnpm --filter frontend exec biome check .` |
| 型 | `pnpm typecheck:frontend` |
| ビルド | `pnpm build` |
| 接続ヘルパー単体 | `node --experimental-strip-types --test frontend/features/chat/api/chatWebSocket.test.mjs`（対応するNodeが必要） |
| チャット画面（Playwright / Chromium） | 初回は`pnpm --filter frontend exec playwright install chromium`、実行は`pnpm test:e2e` |

ルート`pnpm test`はbackend（旧data_toolsテスト移行済み）であり、frontendのNodeテストを含まない。ブラウザ・実サーバー接続も別に確認する。
`pnpm test:e2e`は通常devのdotenvと設定解決を保持し、configured PostgreSQLのread-only readiness→実`backend.main:app` OS health（3212）→モックChromium→実接続Chromiumの順に検証する。どの必須層の非0も全体非0とし、未準備/staleをfresh fixture成功で代替しない。configured要求はhealthだけで、DBの自動更新・LLM質問・Web保存をしない。占有portは拒否し、試験所有processだけを終了する。
モック層はチャット画面とイベントを検証する。実接続層は一時DB・実backendを使い、外部LLM/検出SDKの固定ダブルは実通信として扱わない。

明示的な単独実行は`pnpm --filter frontend test:e2e:mock`/`test:e2e:real`。実接続は専用Next/backendと専用test DBの所有UUID schemaを使い、APIをinterceptせず、登録・同YJ置換・一部旧版保持・参照0旧payload削除・同原本再送の非復活・OS再起動後GET/候補/検索の維持を検証する。更新対象の一時DBと、変更してはいけない運用DB/原物/backupを区別する。現行形式のfixtureは空DBへのAlembicと原本からの登録で作成し、旧索引の移行・stamp・互換読み取りを行わない。実接続試験では外部LLM keysを空・dotenv無効にし、configured smokeへ漏らさない。Next試験出力は`.next-e2e-mock`/`.next-e2e-real`（必要時buildは`.next-e2e-build`）で通常`.next`と分離する。

## 原本XML・添付文書の検証規則（内容・文脈保持と許容される表示形式差）

PMDA XML原本から添付文書データへの変換・照合（Oracle検証）では、原文の内容と文脈が完全に保持されていることを必須としつつ、以下の既存の表示形式差を許容される表現として判定規則に明記する。

1. **ブロック順序の緩和（兄弟Detail要素の先行結合）**:
   - 項目 13, 16.1, 16.6, 17.1 などにおいて、親要素に属する兄弟 Detail 要素が介在する表・図・リスト・脚注より前に結合されて段落化される（例: 16.1 で日本人志願者Detail→図→日本人表→脚注→外国人志願者Detailが、日本人+外国人統合段落→図→日本人表→脚注→外国人表となる等）。
   - すべての散文（prose）値が完全であり、親・治験・適応症の文脈が保持されている場合は、原本出現順からの並び替えを許容される既存表現とする。
2. **生成される文脈ラベル・強調段落・山括弧表現**:
   - 原本見出し（Headers）や一部の親Detailは、文脈ラベルや生成された強調段落（`<strong>`等）として展開される（項目 1, 2, 4, 7, 8, 9.2, 9.7, 16.2等）。
   - 同一のItem/Header文脈に対応する見出し反復（例: 16.1における複数の`〈単回投与〉`生成）や、既存山括弧の重複（`〈`の二重化等）は生成表示形式として扱い、余分な生XMLノードの混入と誤認しない。
3. **図（Graphic / Figure）の空段落レンダリング**:
   - 項目 16.1 および 19 などの図要素は、`figure.reference` にファイル名（例: fig05, fig06）を保持するが、HTMLレンダリングでは空段落 `<p></p>` として出力され、画像バイナリやファイル名文字列はHTML本文に現れない。
   - 性状 3.2 の InlineGraphic もプレースホルダと原本順を保持していれば、HTML本文上の空段落表現を許容する。
4. **表の `td` 出力とアクセシビリティヘッダー（`th` / `scope`）の非付与**:
   - 表（SimpleTable等）はすべて `<td>` で出力され、`<th>` や `scope` 属性を持たない。原本のヘッダー構造・グリッド・ペイロード列がセルテキストとして保持されている場合、HTML上の `th`/`scope` の欠如を既存表現として受容する。原本に指定がない限り `th`/`scope` を捏造しない。
   - 相互作用・副作用の生成列タイトルはペイロード列に存在するが、表示ヘッダーセルではない。
5. **参照（Reference）の集約レベル**:
   - 相互作用 10.1 および 10.2 の参照は、セル単位ではなく表/ブロック単位に集約され、原本の出現順・対象が表参照として保持される（SimpleTableのセル参照はセル単位で保持）。この集約レベルの差を許容する。
6. **グループ化段落内での参照重複排除**:
   - グループ化された段落内における同一参照の重複は、初出の順序を保持した上で重複排除される（例: 16.1 で 6 件 → 5 件、16.7 で 25 件 → 22 件）。出現件数の絶対一致ではなく、グループ化された意味論として許容する。

## 自動修正と最終確認

ルートと各パッケージの`check`は`--write`/`--fix`やformatを含む。Evaluatorでは使わない。書き込み役も担当外の本番・テスト・既存差分を変更しないよう対象を限定し、実際の差分を確認する。
反復中は関連するテスト、全ケース後は計画とプロジェクトに必要な品質ゲートを実行する。現在の差分に有効な証跡は再利用できる。コマンド・場所・終了コード・件数・差分版を記録し、環境エラー・未実施・skip/xfailは区別する。
この資料にコマンドがあること自体は、実行成功の証跡ではない。
