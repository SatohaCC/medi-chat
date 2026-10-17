---
name: domain-layer
description: ドメイン駆動設計のドメイン層を設計・実装・レビューするときの一般的なルール。
---

# Domain Layer

ビジネスルールを表現し、ドメインモデルの不変条件を保つ最内層。

## 1. 責務・制約

- **責務**: 状態遷移、値の検証、計算、集約の整合性をドメインモデル内で完結させる。
- **依存方向**: 外側のレイヤーから内側のドメインへ依存する。ドメインは Application、Infrastructure、Presentation に依存しない。
- **技術依存**: Web フレームワーク、ORM、DB セッション、HTTP の Request/Response、外部 API の型を持ち込まない。
- **常に正しい状態**: Domain Primitive、Value Object、Entity、Aggregate は生成時または復元時に不変条件を検証する。
- **境界の分離**: DTO、認証・認可、トランザクションの調整、外部入出力の変換はドメインの責務にしない。

## 2. 構成要素

1. **Domain Primitive (DP)**: 基本型をラップした最小の値オブジェクト。生成時に正規化と自己検証を行い、不正な値を保持しない。
2. **Value Object (VO)**: 複数の値を組み合わせた不変オブジェクト。IDによる同一性を持たず、値で比較する。
3. **Entity**: IDによって同一性を判定し、状態変化を伴うライフサイクルを持つオブジェクト。
4. **Aggregate**: ひとまとまりの不変条件を守る整合性境界。外部からの操作は **Aggregate Root** を経由する。
5. **Domain Service**: 1つの Entity/VO に自然に属さない、状態を持たない業務判断。Entity や VO に閉じた処理を安易に Service へ移さない。
6. **Repository Interface**: ドメインが必要とする永続化操作の抽象。Python では `Protocol`、他言語では interface 等で定義し、具象実装は外側に置く。
7. **Domain Exception**: 業務ルール違反やドメイン上の失敗を表す例外。HTTP ステータスやDB固有の例外型は持たせない。

## 3. 推奨構造

小規模なドメインでは、責務ごとのディレクトリを増やさず、ドメイン直下のモジュールにまとめる。各ファイルをその責務の正本とし、互換用の再公開Facadeや不要な `__init__.py` 集約を作らない。

```text
domain/
├── identifiers.py      # 他コンテキストへ公開する唯一のEntity ID（1コンテキスト＝1公開ID）
├── exceptions.py       # Domain Exception
├── primitives.py       # コンテキスト内部のDomain Primitive、Enum
├── value_objects.py    # Value Object
├── entities.py         # Entity、Aggregate Root
├── repositories.py     # Repository Interface
└── services.py         # Domain Service
```

複数の境界づけられたコンテキストがある場合だけ、コンテキストを先に分け、その内側を同じフラット構成にする。コンテキスト内部の依存方向は以下の単方向階層（上流 $\leftarrow$ 下流）を Import Linter と AST テストで機械的に強制する：
`identifiers` / `exceptions` $\leftarrow$ `primitives` $\leftarrow$ `value_objects` $\leftarrow$ `entities` $\leftarrow$ `repositories` $\leftarrow$ `services`

```text
domain/
├── foundation/         # 業務非依存のPrimitive・VO・例外基底
├── shared/             # 合意した共有語彙・汎用正規化処理
└── medicine/
    ├── identifiers.py
    ├── exceptions.py
    ├── primitives.py
    ├── value_objects.py
    ├── entities.py
    ├── repositories.py
    └── services.py
```

1ファイルが実際に大きくなった場合は、まず境界づけられたコンテキストや集約単位を見直し、それでも必要なときだけ責務内で分割する。配置場所ではなく責務と依存方向を優先する。共有語彙は Shared Kernel 等の明示的な境界に置き、特定コンテキストのモデルを無関係なコンテキストから直接再利用しない。

## 4. 設計ルール

