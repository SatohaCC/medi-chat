# Domainハーネス

`scripts/domain_architecture.py`がDomainの構造規則を静的に検査する。対象ソースはASTとして読み、import・実行しない。標準のbackend lintとCIで全規則を強制する。違反baselineや個別ファイルの抑制設定は設けない。

## 実行

```bash
pnpm --filter backend lint:domain
pnpm --filter backend lint:domain:harness

# リポジトリルートから直接実行
uv run --project backend --locked python scripts/domain_architecture.py
uv run --project backend --locked python scripts/domain_architecture.py --json
uv run --project backend --locked python scripts/domain_architecture.py --context attachment
```

rootはスクリプト配置から解決する。`--root <repo>`で独立した合成コードにも適用できる。終了コードは0=違反なし、1=違反あり、2=対象ディレクトリ・contextなどの入力エラー。診断はリポジトリ相対パス・1始まりの行番号・規則IDを返す。`--context`は診断の絞り込みであり、CIでは指定しない。

## 強制する構造

| ID | 規則 |
| --- | --- |
| DOM000 | Python構文エラー |
| DOM001 | Context直下の責務別モジュール配置。foundation/primitivesの共通基底だけ既定の階層を使う |
| DOM002 | `__init__.py`は空またはdocstringのみ。再公開・初期化処理を置かない |
| DOM003 | 外層・他Contextの内部モデルへの依存禁止。foundation/sharedから業務Contextへの逆依存も禁止 |
| DOM004 | 同Context内とsharedへの役割別の依存方向 |
| DOM005 | 自動検出した全業務Contextに公開IDを1クラスだけ定義。EntityStringIdまたはEntityUUIDを継承し、プロジェクト内の依存先はfoundationのID基底に限定 |
| DOM006 | 値の計算・型定義等に使う標準ライブラリをVALUE_MODULESに列挙し、それ以外の技術依存を禁止。wildcard import、動的import／実行、open/input/print等も禁止。URLの純粋な解析であるurllib.parseは利用可能 |
| DOM007 | Domainのdataclassをfrozenにし、業務VO／Entityはfrozen dataclassとして保持。デコレーターの別名・修飾名・継承も確認 |
| DOM008 | フィールドの可変collectionを禁止。ネスト・文字列注釈・型aliasを解決し、業務モデルの可変な初期値も禁止 |
| DOM009 | 業務VO／Entityのフィールドにstr/int/float/bytes/Any/objectを直接保持しない。Primitive／VOへ分ける。boolの状態フラグは許可 |
| DOM010 | `create()`の生成ラッパーを禁止し、型付き値を直接コンストラクタへ渡す |
| DOM011 | 業務VO／Entityのpost-initでフィールドを置換しない。selfフィールドの単純な型検査や_require型の補助メソッドを置かない |
| DOM012 | 業務PrimitiveはDomainPrimitiveを、Repository契約はProtocolを継承。クラスは役割を特定できるモジュール直下へ定義し、入れ子にしない |
| DOM013 | Domainモジュール間の循環依存を禁止 |

業務Contextはdomain直下のパッケージから自動検出する。foundation/sharedは業務Contextではなく、公開IDの数を課さない。既存Contextの名前を列挙して新規Contextを検査から漏らさない。必要のない責務ファイルを空で作成する必要はない。

既存のImport Linterは間接依存も含む4層の検査を担う。既存のDomain配置・公開ID数・dataclass不変性・create禁止テストは、このハーネスの該当規則を呼び出して正本を一本化する。型の適合はPyright/mypyでも確認する。

## 検証の範囲

`test_domain_harness.py`に正常例と禁止例を置く。新規Context、逆方向import、関数内import、型注釈、別名dataclass、型alias、通信・プロセス実行、循環、CLIの終了コードを検証する。

これは構造の静的検査であり、任意のPythonプログラムの意味を完全に証明するものではない。reflection・monkeypatch・独自デコレーター等を使った実行時の迂回の完全検出は保証しない。Aggregate境界の妥当性、業務語彙、状態遷移、Primitiveのvalidate()が必要な値を拒否すること、深い不変性の振る舞いはDomainの個別テスト・レビューで確認する。

foundationのDomainPrimitiveとImmutableMappingは、単一値の正規化や入出力からの独立を提供する共通基底である。業務VO／Entityのpost-init禁止をこれらの基底の実装へ適用しない。JSON値の型定義はfoundation/json_types.pyに置き、業務フィールドへ生のJSONを直接保持させない。
