# 委任・記録の規約

進行役が読む。子へ全文を渡さず、担当者共通規約と役割に必要な情報だけ渡す。

## 起動と進行

- 新規起動は原則`fork_turns="none"`。元の要件、役割定義と共通規約のパス、`PLAN_PATH`・`TESTCASE_PATH`、担当範囲、承認版、作業単位・方式、品質コマンド、BASELINEと前段証跡の参照先を渡す。
- AGENTS.mdに従い対象領域に必要な資料と関連節だけを指定する。Generatorはテスト作成から本番実装・Refactor・検証まで一依頼で進め、Evaluatorには実装担当と別のエージェントで元の要件・承認済み文書・現在のGit差分・`tmp/quality/task.json`・`tmp/quality/result.json`を参照させる。

## 推論量

モデル・権限は呼び出し元を継承し、ユーザーが明示変更しない限り下表を適用する。

| 役割 | 推論量 | 判断 |
|---|---|---|
| Planner | medium（既定） | 曖昧な公開契約・複雑な設計はhigh |
| Test Designer | medium（固定） | 複雑な仕様でも自動で変更しない |
| Generator | medium（既定） | 複雑なドメイン・横断変更ではhighを明示できる |
| Evaluator | medium（固定） | 必須検証と要件からの評価も同じ設定 |

## 機械的証跡と状態管理

手動の進捗Markdownは作成せず、次の機械的証跡と承認済み文書で状態を管理する。

- **承認済み仕様**: `PLAN_PATH`（計画・受入条件）と`TESTCASE_PATH`（テスト仕様・ケースID）。承認後に実装進捗の転記で書き換えない。
- **ケースと実テストの対応**: `tmp/quality/task.json`で要件/ケースID・受入条件・実テスト（ファイルパスとselector）を結び付ける。TESTCASE_PATHへの実テスト位置の手動転記は行わない。
- **検証証跡と差分状態**: `pnpm agent:check --report tmp/quality/result.json`（および`.agents/work/.hooks/`のレシート・レポート）と`git status --short` / `git diff`を正本とする。現在の差分に対して有効な証跡かを確認し、子の自己申告だけで完了としない。
