# medi-chat 機能一覧と簡素化案

作成日: 2026-09-29

この一覧は、現在のコードをもとにした機能棚卸しです。実装を変更する前に、MVPに残す機能と後回しにする機能を分けるために使用します。

## 0. 採用する最小処理フロー

現在の実装は、次の処理だけを行います。

```text
チャット
  ├─ Jevで添付文書項目を判定
  ├─ 形態素解析で名詞を取得
  └─ 固定キーワードで添付文書項目を判定
       ↓ 判定完了順に SearchCriteria リストへ追加
       ↓ 3つの判定完了後、JSONL由来の検索インデックスを検索
       ↓ unit_idで重複排除・根拠を統合
       ↓ 統合済み根拠だけをLLMへ渡す
```

各判定器は添付文書を直接検索せず、`SearchCriteria`だけを返します。検索とLLM問い合わせはパイプラインの最後に1回ずつ行います。

## 1. 現在の機能一覧

### A. 医薬品データ作成

| ID | 機能 | 現在の内容 | 主な実装 |
| --- | --- | --- | --- |
| DATA-01 | PMDA XML読込 | 医薬品ごとの原本XMLを読み込む | `data_tools/data/`, `data_tools/structure_pmda_xml.py` |
| DATA-02 | XML構造化 | 見出し、本文、表、参照、図、改訂情報を保持した `document.json` を生成 | `data_tools/pmda_xml/` |
| DATA-03 | 検索単位生成 | 添付文書を検索可能な単位に分割して `search_units.jsonl` を生成 | `data_tools/pmda_xml/units.py` |
| DATA-04 | 検証 | セクション番号、参照、manifest、本文の網羅性を検証 | `validation.json` |
| DATA-05 | 検索インデックス | SQLite FTS5 と医薬品カタログを構築する | `backend/infrastructure/persistence/index_writer.py`, `backend/infrastructure/cli/build_search_index.py` |

### B. 医薬品選択

| ID | 機能 | 現在の内容 | 主な実装 |
| --- | --- | --- | --- |
| MED-01 | 医薬品カタログ取得 | 対応医薬品一覧を取得する | `GET /api/medicines`, `backend/presentation/medicine_routes.py` |
| MED-02 | YJコード特定 | YJコードで検索対象を固定する | `MedicineMatch`, `backend/domain/medicine/entities.py` |
| MED-03 | 複数選択 | 最大8件まで選択できる | `MedicineSelector`, `ChatRequest` |
| MED-04 | 入力サジェスト | 医薬品名、かな、カタカナ、ローマ字から候補を表示する | `frontend/app/lib/medicineAutocomplete.ts` |
| MED-05 | 入力からの追加 | 質問文中で選んだ医薬品を対象薬に追加する | `useMedicineCatalog` |

### C. 質問の解釈と検索

| ID | 機能 | 現在の内容 | 主な実装 |
| --- | --- | --- | --- |
| SEARCH-01 | ルールベース意図判定 | 禁忌、用法用量、妊婦、腎機能、副作用などをキーワードで判定する | `backend/application/retrieval/queries/policies/selection.py` |
| SEARCH-02 | セクション検索 | 意図をPMDAセクション番号に変換して検索する | `backend/infrastructure/persistence/evidence_reader.py` |
| SEARCH-03 | 全文キーワード検索 | Janomeで質問からキーワードを抽出し、対象薬の文書全体を検索する | `backend/application/retrieval/queries/services/keyword_detection.py`, `backend/infrastructure/morphology/janome_keyword_extractor.py` |
| SEARCH-04 | 複数薬剤の相互作用検索 | 指定薬の相互作用セクションを通常の検索条件で取得する。2剤間専用の直接記載判定は現行実装に含まれない | `backend/application/chat/queries/services/reply_preparation.py`, `backend/infrastructure/persistence/evidence_reader.py` |
| SEARCH-05 | Jev意図判定 | AIで複数の候補意図・確信度を判定し、該当セクションを追加取得する | `backend/application/retrieval/queries/services/intent_detection.py`, `backend/infrastructure/intent/jev_classifier.py` |
| SEARCH-06 | 検索結果マージ | ルール、Jev、キーワードの結果をIDで重複排除し、取得元を表示する | `backend/application/retrieval/queries/policies/selection.py` |

### D. 回答生成

| ID | 機能 | 現在の内容 | 主な実装 |
| --- | --- | --- | --- |
| ANSWER-01 | 根拠付き回答 | 検索結果を根拠として回答を生成する | `backend/application/chat/queries/policies/answer_prompt.py` |
| ANSWER-02 | LLM切替 | OpenAI / Gemini とモデルを選択できる | `backend/infrastructure/llm/`, `ChatHeader` |
| ANSWER-03 | ストリーミング | WebSocketで回答トークンを逐次表示する | `/api/ws`, `/ws/chat`, `useChatWebSocket` |
| ANSWER-04 | REST回答 | RESTで根拠検索し、必要なら非ストリーミングLLM回答を返す | `POST /api/chat` |
| ANSWER-05 | 通信状態表示 | 接続、検索中、検索完了、切断・中断を表示する | `chatWebSocket.ts`, `MessageItem.tsx` |

### E. 根拠表示UI