- 複数コンテキストから参照されるという理由だけでIDをsharedへ移さない。識別対象の所有元が明確なら、そのコンテキストの `identifiers.py` が正本となり、他コンテキストは公開IDとして参照する。Shared Kernelへ置くのは、意味・制約・変更責任を共同で管理する合意がある語彙に限る。
- 照合・検索・集計の実行中だけ作るグループは、独立した業務上の同一性やライフサイクルを持たない限りEntity・Aggregateとして公開しない。グループ化・重複排除・照合中の整合性はサービスが所有し、必要な作業用状態は非公開の内部モデルに置く。外部には不変の結果VOを返し、利用側に内部モデルの操作や結果変換を要求しない。業務上の状態遷移・同一性・整合性境界を持つグループは、この一時状態と区別してモデル化する。
- IDの型名は `〜Id`、属性名は `〜_id` / `〜_ids` に統一し、同じ識別子に `Key` と `Id` の別名を用意しない。公開契約の変更では利用側も更新する。既存DB・ファイルの項目名を維持する必要がある場合はInfrastructureで明示的に変換し、ドメインへ旧名の互換プロパティを追加しない。
- 原本の構造・改訂・整合性は原本を所有するコンテキスト、検索条件・検索単位・取得結果の統合は利用側のコンテキストが所有する。利用側は原本IDと必要な情報のスナップショットを保持する。派生モデルのIDもそのモデルの所有元に置く。別モデルを残すときは用途・不変条件・ライフサイクルの違いを明示し、同じ契約なら一本化する。索引の保存やSQL・FTSはInfrastructure、原本から派生モデルへの変換の調整はApplicationや取り込み処理に置く。
- 独立した複数の値を重複なく保持する情報は不変集合で表し、全組み合わせをEnumや対応表に列挙しない。組み合わせ自体に固有の業務ルールがある場合は別途モデル化する。公開境界では順序を定義して配列へ変換し、要素がない状態は空集合・空配列で表す。未取得・不明を区別する必要がある場合はその意味を別途定義する。
- 他の値から一意に導出できる情報は、独立した入力項目として二重保持せずプロパティ等で導出する。階層の親を番号から導出できても、親の存在や重複などの集合全体の整合性はAggregateで検証する。
- 各コンテキストの `identifiers.py` は標準ライブラリと `foundation/primitives/identifiers.py` のID基底だけをimportする。Entity・AggregateのIDは `EntityUUID` または `EntityStringId` を継承し、通常のPrimitive基底・shared・他コンテキストへ依存させない。foundationのID基底モジュール自身には、この利用側の制限を適用しない。
- 各コンテキストが所有し、他コンテキストから参照されるEntityのID Primitiveは `identifiers.py` に定義する。他コンテキストからの直接参照はこの公開IDモジュールに限り、Entity・Aggregate・通常のPrimitive・VO・Exception・内部サービスは参照しない。必要な情報はApplicationが利用側の型へ変換する。`identifiers.py` はID定義だけを持ち、内部モデルのimport・再公開や業務サービスを置かない。共有基盤から業務コンテキストのIDへの逆依存も禁止する。公開IDの移動時は利用側を更新し、旧モジュールへ再公開しない。
- コンテキスト間で同じ意味・契約を持つ識別子は、共有語彙として合意した場合に限りShared Kernelへ置く。共有領域は特定コンテキストに依存しない。検索経路・結果統合などの振る舞いはその責務を所有するコンテキストに置き、import解消だけを目的に共有領域へ移さない。移動時は利用側を正本へ更新し、旧パスの再公開を残さない。
- Entity / Value Object はPrimitiveや不変コレクションを明示的に渡して直接生成する。文字列・リスト・辞書からの変換だけを担う `create()` や、その代わりとなる生成ラッパーを追加しない。
- 外部データを取り込む利用側でPrimitive・VO・tuple・frozensetへ変換する。単一値の正規化・形式検証はPrimitive、複数の値の関係や集約内の整合性はモデルの生成時に保証する。ファクトリ削除を理由に不変条件を削除したり、変換処理をそのままモデルの `__post_init__()` に移したりしない。
- `from_value()` / `parse()` 等のPrimitiveの復元操作と、外部SDK・ORMの `create()` はモデルの生成ラッパーと区別する。
- モデルの `__post_init__()` は複数値の関係や集約の不変条件に使い、基本型とPrimitiveの両方を受け入れる暗黙変換や、単一フィールドの型チェックを重ねない。既存の暗黙変換を削除するときは利用側とテストも明示的な生成へ移行する。検証のために正規化関数を呼び、戻り値を捨てる実装も避ける。
- 原文・スナップショットを表す値には汎用文字列基底のtrimやNFKCを機械的に適用しない。空本文が有効な原文契約の場合は、非空文字列を前提とする基底ではなく、その契約を表すPrimitiveで保持する。外部の整形・公開境界には `.value` を渡す。

