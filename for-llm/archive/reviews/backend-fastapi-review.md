# バックエンドのFastAPIレビューと修正事項

レビュー日: 2026-10-02  
状態: 未対応（レビュー結果の記録のみ。製品コードは変更していない）

FastAPIスキルに基づき、現在のバックエンドのAPI、入力モデル、非同期処理、SDKクライアントの管理を確認した。以下は現在の実装に対する指摘であり、直前のファイル配置変更で発生した不具合だけに限定していない。

## 修正一覧

| ID | 優先度 | 修正事項 | 状態 |
| --- | --- | --- | --- |
| FASTAPI-01 | P1 | 同期のSQLite検索をイベントループから分離する | 未対応 |
| FASTAPI-02 | P2 | プロバイダーとモデルの既定値・解決処理を統一する | 未対応 |
| FASTAPI-03 | P2 | RESTにもプロバイダー・モデルの検証を適用する | 未対応 |
| FASTAPI-04 | P2 | SDKクライアントを確実に閉じる | 未対応 |
| FASTAPI-05 | P2 | 不正JSON受信時のWebSocket終了処理を修正する | 未対応 |
| FASTAPI-06 | P3 | Queryの宣言をAnnotatedに統一する | 未対応 |
| FASTAPI-07 | P3 | 共有サービスの取得をDependsで宣言する | 未対応 |

P1は同時リクエストへの影響がある問題、P2は特定の入力・設定・通信状態で発生する問題、P3は規約と保守性の改善として扱う。

## FASTAPI-01: 同期のSQLite検索をイベントループから分離する

対象: `backend/presentation/chat_service.py` の `ChatService.prepare_reply()`。呼び出し先は `backend/application/chat/answer_preparation.py` と `backend/infrastructure/persistence/evidence_reader.py`。

**確認した問題**

非同期メソッド内で同期の `search_evidence()` を直接実行している。検索中のSQLiteアクセスと結果の組み立てが、同じワーカーの別リクエストやWebSocket処理を待たせる。

検索処理に意図的に300msの遅延を入れた再現では、同時に送った軽量API `GET /api` の応答も308.2ms待たされた。この値は遅延を注入した検証結果であり、通常の検索時間の計測値ではない。

**修正方針**

同期検索を `asyncio.to_thread()` などでイベントループ外へ移す。SQLite接続を作成・使用・終了する処理は同じ実行スレッドに収め、共有する文書キャッシュについても同時アクセスを確認する。検索件数、重複排除、根拠の並び順は維持する。

**完了条件**

- 遅い検索を実行中でも、別の軽量APIとWebSocketの応答が検索終了を待たない。
- REST・WebSocketの回答、根拠、LLM入力が修正前と一致する。
- 複数の検索を同時実行してもSQLite接続や共有キャッシュのエラーが発生しない。

## FASTAPI-02: プロバイダーとモデルの既定値・解決処理を統一する

対象: `backend/presentation/chat_websocket_routes.py` の `validate_model_name()`、`backend/presentation/chat_service.py` の `stream_answer()`。

**確認した問題**

WebSocketの検証では、プロバイダー省略時に常にOpenAIを使用する。一方、実行時は `DEFAULT_PROVIDER` を参照するため、検証した組み合わせと実行する組み合わせが一致しない。モデル省略時もプロバイダーに関係なく `DEFAULT_MODEL` または `gpt-6-luna` が使用される。

| 設定・入力 | 確認した結果 | 修正後に期待する結果 |
| --- | --- | --- |
| `DEFAULT_PROVIDER=gemini`、provider省略、`model=gemini-2.5-flash` | OpenAI用の検証で拒否される | Geminiのモデルとして受理する |
| `DEFAULT_PROVIDER=gemini`、provider省略、`model=gpt-6-luna` | 検証を通り、Geminiへ渡される | 組み合わせの不一致として拒否する |
| OpenAIを既定とする設定で、`provider=gemini`、model省略 | Geminiへ `gpt-6-luna` が渡される | Geminiに対応する既定モデルを選ぶ |

**修正方針**

許可するプロバイダー・モデルと既定値の解決をLLM側の責務として一元化する。リクエストで指定されたプロバイダー、環境設定、プロバイダーごとの既定モデルの優先順位を明文化し、解決済みの同じ組み合わせを検証と実行に使用する。別プロバイダー向けの `DEFAULT_MODEL` を流用しない。

**完了条件**

- 上表の3ケースが期待結果どおりになる。
- provider/modelを両方省略した場合も、設定に整合する組み合わせを使用する。
- REST・WebSocketの両方が同じ解決処理を使用する。

## FASTAPI-03: RESTにもプロバイダー・モデルの検証を適用する

対象: `backend/presentation/chat_routes.py` の `ChatRequest`、`backend/infrastructure/llm/provider_factory.py` の `create_llm_provider()`。

**確認した問題**

RESTのprovider/modelは任意の文字列を受理する。ダミーSDKを使用したリクエストでは、`provider=typo-provider` と `model=arbitrary-model` が拒否されず、HTTP 200になった。同じ入力はWebSocketでは拒否される。また、実際のファクトリーは未知のプロバイダー名を `GeminiProvider` に振り分ける。

指定ミスにより意図しないサービスが選ばれたり、不正なモデル名のまま外部通信を開始したりする。