| ID | 機能 | 現在の内容 | 主な実装 |
| --- | --- | --- | --- |
| UI-01 | Markdown回答 | 見出し、表、リンク、太字などを表示する | `AssistantMarkdown`, `MarkdownContent` |
| UI-02 | 根拠セクション折りたたみ | 回答中の「根拠・参考文献」等を閉じて表示する | `frontend/app/lib/markdown.ts` |
| UI-03 | 根拠カード | 医薬品、セクション、改訂情報、抜粋、PMDAリンクを表示する | `SourceEvidencePanel` |
| UI-04 | セクション絞り込み | 根拠をセクション単位で絞り込む | `SourceEvidencePanel` |
| UI-05 | 取得元表示 | ロジック、Jev、キーワードの取得元を表示する | `ChatSource.retrieved_by` |
| UI-06 | Jevインスペクタ | 意図、確信度、確率分布、生JSONを表示・コピーする | `JevResponseInspector` |

### F. 運用・開発用機能

| ID | 機能 | 現在の内容 | 主な実装 |
| --- | --- | --- | --- |
| OPS-01 | ヘルスチェック | コーパスの文書数・検索単位数を確認する | `GET /health`, `GET /api` |
| OPS-02 | プロバイダ設定 | 環境変数で既定のLLMプロバイダ・モデルを指定する | `backend/main.py`, `.env.example` |
| OPS-03 | テスト | API、WebSocket、検索、Jev、XML構造化、UI補助処理を検証する | `backend/tests/`, `data_tools/tests/` |

## 2. 実装をシンプルにする場合の優先度

### MVPとして残す機能

最初は「指定した1つの医薬品について、添付文書の根拠を返す」範囲に絞ります。

1. PMDA XMLを原本として保持し、検索単位とSQLiteインデックスを生成する
2. 医薬品をYJコードで1件選択する
3. 質問をルールベースで主要セクションに振り分ける
4. 対象セクションを検索し、抜粋・改訂情報・PMDAリンクを返す
5. 1つのLLMプロバイダで根拠付き回答を生成する
6. 回答と根拠一覧を表示する
7. `/health` とデータ構築テストを残す

MVPの処理フローは次の1本にします。

```text
医薬品選択 → 質問入力 → ルール判定 → SQLite検索 → 根拠付きLLM回答 → 根拠表示
```

### 後回しにする機能

| 機能 | 後回しにする理由 |
| --- | --- |
| 2剤間の専用相互作用ロジック | 1剤検索と異なる分岐・表示・テストが増える |
| Janomeによる全文キーワード検索 | 検索方式が増え、結果マージが必要になる |
| Jevによる意図判定・複数セクション取得 | 外部AI依存、確信度処理、利用不能時の分岐が増える |
| OpenAI / Gemini / 複数モデルの切替 | プロバイダごとの設定・エラー・テストが増える |
| Jevレスポンスの詳細インスペクタ | 医療従事者向けのデバッグ機能であり、通常利用には不要 |
| 医薬品の複数選択 | 質問対象と相互作用対象の状態管理が複雑になる |
| ローマ字・かなの高機能サジェスト | 医薬品カタログ取得とデータソースが二重になる |

### MVPでは削除または1つに統合する候補

| 現在の重複・分岐 | 簡素化案 |
| --- | --- |
| REST `/api/chat` と WebSocket `/api/ws`・`/ws/chat` | まずREST 1本にする。ストリーミングが必須ならWebSocket 1本に統一する |
| ルール検索・Jev検索・キーワード検索 | MVPではルール検索だけにする |
| フロントエンド内蔵 `medicines.json` とバックエンド `/api/medicines` | 医薬品カタログの唯一の情報源を決める。MVPはバックエンドのYJコード一覧に統一する |
| LLMプロバイダ・モデルの画面選択 | MVPでは環境変数で固定し、画面からは外す |
| `retrieved_by` の複数組み合わせ | MVPでは `logic` のみとし、取得元の複雑な組み合わせ表示を外す |
| `max_sources` のAPI・サービス・検索層への伝播 | 結果件数の仕様を一度決め、全層で同じ契約にする。無制限方針なら公開引数ごと削除する |

## 3. 残すべき安全・根拠機能

以下は実装が複雑でも、医療用途の信頼性に関わるため削らない方針がよいです。

- PMDA XML原本を残すこと
- XMLの階層、表、参照、図、改訂情報を失わないこと
- 根拠抜粋とセクション番号を回答に紐づけること
- PMDA原本へのリンクを表示すること
- 「記載が見つからない」ことを「併用可能」と解釈しない注意文
- 対象医薬品をYJコードで固定すること
- データ生成時の検証とヘルスチェック

特に、XMLを単純なテキストに変換してしまうと、根拠表示と将来の検索改善の両方が難しくなります。データ作成部分は現状の source-preserving 方針を維持し、チャット経路とUI側を簡素化するのが安全です。

## 4. 推奨する段階分け

| 段階 | 実装範囲 | 判定基準 |
| --- | --- | --- |
| Phase 1 | 1剤、ルール検索、1プロバイダ、RESTまたはWebSocketのどちらか、根拠表示 | 主要セクションの質問に根拠付き回答が返る |
| Phase 2 | ストリーミング、複数剤、相互作用専用検索 | UXまたは相互作用の要求が明確になった場合のみ追加 |
| Phase 3 | Jev、キーワード検索、結果マージ、詳細インスペクタ | ルール検索で不足する質問例が収集できた後に追加 |

## 5. 現時点の結論

最も効果が大きい削減順は次のとおりです。

1. 検索経路をルール検索1本にする
2. 通信方式をRESTまたはWebSocketの1本にする
3. LLMプロバイダを1つに固定する
4. 医薬品を1件選択にする
5. Jev詳細表示と複雑な取得元バッジを外す

この順なら、PMDAデータの品質・根拠表示・医療用途の注意文を維持したまま、バックエンドの分岐、フロントエンドの状態管理、テストケースの数を同時に減らせます。

なお、これは機能整理のみで、コード変更やテスト実行は行っていません。