- Entity や Aggregate はデータの入れ物にせず、状態遷移と不変条件を操作として公開する。
- Aggregate Root だけが集約内部の Entity を生成・変更できる。別集約の Entity を直接保持せず、必要なら識別子や参照用の値だけを保持する。
- DP と VO は可能な限り不変にする。変更が新しい値を意味する場合は、新しいインスタンスを返す。
- **非空文字列と原文を区別する**: 名前・識別子などの非空文字列は `BaseString` 等で空文字を拒否する。値の不在は `Primitive | None`（Optional）で表現する。原文として有効な空本文は不在と区別し、原文を保持するPrimitiveの契約に従う。
- Domain Service は副作用や業務状態を持たない。永続化が必要な場合も、ドメイン側の Repository Interface に依存する。
- Repository Interface はドメインのユースケースに必要な最小操作を表す。ORMモデル、セッション、SQL、ページング用のHTTPカーソルなど、技術詳細をシグネチャに漏らさない。
- Domain Exception はドメイン語彙で表現し、HTTPレスポンスやログ形式への変換は外側のレイヤーで行う。
- 日時、乱数、外部サービスなど実行環境に依存する判断は、必要に応じて小さな抽象を注入する。現在時刻や外部クライアントをドメインから直接取得しない。
- Domain Event を使う場合は、発生した業務上の事実と配送・購読の仕組みを分離する。イベント配送の技術実装を Entity に持たせない。

## 5. どこに置くかの判断

| 問題 | 置き場所 |
| --- | --- |
| 1つの値の形式・範囲・正規化 | Domain Primitive |
| 複数の値の組み合わせと値としての等価性 | Value Object |
| IDを持つ対象のライフサイクル | Entity |
| 複数のオブジェクトを一貫して変更する境界 | Aggregate / Aggregate Root |
| 1つの Entity/VO に属さない純粋な業務判断 | Domain Service |
| 保存・検索の抽象 | Repository Interface |
| 業務ルール違反 | Domain Exception |
| 入力変換、認可、ユースケースの順序付け、コミット | Application / 外側のレイヤー |

## 6. テスト・レビュー指針

- 実装詳細ではなく、不変条件、状態遷移、戻り値、例外、集約境界など外部から観測できる振る舞いを検証する。
- Domain model はモックせず、実際の DP、VO、Entity、Aggregate を使う。外部ポートの差し替えには Fake やインメモリ実装を使う。
- 正常系だけでなく、空値、境界値、正規化、無効な状態遷移、重複、再実行、関連IDの不一致を確認する。
- Repository Interface のテストでは、実装が保存・取得・検索の契約を満たすことを確認する。DB製品固有の挙動は Infrastructure のテストに分ける。
- ドメイン層の依存を調べるときは、Web・DB・Applicationへの逆向き依存、集約をまたぐ Entity の直接保持、Domain Service への過剰なロジック移動がないかを確認する。
- コンテキスト間の依存ルールは静的検査で継続的に確認する。新規コンテキストにも適用できる規則を優先し、公開IDや共通基盤への許可は範囲を限定する。直接・間接の禁止依存と、公開ID経由の内部モデル参照を検査する。許可例・違反例で検査規則を検証し、動的importなど検査できない範囲を明示する。
