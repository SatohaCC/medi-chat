---
name: feature-pipeline
description: 機能追加・振る舞い変更を、計画・テスト仕様の承認、作業に応じたテスト先行・回帰検証、評価、完了報告で進める。明示的な開始・再開依頼時だけ使い、通常の実装依頼やSkillへの言及・設定変更では実行しない。
---

# Feature Pipeline

`$feature-pipeline <要件>` または `/feature-pipeline <要件>` で開始する。Planner・Test Designer・Generator（テストと本番の統合実装役）・Evaluatorの4役で進める。
進行順は計画書承認 → テストケース（テスト仕様）承認 → テスト先行または変更前後の回帰検証 → 評価 → 完了報告。
ユーザー承認の対象は計画書とテストケースの2つだけ。承認後は実装・検証・評価・修正・再評価まで進め、実装や評価結果への追加承認は求めない。単独の役割の依頼ではその範囲だけを行う。

## 呼び出し条件

ユーザーが明示的に開始・再開を指示した場合だけ適用する。通常の機能追加・バグ修正・計画・テスト依頼や、Skill名・リンクの言及だけでは起動しない。`agents/openai.yaml`の`policy.allow_implicit_invocation: false`を維持する。

## 開始・再開と役割

進行役は開始時に[委任・記録の規約](references/orchestration.md)を読む。子には自身の役割定義と[担当者共通規約](references/agent-contract.md)を渡し、このSkill全体は読ませない。

- 適用されるAGENTS.mdと対象資料、本番・テストの編集範囲、品質コマンドと必要な環境を特定する。
- `git status --short`をBASELINE_STATUSとして確認し、既存差分・未追跡内容を保持する。
- 承認対象文書は下の2パスのみ。ケースと実テストの対応は`tmp/quality/task.json`、実行証跡は`tmp/quality/result.json`（および`.agents/work/.hooks/`）で機械的に管理し、手動の進捗Markdownは作成しない。再開時は承認履歴・2文書・現在のGit差分・機械的証跡を照合して未完了段階から続ける。

| 起動名 | 定義 | 編集範囲 |
|---|---|---|
| `planner` | [Planner](../../agents/planner.md) | `PLAN_PATH` (`for-llm/plan/YYYYMMDD-<topic>.md`) |
| `test-designer` | [Test Designer](../../agents/test-designer.md) | `TESTCASE_PATH` (`for-llm/testcase/YYYYMMDD-<topic>.md`) |
| `generator` | [Generator](../../agents/generator.md) | 計画に含まれるテスト・Fixture・Fake・本番側、`tmp/quality/task.json` |
| `evaluator` | [Evaluator](../../agents/evaluator.md) | ソース編集なし、評価と必要な検証 |

同じ作業ツリーで書き込み段階を同時実行しない。Evaluatorは実装担当と別のエージェントにし、実装担当の自己評価を結論として渡さない。

## 段階

1. **計画**: Plannerへ目的・範囲・公開契約・受入条件・検証方法を依頼し、ユーザーの計画承認を待って次へ進む。
2. **テスト仕様**: Test Designerへ要件とケースの対応、前提・操作・期待結果、必要な検証層と作業方式を依頼し、ユーザーの仕様承認を待つ。
3. **実装・検証**: Generatorへ方式（バグ・重要ルールは小単位TDD、通常機能はテスト先行、構造整理は変更前後Green確認）・対象ケース群・編集範囲を渡す。テスト作成から本番実装・Refactor・`pnpm agent:check --report tmp/quality/result.json`まで一依頼で進め、完了後にEvaluatorへ進む。
4. **評価と完了報告**: 追加承認を挟まずEvaluatorへ依頼し、要件→ケース→テスト・実装・機械的証跡（`tmp/quality/task.json`・`tmp/quality/result.json`）を照合する。未実施・skip・xfail・環境不足は成功に含めない。

## 変更前失敗・差し戻し・判定

- 変更前に失敗がある場合、「既存」という理由だけで必須ゲートから除外しない。承認済み計画・仕様で除外条件が明記され、前後比較で悪化がない場合のみ範囲内評価へ進める。
- 要件・範囲・公開契約・受入条件の変更はPlanner、検証条件・期待結果・ケースの追加/削除はTest Designerへ戻し、再承認を得る。意味と検証範囲を保つ命名・重複整理・Fixture/Fake修正はGeneratorで進める。

| 判定 | 進行役の処理 |
|---|---|
| PASS | 要件・受入条件・全ケース・必須検証を満たした場合のみ。評価・最終差分・検証した層・残余リスクを提示して完了する |
| NEEDS_REVISION | 本番・テスト修正はGenerator、ケース漏れはTest Designer、要件・設計はPlannerへ戻す（自動修正・再評価は最大2回） |
| FAIL | 設計や前提が成立しない場合は停止し、理由と判断事項を示す |
