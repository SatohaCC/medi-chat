# medi-chat 作業案内

- 既存の差分・未追跡ファイルを保持し、依頼された範囲だけを変更する。
- 対象ディレクトリに適用されるAGENTS.mdも確認する。frontend作業では`frontend/AGENTS.md`とインストール済みNext.jsの対象ガイドを読み、生成される案内ブロックを削除・複製しない。
- 未実施・環境不足・skip/xfailを検証成功として報告しない。検証した層と今回の差分を特定する。
- コードを変更するすべてのエージェントは[共通品質ハーネス](scripts/README.md)を使う。受入条件のある作業では`tmp/quality/task.json`で条件と登録済みテストを対応付け、編集後は`pnpm agent:check --phase quick`、完了前は`pnpm agent:check --report tmp/quality/result.json`を実行する。失敗時はレポートの診断・修正候補を読み、成功または未解決の具体的な理由まで確認する。受入条件や検査を弱めて成功にしない。
- `AGENTS.md`と共通CLIは複数エージェント間の共有契約であり、各実行環境での自動起動を保証しない。編集・終了イベントへ自動接続する場合は、そのエージェントのHookを共通CLIのadapterとして設定する。
- feature-pipelineの役割・承認手順は共通Skillと実行環境のエージェント設定を使う。他のエージェント向けのリポジトリ内出力は[Feature Pipeline](.agents/skills/feature-pipeline/SKILL.md)と[Markdown役割定義](.agents/agents/)を参照する。明示的な開始・再開依頼がある場合だけ実行する。現在のケース・承認・ログをこのファイルへ書かない。

## 開発段階の変更方針

- 現在は開発段階であり、変更対象の旧実装・旧データ形式・旧DBとの後方互換性は不要とする。置き換えで不要になったコード・互換読み取り・移行処理・設定・テストは削除する。
- 生成データ・検索索引・開発用DBは原本から再生成・再登録して置き換えてよい。変更前のものを残すためだけの別ディレクトリ・バックアップ・並行運用は不要とする。
- 原本・手作業で作成したデータ・依頼範囲外の差分はこの方針による削除対象にしない。個別に保持の指示がある場合は、その指示を優先する。

## 失敗記録の参照と整理

- 計画前・対象範囲の拡大時、エラー後の次の修正前、完了報告前に[失敗記録と統合先の目次](.agents/lessons/INDEX.md)を照合する。該当する正本または承認済み記録の本文を読み、適用条件と確認手順を現在の対象・環境に照らす。目次だけから対策を推測しない。
- 新規候補・更新案の作成、承認、統合・廃止は[運用ルール](.agents/lessons/README.md)に従う。承認待ちは規約として適用せず、人間の承認前に承認済みへの移動・INDEX登録をしない。
- 棚卸しや規約への反映を依頼された場合は[分類・統合記録](.agents/lessons/REVIEW.md)を確認する。一般的な指示はこのファイル、対象別の規則は既存の設計・検証文書、失敗の証拠・例外条件は記録本文へ置き、同じ規則を複製しない。

## 必要時に読む資料

役割と対象範囲の両方で選び、関連節を読む。該当する資料は必須。範囲が広がったら追加で確認する。

| 条件 | 資料 |
|---|---|
| 設計、依存方向、公開契約やbackendの契約・実装を計画・変更・評価する | [backend設計](docs/architecture/backend-design.md)の対象節と「変更時の確認」 |
| Applicationの配置・公開範囲・依存を扱う | [Application規約](docs/architecture/application-architecture.md) |
| Domainの配置・公開ID・不変条件を扱う | [Domain規約](docs/architecture/domain-architecture.md) |
| frontendの契約・実装を計画・変更・評価する | [frontend作業案内](frontend/AGENTS.md)・[パッケージ設定](frontend/package.json)・[frontend検証](docs/development/validation.md#frontend) |
| 添付文書カタログ、検索、Jev、プロンプトの共通定義を扱う | [定義ソース](backend/infrastructure/package_insert_definitions/README.md) |
| テストを設計・変更・評価する | [テスト設計と検証](docs/development/validation.md)・[pytest設定](pytest.ini) |
| 検証を計画・実行・評価する、起動設定・依存環境・品質入口・CIを変更する | [validation](docs/development/validation.md) |

- backendのバージョン・lint・依存設定は`backend/pyproject.toml`を正本とする。FastAPI/Pydantic・DI・ストリーミングの変更では、適用可能なSkillと`ddd-onion-bestpractices`の関連規約を確認する。
- frontendの型・lintは対象パッケージの設定を正本とする。useEffectは接続・購読等の外部同期に使い、ユーザー操作・メッセージ処理はイベントやコールバックに置く。

進行役は委任時に必要な資料と関連節を指定する。子も不足や新しい対象に気づいたら追加確認する。読了済みで未変更の資料を毎ケース再読込せず、更新された文書・契約は現在版を確認する。
共通指示と読み込み順は安定させ、ケース・時刻・進捗・差分は後続メッセージへ置く。初期指示を毎回再構成しない。
