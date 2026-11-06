# エージェント共通設定

`agents/`の役割定義と`skills/`の共通スキルはGit管理し、別端末でも同じ内容を使用します。作業記録の`work/`や、ここに明示していない端末固有ファイルはGit管理しません。

- `feature-pipeline`: 明示的な開始・再開依頼時だけ使用します。
- `ddd-onion-bestpractices`: DDD・層の依存と責務の確認に使用します。
- `react-aria`: React Ariaの実装・検証用資料です。導入元はReact Aria公式Agent Skills（https://react-aria.adobe.com）です。
- `security-audit`: セキュリティレビュー用です。導入元と導入時のhashはルートの`skills-lock.json`を参照してください。

共通の検証入口は`pnpm agent:check`です。`hooks.json`はAntigravity用、`../.codex/hooks.json`はCodex用のadapterです。設定ファイルが存在するだけでは自動実行を保証しません。各端末・実行環境でHookの読み込みと実行を確認してください。

秘密情報、個人パス、ログ、進行記録をスキル・役割定義へ追加しないでください。新しいスキルは、内容と導入元を確認してから共有します。
