# medi-chat 作業案内

- 既存の差分・未追跡ファイルを保持し、依頼された範囲だけを変更する。
- 対象ディレクトリに適用されるAGENTS.mdも確認する。frontend作業では`frontend/AGENTS.md`を読む。
- 未実施・環境不足・skip/xfailを検証成功として報告しない。検証した層と今回の差分を特定する。
- feature-pipelineの役割・承認手順は共通Skill/TOMLを使う。現在のケース・承認・ログをこのファイルへ書かない。

## 必要時に読む資料

役割と対象範囲の両方で選び、関連節を読む。該当する資料は必須。範囲が広がったら追加で確認する。

| 条件 | 資料 |
|---|---|
| 設計、依存方向、公開契約を計画・変更・評価する | [architecture](docs/agent-guides/architecture.md) |
| backendの契約・実装を計画・変更・評価する | [backend](docs/agent-guides/backend.md) |
| frontendの契約・実装を計画・変更・評価する | [frontend](docs/agent-guides/frontend.md) |
| テストを設計・変更・評価する | [testing](docs/agent-guides/testing.md) |
| 検証を計画・実行・評価する | [validation](docs/agent-guides/validation.md) |

進行役は委任時に必要な資料と関連節を指定する。子も不足や新しい対象に気づいたら追加確認する。読了済みで未変更の資料を毎ケース再読込せず、更新された文書・契約は現在版を確認する。
共通指示と読み込み順は安定させ、ケース・時刻・進捗・差分は後続メッセージへ置く。初期指示を毎回再構成しない。