**修正方針**

FASTAPI-02の共通定義・解決処理を使い、REST・WebSocketの両方でプロバイダーとモデルの組み合わせを検証する。ファクトリーも未知の名前を黙ってGeminiに変換せず拒否する。既存の別名を維持する場合は、その対応も共通定義に明示する。

**完了条件**

- 不正な入力に対してRESTは422、WebSocketは入力エラーイベントを返す。
- 不正な入力では回答生成用SDKを呼び出さない。
- 有効な入力と省略時の動作が両APIで一致する。

## FASTAPI-04: SDKクライアントを確実に閉じる

対象: `backend/infrastructure/llm/gemini_provider.py` と `backend/infrastructure/llm/openai_provider.py` の `stream_response()`。

**確認した問題**

回答ごとにSDKクライアントを生成しているが、明示的な終了処理がない。ダミーSDKで正常終了まで実行した結果、OpenAIの `close()`、Geminiの `close()` と `aio.aclose()` の呼び出しはいずれも0回だった。

これは実際の接続リーク量を測定した結果ではない。現状はSDKのGC処理に依存し、例外・キャンセル・アプリ終了時を含む接続解放のタイミングをアプリ側で保証していない。

**修正方針**

SDKが提供する非同期コンテキストマネージャー、または `try/finally` でクライアントとストリームを解放する。Geminiは同期・非同期クライアントの終了APIが別なので、使用する側を正しく閉じる。クライアントをアプリ全体で共有する設計を採用する場合は、生成と終了をFastAPIのlifespanに対応させる。

**完了条件**

- 正常終了、SDK例外、キャンセル、ストリームの途中終了でリソースが解放される。
- Geminiの再試行中に、まだ使用するクライアントを閉じない。
- 現在のチャンク順序、再試行条件、キャンセル伝播を維持する。

## FASTAPI-05: 不正JSON受信時のWebSocket終了処理を修正する

対象: `backend/presentation/chat_websocket_routes.py` の `stream_chat_response()`。

**確認した問題**

`receive_json()` の解析エラーが受信ループ外の例外処理へ抜け、エラーイベントを送った後、closeフレームを送らずハンドラが終了する。

ローカルASGIで `{` に続けてpingを送る再現では、acceptとerrorのみが送信され、後続のpingは処理されなかった。Uvicornの実装上も、この経路は明示的なWebSocket終了通知を伴わない接続終了につながる。

**修正方針**

JSON解析エラーを受信ループ内で捕捉し、入力エラーを返して次のメッセージを待つ方針を推奨する。接続終了が必要な例外は、適切なcloseコードを送って終了する。`WebSocketDisconnect` は通常の切断として扱う。

**完了条件**

- 不正JSONの後でも、同じ接続でpingと有効なチャットリクエストを処理できる。
- 接続を終了する経路ではcloseフレームを送る。
- 不正な入力ではLLMを呼び出さず、切断済みソケットへ不要な送信をしない。

## 規約と保守性の改善

### FASTAPI-06: Queryの宣言をAnnotatedに統一する

対象: `backend/presentation/medicine_routes.py` の `list_medicines()`。

`query: str | None = Query(default=None, max_length=200)` を、`Annotated[str | None, Query(max_length=200)] = None` の形式へ変更する。引数の省略、通常文字列、200文字超過時の応答とOpenAPIの制約が変わらないことを確認する。

### FASTAPI-07: 共有サービスの取得をDependsで宣言する

対象: `backend/presentation/chat_routes.py`、`backend/presentation/chat_websocket_routes.py`、`backend/presentation/medicine_routes.py`、`backend/presentation/health_routes.py`。

各ルートで直接 `app.state` から取得しているサービス・ストアを、型付きの依存関数と `Annotated[..., Depends(...)]` で宣言する。リソースの生成は既存のlifespanが担当し、依存関数は取得を担当する。HTTPとWebSocketの双方で利用できる形にし、テスト時は `dependency_overrides` で差し替えられることを確認する。

## 検証範囲と実装順序

レビュー環境はFastAPI 0.141.1、Starlette 1.7.0、Pydantic 2.13.5。確認にはローカルASGI、一時SQLite、ダミーSDKを使用し、dotenvの読み込みと外部APIキーを無効化した。外部API通信、本番環境での動作確認、レビュー時の全体テスト再実行は行っていない。

直前のリファクタリング検証では、テスト137件成功・既存の9件失敗、型検査は既存の8件のエラーだった。この記録はレビュー前の結果であり、上記の修正後の検証結果ではない。

推奨順序はFASTAPI-01、FASTAPI-02と03、FASTAPI-04、FASTAPI-05、FASTAPI-06と07。既存のファイル分配方針と添付文書カタログの一元管理は維持する。実装時には各項目の完了条件を確認し、既存の失敗と新規の失敗を区別して記録する。

## 参照

- レビュー時に参照したFastAPIスキル: `.agents/skills/fastapi/SKILL.md`（現行ツリーには存在しない）
- [FastAPI: 非同期処理と通常の関数呼び出し](https://fastapi.tiangolo.com/async/#other-utility-functions)
- [FastAPI: lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [Google Gen AI SDK: クライアントの終了処理](https://googleapis.github.io/python-genai/#close-a-client)
