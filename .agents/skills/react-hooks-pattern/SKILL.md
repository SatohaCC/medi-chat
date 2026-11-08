---
name: react-hooks-pattern
description: Reactの状態・Effect・custom Hookを設計・実装・リファクタリング・レビューするときに使う。Hookの呼び出し規則、状態の所有者、依存配列、cleanup、SSRを確認し、必要な場合だけReactのActionsやCompilerを扱う。通常の純粋な関数までHook化しない。
---

# React Hooks Pattern

## 目的と出典

[Patterns.dev — Hooks Pattern](https://www.patterns.dev/react/hooks-pattern/)を起点に、状態を伴う振る舞いをcustom Hookとして扱う。抽出の目的は責務の明確化とロジックの再利用であり、ラッパーの置き換えや行数削減そのものではない。

以下は公式React資料と照合した適用指針を含む。記事のサンプルを完成済みの実装としてコピーしない。

## 着手時の判断

- プロジェクトのAGENTS.md、frontend作業案内と指定資料を確認する。React・react-dom・フレームワークの導入バージョン、既存の取得・購読方式、lintとCompilerの設定を実物で確認する。記事で紹介された新APIのためだけに更新しない。
- ロジックを「描画中に計算できる値」「操作で始まる処理」「外部との同期」「保持する必要のある状態」に分ける。前二者をEffectへ移さない。
- custom Hookには`useChatConnection`のように目的を表す名前を付け、入力・返却値・操作・外部依存を絞る。Hookを使わない変換処理は通常の関数にする。汎用のuseMount等で依存関係を隠さない。
- 同じHookの複数呼び出しは、ローカル状態そのものを共有しない。共有が必要なら上位の所有者、Context、既存ストアやキャッシュを検討する。

根拠: [custom Hookによるロジック再利用](https://react.dev/learn/reusing-logic-with-custom-hooks)。

## 呼び出しと状態

- 通常のHookは関数コンポーネントまたはcustom Hookのトップレベルで、条件付きearly returnより前に呼ぶ。ループ、条件、イベントハンドラ、Effectの内部から呼ばない。`use` APIの例外は後述の参照資料で確認する。
- 新しい値が前の値に依存する更新、特に同じ操作内で積み重なる更新には関数形式のsetterを検討する。直接値を渡すsetterを一律にバグ扱いしない。
- 高コストな初期値には純粋な遅延initializerを検討する。「必ず一度しか呼ばれない」と仮定しない。開発時のStrict Modeではinitializerやupdaterが再実行され得る。
- 複数の値の遷移を一か所で扱う利益があればuseReducerを検討する。stateとpropsを直接変更せず、描画に使う値をrefだけに保持しない。

根拠: [Rules of Hooks](https://react.dev/reference/rules/rules-of-hooks)、[useState](https://react.dev/reference/react/useState)。

## Effectと外部同期

- Effectを設ける前に、同期対象の外部システムを説明できるか確認する。派生値は描画時の計算、送信等のユーザー操作はイベントハンドラへ置く。
- Effectが参照するreactiveな値を依存配列へ反映する。再実行を止めるために依存を抜いたりlintを抑制したりしない。不要なオブジェクト・関数依存は構造の見直しで減らす。
- 購読・タイマー・接続のsetupに対応する解除を返す。cleanupはunmount専用ではなく、依存変更時にも古い値で走る。Strict Modeのsetup → cleanup → setupに耐える構造にする。
- 非同期取得を変更する場合、古い応答の上書き、解除後の更新、失敗・再試行を確認する。既存の取得基盤を優先し、Hook抽出だけで独自fetch基盤を導入しない。
- stale closureは読み取る値と更新の意味を確認して直す。空の依存配列や最新値のrefを万能の修正にしない。購読を更新すべき値まで隠さない。

根拠: [useEffect](https://react.dev/reference/react/useEffect)。

## 条件に応じて読む資料

ブラウザーAPI・storage・SSR、外部ストア、ReactのActions・`use`、Compiler、クラスからの移行を扱う場合は、[references/advanced-and-caveats.md](references/advanced-and-caveats.md)の該当節を読む。APIの網羅的な導入を目的にしない。

表示の独立性やContainerとの境界が論点なら、その必要性を別途判断する。custom Hookへ抽出しても呼び出し側の外部依存がなくなるわけではない。

## 検証と報告

プロジェクトの検証手順・品質ハーネスを使う。変更した振る舞いに応じて、操作と描画、入力変更、失敗、解除、競合を確認する。独立したHookの契約を確かめる利益があれば、既存のrenderHook等を使う。Hookを通常の関数として直接呼んで検証しない。

Hookの数・名前・ファイル分割そのものをテストしない。レビューでは具体的な動作上の問題と根拠を示し、不要な抽出を要求しない。結果は変更した責務、残る依存、実際に実施した検証と未検証の層を説明する。
