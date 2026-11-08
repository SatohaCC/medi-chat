# 条件別の指針と記事サンプルの注意点

## ブラウザーAPI、外部ストア、SSR

ブラウザー環境を判定するだけでhydrationが正しくなるとは判断しない。サーバー出力とクライアント初回描画が一致するか、ブラウザーの値へいつ切り替えるかを設計する。

外部値の購読には既存の実装を優先し、必要ならuseSyncExternalStoreを検討する。subscribeは解除を返す。getSnapshotは変更がない間は同じsnapshotを返し、SSRではgetServerSnapshotをサーバーとhydrationで整合させる。

記事のstorage・media queryサンプルを使う場合の追加確認:

- localStorageの読取・JSON解析・書込が失敗した場合の方針を決める。TypeScriptの型アサーションを保存値の検証に使わない。
- storageのkeyやmedia queryの入力変更後に、購読先と返却値が一致するか確認する。key変更時に旧値を新keyへ書き込む挙動を見落とさない。
- 複数タブ・同一タブ内の同期が要件なら、その通知経路を確認する。ローカルstateだけで共有を保証しない。

根拠: [useSyncExternalStore](https://react.dev/reference/react/useSyncExternalStore)。storageの例外・入力変更の扱いはサンプルを採用する際の追加の設計判断。

## useとActionsを使う場合

導入バージョンに対応する公式APIを確認する。以下は自動的に既存実装を置き換える理由にはしない。

- `use`: 通常のHookと異なり条件・ループ内で呼べるが、コンポーネントまたはHook内で使う。try/catchで包まず、Promise拒否は適切なError Boundary等へ委ねる。Client Componentのrenderごとに新しい未キャッシュPromiseを作らない。既存フレームワークのPromise供給・キャッシュを優先し、Suspenseの待機表示も設計する。
- `useActionState`: actionの第一引数は前回stateであり、フォームデータ等はその次に来る。返されたactionをform actionへ渡すか、手動実行時は必要なAction/Transitionの文脈を確保する。
- `useFormStatus`: react-domから使い、対象formの子孫で呼ぶ。Hookを呼ぶコンポーネント自身が返すformの状態を読めるとは仮定しない。
- `useOptimistic`: Action/Transition内で楽観更新し、確定結果を実際の基底データへ反映する経路を用意する。楽観表示だけで永続化や再取得が完了したとは扱わない。失敗時の復元・通知も確認する。

根拠: [use](https://react.dev/reference/react/use)、[useActionState](https://react.dev/reference/react/useActionState)、[useFormStatus](https://react.dev/reference/react-dom/hooks/useFormStatus)、[useOptimistic](https://react.dev/reference/react/useOptimistic)。

## Compilerとmemoization

ReactのバージョンだけでCompilerが有効とは判断しない。ビルド設定と適用対象を確認する。有効な新規コードでは自動最適化を活かし、必要性のある箇所で手動memoizationを使う。既存のuseMemo/useCallbackを一括削除せず、変更時は依存と動作を検証する。memoizationをデータの永続保持や副作用の実行保証として使わない。

根拠: [React Compiler Introduction](https://react.dev/learn/react-compiler/introduction)。

## クラスから移行する場合

ライフサイクル名をEffectへ機械的に対応させず、外部同期の単位で組み直す。記事のscroll保存例で`[pageId, y]`を依存にするcleanupは、unmount時に加え依存変更時にも保存する。元の保存タイミングと同じとは扱わず、保存の契機と値の仕様を明確にしてから移行する。

また、記事の「直接値を渡すsetterは安全でない」「遅延initializerは初回にしか呼ばれない」という説明を絶対条件にしない。直接値による更新も正当な用途があり、開発時には純粋性の確認でinitializerが複数回呼ばれ得る。

根拠: [useEffectのcleanup](https://react.dev/reference/react/useEffect)、[useStateの更新と初期化](https://react.dev/reference/react/useState)。
