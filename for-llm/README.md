# エージェント向け資料

正式な設計・仕様・開発・運用資料は [docs](../docs/) に置きます。このディレクトリにはエージェント向けの作業案内と作業記録を置きます。

## 共有する資料

| 場所 | 内容 |
| --- | --- |
| [guides/](guides/) | 設計・backend・frontend・テスト・検証の作業案内 |
| [lessons/](lessons/) | 失敗記録の運用、承認待ち・承認済み記録 |
| [archive/](archive/) | 過去の計画・レビュー・検証報告。現在の仕様や検証結果とは区別する |

読む資料は [AGENTS.md](../AGENTS.md) の条件に従って選びます。失敗記録は [INDEX](lessons/INDEX.md) から参照し、承認待ち記録を規約として扱いません。
Skill・役割定義は既存の [.agents](../.agents/) に置きます。

## ローカルの作業記録

以下はGit管理外です。機密情報を含み得るログ・設定・証跡を共有資料へ一括追加しないでください。

| 場所 | 内容 |
| --- | --- |
| `work/YYYYMMDD-<topic>/` | 作業単位の計画・テスト仕様・進捗・証跡 |
| `proposals/` | 未確定の設計案 |
| `reviews/` | PR本文・レビュー取得結果などの作業用資料 |
| `validation/` | 単独の検証ログ・JUnit結果。作業名ごとに分ける |
| `tools/` | ローカル作業用スクリプト |

Feature Pipelineは作業開始時に `work/YYYYMMDD-<topic>/` を固定し、以下へ出力します。

```text
work/YYYYMMDD-<topic>/
├── plan.md
├── testcase.md
├── progress.md
└── evidence/
```

既存の計画・テスト仕様・進捗とケース別証跡もこの構成に移動しました。既存の記録は実施時点の証拠として保持し、移動を理由に承認状態や検証結果を書き換えません。
