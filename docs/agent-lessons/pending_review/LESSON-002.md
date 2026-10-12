# LESSON-002: 世代スナップショット管理の内部ループI/Oとdeepcopyによる検索遅延

- 状態: pending_review
- 作成日: 2026-10-12
- 最終確認日: 2026-10-12
- 承認者・承認日・承認の参照: 未承認
- 更新案の場合の対象: なし
- 統合先・廃止理由: なし

## 本文を読むトリガー条件

`generation_runtime.py`、スナップショットリーダー、または検索・取得パイプラインでキャッシュやループ内でのモデルマッピング・インデックス構築を変更する作業。

## 適用する条件／適用しない条件

世代管理スナップショット（`GenerationRuntime` / `_SnapshotReader`）や同等のインメモリ検索プロジェクションを扱う場合に適用する。単純なSQLite直接クエリや静的辞書引きには適用しない。

## 観察した失敗と証拠

先行配信（ロジック検索）のレスポンスが、キャッシュ有効時でも約0.7〜1.0秒（初回は約1.8秒）かかっていた。本来数十ミリ秒で返すべきローカル検索が実環境で遅延していた。

<details>
<summary>関連PR・コミットの証拠</summary>

- 対象コミット: 9bfde32, eb0bb42, 1dd1173
- 該当ファイル: `backend/infrastructure/persistence/generation_runtime.py`

</details>

## 原因

- 証拠で確認できた原因:
  1. `_acquire()` 内でキャッシュヒット時にも `read_registered_snapshot()` が毎回呼ばれ、全成果物ファイルのディスク読込とSHA-256ハッシュ計算（約340ms）を実行していた。
  2. `_SnapshotReader._search()` 内で、検索ユニットごとに `entry.metadata.to_dict()`（`ImmutableMapping` の `deepcopy`）を全件呼んでおり、1リクエストあたり約270〜295ms消費していた。
  3. `criteria.keywords` が空のセクション検索時にも、都度インメモリSQLite (`:memory:`) を作成してFTS5テーブルの構築とINSERTを行っていた。
  4. サーバー起動時に世代キャッシュが未ウォームアップだったため、初回リクエストでXML全パース（約1.4秒）が発生していた。
- 未確認の仮説・残る不確実性:
  登録文書件数が大幅に増加（数百〜数千件）した場合のインメモリプロジェクションのメモリフットプリントは未計測。

## 次回の具体的な確認手順

スナップショットやプロジェクションを生成・検索するコードでは、キャッシュヒット時のクリティカルパスにディスクI/O（ファイル読込・ハッシュ計算）が残っていないかプロファイリングで確認する。また、ユニットごとの反復ループ内で `to_dict()` や `deepcopy` が走っていないかを点検し、起動時ウォームアップの要否を検討する。

## 対策の検証

- 検証方法と成功・失敗の判定条件:
  `GenerationRuntime` 経由のロジック先行配信時間を測定し、50ms未満で配信されること。
- 実施結果・検証した層・対象差分:
  `acquire()` キャッシュヒット時の不要な `read_registered_snapshot()` の抑止、`raw_metadata` の直接参照、同一スナップショット内での `_rows_cache` 導入、キーワード空時のFTS5構築スキップ、起動時ライフスパンでのウォームアップを追加。
  Call 1: 1.599s → 0.047s、Call 2: 0.688s → 0.025s に短縮（約28〜40倍高速化）。
  `pytest backend/tests/test_generation_runtime.py backend/tests/test_progressive_retrieval.py backend/tests/test_chat_service.py backend/tests/test_chat_websocket_routes.py`（40件パス）、`pnpm --filter backend lint`（全チェックパス）、`pnpm typecheck:python`（Pyright 0 errors）。
- 未実施・環境不足・skip/xfail:
  なし。
- 回帰テスト・lint・CI／既存規約へのリンク:
  [backend/tests/test_generation_runtime.py](../../../backend/tests/test_generation_runtime.py)

## 次の関連作業での評価

未評価。承認待ちであり、INDEXには登録しない。
