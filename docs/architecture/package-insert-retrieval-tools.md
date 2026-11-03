# 電子添文の3つの根拠取得ツール

本番のComposition Rootは`PackageInsertTools`を`MedicalToolProvider`としてLangGraphへ注入する。取得方式は次の3つの独立した`MedicalTool`で表す。

| ツール名 | Applicationのクラス | 検索条件の生成 | 取得由来 |
| --- | --- | --- | --- |
| `package_insert_fixed_keyword` | `PackageInsertFixedKeywordTool` | 固定医療キーワードと項目の対応 | `logic` |
| `package_insert_morphology` | `PackageInsertMorphologyTool` | 医薬品名を除外した質問の形態素解析・全文検索 | `keyword` |
| `package_insert_jev` | `PackageInsertJevTool` | Jevの質問意図判定と関連項目の選択 | `jev` |

各ツールは担当する検出器だけを呼ぶ。固定キーワードツールはJevも形態素解析も呼ばず、形態素解析ツールはJevを呼ばない。従来の一括`PackageInsertTool`は削除した。3つとも必須実行であり、LLMによる省略や呼び分けへは変更していない。

## 共通処理と寿命

`PackageInsertTools.acquire()`が要求ごとに1つの`EvidenceRetrievalSession`を作り、同一の`RetrievalSnapshot`と医薬品照合結果を3ツールへ渡す。医薬品カタログの取得は1回で、要求をまたぐキャッシュや可変状態は共有しない。

1・2・8等の常時取得する安全情報は`EvidenceRetrievalPolicy`を共有し、`always`由来として保持する。3ツールが返す根拠にはこの共通情報も含めるが、検索条件ごとのキャッシュによって再検索しない。安全情報を別の4番目の検出器にはしない。

検出器は並列に動かし、同一MVCCトランザクションへの検索と通知はSession内のlockで直列化する。ローカル根拠はJevの終了を待たずに累積リストとして通知する。最終結果は検索単位IDで重複を除去し、原文・出典・改訂情報・取得由来を保持して項目順に並べる。Jevの分類原本と複合意図も引き継ぐ。

必須ツールの終了・失敗・取消では非同期の子タスクをcancel/joinしてからスナップショットを解放する。LLM生成中は取得用のDBトランザクションを保持しない。対象医薬品を特定できない場合は検索・検出器・回答モデルを呼ばず、確認応答を返す。HTTP/WSの項目名・イベント・取得由来の値は変更しない。

## 検証する契約

- 各ツールが担当外の検出器を呼ばないこと。
- 共通安全情報と各検索条件を再検索しないこと、医薬品照合とスナップショット取得が1回であること。
- Jev待機中の累積根拠通知、従来の取得結果との原文・出典・由来・分類情報の一致。
- 成功・検出器失敗・通知失敗・取消時に子タスクとスナップショットを終了し、生成前に解放すること。
- 未登録医薬品では検出器/LLMを呼ばず、解放済みSessionのツールを再使用できないこと。

テストは`backend/tests/application/chat/test_package_insert_tools.py`と`backend/tests/integration/test_package_insert_tool_agent.py`に置く。外部SDKはダブルであり、実Jev/LLM通信・実DBでの成功を意味しない。

2026-11-02の最終差分で`pnpm quality:backend`は終了コード0。通常テスト971件成功・実DB/非公開原本等345件除外、構造ハーネス66/73/42件、Import Linter 24契約、Ruff・Pyright・mypyを確認した。今回追加した18ケースには、要求間のキャッシュ分離と、Jev利用不可・一般質問・複合意図・一部未登録製品での結果一致も含む。実Jev/LLM・実PostgreSQL・ブラウザでの新たな実接続試験は未実施。
