# エージェント運用

設計・仕様・開発・検証手順は[docs](../docs/README.md)、実行ツールは[scripts](../scripts/README.md)に置く。

| 場所 | 内容 | Git管理 |
| --- | --- | --- |
| [guides/](guides/) | 設計・backend・frontend・テストの作業規約 | 共有 |
| [lessons/](lessons/) | 失敗記録の運用、承認待ち・承認済み記録 | 共有 |
| [archive/](archive/) | 過去の計画・レビュー・検証報告 | 共有。現在の仕様・検証結果とは区別 |
| [agents/](agents/) | 役割定義 | 共有 |
| [skills/feature-pipeline/](skills/feature-pipeline/SKILL.md) | プロジェクトの作業手順 | 共有 |
| `skills/`のその他 | 導入済みSkills | ローカルのまま保持 |
| `work/YYYYMMDD-<topic>/` | 作業単位の計画・テスト仕様・進捗・証跡 | 管理外 |
| `work/legacy/` | 移動した過去の提案・レビュー・単独検証・作業ツール | 管理外 |
| `work/.hooks/` | hooksの検査ログと結果 | 管理外 |

読む資料は[AGENTS.md](../AGENTS.md)の条件に従って選ぶ。失敗記録は[INDEX](lessons/INDEX.md)から参照し、承認待ち記録を規約として扱わない。

Feature Pipelineは明示的な開始・再開依頼がある場合だけ使い、開始時に以下のWORK_DIRを固定する。

```text
work/YYYYMMDD-<topic>/
  plan.md
  testcase.md
  progress.md
  evidence/
```

過去の記録・原本を移動しても、承認状態や当時の検証結果を書き換えない。機密情報を含み得る作業記録は共有資料へ一括追加しない。
