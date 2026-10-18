# 医薬品メンション入力の実装計画（@react-spectrum/ai 採用案）

作成日・更新日: 2026-10-18。状態: 計画案。実装・動作検証は未実施。

## 1. 目的と範囲

`@react-spectrum/ai` の `PromptField` / `PromptTokenField` を導入し、文章中の任意の位置へ医薬品トークンを挿入する。「@薬A から @薬B へ変更」の順序と後続文を保持し、同一の `PromptFieldValue` から本文と今回の言及薬を生成する。

対象はfrontendの依存、Next.js設定と起動経路、Provider、入力ドック、薬の選択、送信処理、関連試験。backendのJSON契約、検索方式、DB、検索索引、外部LLM通信プロトコルは変更しない。
既存の `searchMedicines` と候補取得・マージ規則を再利用する。候補検索は医薬品名のブラウザ内検索であり、添付文書本文の検索やLLM処理ではない。

## 2. 対象薬と省略質問の仕様

### 2.1 状態と所有者

処方箋をベースに、併用薬の追加と後続質問を扱う。現行画面には処方箋から薬を受け取る連携がないため、本変更では既存の初期選択と手動選択をベースとして扱う。患者の処方箋が自動取得されるとは表示しない。

| 状態 | 正典・意味 |
|---|---|
| ベース薬 B | `useMedicineCatalog.selectedYjCodes`。明示的な選択・解除だけで変わる |
| 今回の言及薬 M | 現在の `PromptFieldValue` 内の医薬品トークンから出現順に導出。別stateへ複製しない |
| 継続追加薬 C | 最後に送出成功した質問の、ベースに含まれない薬。チャット側で名前とYJのスナップショットを保持 |
| 今回の対象薬 T | 下記規則で毎回導出。表示とpayloadは同じ結果を使う |

ベースの並びを先にし、続いて言及薬または継続追加薬を並べ、YJで重複排除する。

- Mが1件以上: `T = unique(B + M)`。以前のCは今回使わない。
- Mが0件: `T = unique(B + C)`。薬名を省略した質問でも直前の追加薬を検索対象に残す。
- Tが0件なら送信不可。本文が空、未接続、回答処理中、IME変換中も送信不可。
- 同じ薬が本文に複数回あっても、本文の出現はすべて保持し、YJだけ重複排除する。
- 文字列として入力・貼り付けされた薬名からYJを推測しない。構造化指定は候補から確定したトークンだけを使う。

### 2.2 入力ドックと操作

メッセージ一覧だけがスクロールし、入力ドックを下部に保持する。狭い画面・ソフトウェアキーボード表示時は折り返し、候補と送信操作が画面外へ隠れないことを確認する。

```text
[メッセージ一覧]
[ベースの薬: A × / 処方の薬を追加]
[今回の追加薬: B × / 今回はベースだけにする]
[今回の照合対象: A、B]
[質問入力: この処方に @B を追加してもよい？] [送信]
```

- 1段目は「ベースの薬」。送信で消去・上書きしない。最後の1件も解除可能。
- 2段目はTからBを除いた「今回の追加薬」。本文由来か直前の質問からの継続かを表示する。処方内Aへのメンションを「追加薬」と数えない。
- Mがあるとき、2段目の削除はその薬の全出現トークンを入力から削除する。複数出現を削除することを操作名へ含める。
- Mがないとき、2段目の削除はCからその薬を解除する。
- 新しいトークンを入力すると以前のCを破棄する。最後のトークンを削除した際に古い追加薬が復活しないようにする。Undoでトークンが戻れば、そのトークンをMとして再計算する。
- 「今回はベースだけにする」はCを解除し、ベース外のトークンをすべて削除する。ベースの薬名トークンと通常の文章は残す。
- ベースの選択・解除・並べ替えを明示的に変更したらCを解除する。本文トークンは保持し、今回の対象を再表示する。
- 入力トークンとベースの選択は双方向同期しない。上部でAを解除しても本文にAがあればTにはAが入ることを表示する。

初期選択は既存値を維持し、本文に「イグザレルト」があるかによる自動置換は削除する。表示名解決と対象決定は分離し、カタログ更新や候補取得失敗で別薬へ自動変更しない。静的辞書だけの薬も、入力・継続追加薬には名前とYJを保持する。

### 2.3 ライフサイクルと具体例

送出成功時は `C = TからBを除いた薬` とし、本文とトークンをクリアする。Bは保持する。2段目にはCが継続対象として残る。
送出失敗時は送信処理によって本文、トークン、B、Cを変更しない。入力編集や明示的な解除によって既に変更されたCを復元はしない。

| B | C | 現在のM | 送るT | 送出成功後のB / C |
|---|---|---|---|---|
| A | なし | B | A、B | A / B |
| A | B | なし（その副作用は？） | A、B | A / B |
| A | B | D | A、D | A / D |
| A | なし | A、A | A | A / なし |
| なし | なし | B | B | なし / B |
| なし | B | なし | B | なし / B |
| なし | なし | なし | 送信不可 | 変更なし |

ベース全解除だけを条件に送信を無効化しない。Bが空でもMがあれば送れる。全解除操作ではCも解除されるため、Mも空なら送れない。
新トークンを挿入後に全削除した場合、MもCも空となりBへ戻る。

## 3. 採用パッケージとNext.js連携

### 3.1 最初に行う技術確認

`@react-spectrum/ai` はalphaのため、公式採用をIME動作の保証とは扱わない。実装開始時に `@react-spectrum/ai`、`@react-spectrum/s2`、`unplugin-parcel-macros` の公開バージョンとpeer依存を確認し、互換な具体的バージョンを `--save-exact` で固定する。lockfileも更新する。
採用バージョン、参照資料、型定義、技術確認結果を証跡へ残す。Next.jsはインストール済みガイドを読む。
技術確認では最小PromptFieldでdev・production build、SSR/hydration、日本語IME、候補確定、クリア後のUndo、プレーンテキスト貼り付けを実証する。成立しなければ問題を報告して計画を更新する。独自エディタへ無断で置換しない。

### 3.2 Webpackと既存StyleXの共存

マクロはWebpackで動かす。`frontend/next.config.ts` にマクロプラグインを追加し、サーバー・クライアントのコンパイルで共有する単一インスタンスを設定ファイルのスコープに作る。
既存の `distDir`、`devIndicators`、`reactCompiler` は保持する。公式Next.js手順のS2/macro CSS集約設定を採用バージョンで確認して追加する。既存StyleX/PostCSSの出力・CSS layer順序と共存させる。

以下のすべてを `--webpack` 起動に揃える。package.jsonを経由しない直接起動も検索して更新する。

- `frontend/package.json`: dev / dev:frontend / build。
- `frontend/playwright.config.ts`: モック用Next起動。
- `frontend/playwright.import-integration.config.ts`: 実接続用Next起動。
- `frontend/playwright.ime-manual.config.ts`: 手動IME用Next起動があれば更新。
- その他の試験・スクリプト内の直接 `next dev` / `next build`。

Storybookは別のビルド経路なので、対象UIを掲載する場合はVite側にも公式のマクロ設定を適用してbuild-storybookを検証する。掲載しない場合も既存Storybookを壊さないことを確認する。

### 3.3 Providerと見た目

S2 ProviderのClient Componentを追加し、App Routerのlayoutへ接続する。localeはサーバー・クライアントとも `ja-JP` に固定し、htmlのlangは `ja` を維持する。フォント、背景、カラースキームを公式手順に沿って設定する。
Providerが既存の画面全体へ与える背景・余白・フォントの変化も確認する。既存StyleXの外側レイアウトとS2入力の内側スタイルの責務を分け、S2内部CSSの上書きへ依存しない。S2内のリンクを使う場合はNext router連携を行う。

## 4. 入力・候補・シリアライズ

入力の正典は `PromptFieldValue`。派生した本文やYJを別の編集可能stateとして保持しない。
`PromptTokenField` の `renderCompletions` から既存の `searchMedicines` を呼び、最大8件を返す。候補取得と検索を分離し、旧フック削除時にも既存の辞書とactive catalogueのマージ規則を残す。

トークンは `type: token`、表示名、`value.type: custom`、`anchor: @`、`valueType: medicine`、名前・YJのデータを持つ。データの型とYJの非空を抽出境界で検査する。採用バージョンの実際の型定義に合わせて実装する。
半角 `@` と全角 `＠` を文頭・空白直後・句読点/括弧直後で受け付ける。メールアドレス内は起動しない。全角トリガーでも保存・送信時は半角@へ統一する。空クエリは入力案内、0件は該当なしとし、勝手に別候補へ置換しない。

候補確定は現在のクエリ範囲だけを置換する。カーソル前後・改行・文章順序を保持する。
本文はsegmentsから明示的にシリアライズし、医薬品トークンを `@薬品名` に変換する。標準toStringが@を付けるとは仮定しない。トークン以外のテキストと改行を保持し、全体の前後空白だけを除去する。
コピー/貼り付けはプレーンテキストとし、貼り付けた薬名からトークンやYJを復元しない。カスタムclipboardデータでも意図せず薬の指定が増えないことを技術確認する。

## 5. IME・キー操作・アクセシビリティ

次は保証済みの説明ではなく、採用バージョンで満たすべき受入条件である。

| 操作 | IME変換中 | 候補あり | 通常時 |
|---|---|---|---|
| Enter | IME確定のみ。候補確定・送信なし | 候補確定のみ。送信なし | 条件を満たせば送信 |
| Shift+Enter | IMEへ委ねる | 改行して候補を閉じる | 改行 |
| Tab | IMEへ委ねる | 候補確定、入力フォーカス維持 | 次の操作要素へ移動 |
| 上下矢印 | IMEへ委ねる | 候補移動 | 通常の移動 |
| Escape | 変換キャンセル | 候補を閉じ本文・フォーカス維持 | 本文を変更しない |
| Backspace/Delete | 未確定文字の編集 | クエリ編集 | 隣接トークンは単位削除 |

候補0件でポップアップが開いている場合、Enterは閉じるだけとする。変換中は送信ボタンでも送らない。変換確定に使ったEnterが通常送信へ流れないことを実OSで確認する。
標準コンポーネントで不足する場合は公開APIによる最小限のガードを追加する。内部DOMへ依存したキー制御や、二重の送信ハンドラーを追加しない。
入力には固定のアクセシブル名「質問を入力」を付ける。候補のアクティブ状態、展開状態、候補数、削除操作を伝え、マウス・タッチ・キーボード・読み上げで確認する。

## 6. 送信と履歴

`useChatWebSocket` は入力stateを持たず、`sendMessage(request): SendResult` へ変更する。

```ts
export type SendRequest = {
  content: string;
  productYjCodes: readonly string[];
};
export type SendResult =
  | { sent: true }
  | { sent: false; reason: "empty" | "no-medicine" | "disconnected" | "busy" };
```

送信イベントでPromptFieldValueとB/Cを一度読み、本文・T・表示名を確定する。setState後の再レンダーを送信内容へ依存させない。
フックでも接続、本文、対象0件、処理中を検査し、同期refで二重送信を防ぐ。既存接続ヘルパーのsend成否を使い、成功時だけ履歴追加・処理中への遷移を行う。
`sent: true` の場合だけ呼び出し側がCを更新し、入力と編集履歴をクリアする。クリア後のUndoで送信済み下書きが復活しないことを確認する。
成功はクライアントWebSocketへの送出成功であり、サーバー受領・回答完了とは区別する。
送出後のエラー・切断では入力の自動復元や再送を行わず、既存の中断表示・次回送信履歴からの除外規則を維持する。Cは対象選択として保持し、失敗した回答の成功扱いには使わない。

外部JSONの `type / provider / model / product_yj_codes / messages` を維持する。過去の本文には薬名を残す。発言ごとの構造化YJ保存や、過去薬の根拠を自動で再取得する機能は加えない。省略質問の検索対象は履歴の推測でなくTによって決まる。

## 7. 変更箇所

- `frontend/package.json`、`pnpm-lock.yaml`、`next.config.ts`: 依存固定、Webpack、マクロ、CSS。
- `frontend/app/`のProviderとlayout: locale、フォント、カラースキーム、SSR。
- `medicine-selection`のmodel/候補取得: シリアライズ、YJ抽出、既存検索・取得の再利用。
- `MedicinePromptField.tsx`: 公式入力・候補・IME・アクセシビリティ。
- `useMedicineCatalog.ts`、`MedicineSelector.tsx`: ベース管理、最後の解除、旧自動置換の削除。
- `ChatInputForm.tsx`、`ChatScreen.tsx`、関連styles: 入力ドック、B/M/C/Tの接続と表示。
- `useChatWebSocket.ts`: 引数・結果型、入力state撤去、二重送信防止。
- 各Playwright設定、`e2e/helpers/chat.ts`、関連spec: 起動、セレクタ、操作、payloadの期待値。
- `manual-e2e/ime.spec.ts`: contenteditableの本文・トークン・DOM Selection・送信回数を記録。
- Storybook設定/利用側: 影響範囲を確認し必要なマクロ設定を追加。

medicine-selectionからchatの送信実装へ依存しない。feature間は公開indexを利用する。
旧 `MedicineAutocompleteInput` と旧フックは利用箇所を確認し、置換後の不要コード・互換処理・旧仕様のテストを削除する。共有する候補取得・検索まで消さない。

## 8. 実装順と受入条件

1. Unit 1: パッケージ互換性、全起動経路、Provider、production build、IME・貼り付けの技術確認。
2. Unit 2: 本文抽出、YJ重複排除、B/M/C/Tの状態遷移を純粋処理としてテスト先行実装。
3. Unit 3: 入力・2段ヘッダー・対象表示・解除・省略質問の実装。
4. Unit 4: WebSocket統合、クリア・保持、既存試験ヘルパーとIME記録器の更新。
5. Unit 5: 全体検証。結果はケースと差分版へ対応付ける。

| ID | 条件と期待結果 |
|---|---|
| M01 | A→Bの文中順序、後続文、改行が送信本文に保持される |
| M02 | 同じ薬の複数トークンは本文に残り、YJのみ重複排除される |
| M03 | 2.3の各行についてpayload、B、C、追加薬表示をそれぞれ具体値で確認 |
| M04 | B=Aで@Bを送信後、省略質問でも[A,B]を送り、ベースAは変わらない |
| M05 | 範囲置換・削除・Undo/Redoで本文とYJが一致。全トークン削除で古いCは復活しない |
| M06 | 内外コピー/貼り付けは文字列となり薬の指定を増やさない |
| M07 | キー操作表を候補あり/0件/閉で確認。実OS IME確定Enterと変換中の送信操作で送信0件 |
| M08 | 送出失敗は下書き保持、成功のみクリア。連打1送信、成功後Undoで下書き復活なし |
| M09 | Aの質問後Bへ移っても過去messagesにAの名前が残る |
| M10 | 切断・エラー・再接続でも既存の中断除外規則が維持される |
| M11 | マウス・タッチ・キー・読み上げ、狭い画面でも候補と送信を操作できる |
| M12 | 静的辞書のみの薬・候補取得失敗・カタログ更新で別薬へ自動変更しない |
| M13 | ベース内メンションは追加0件。ベース全解除かつ@Bありなら送信可、全部0件なら不可 |
| M14 | ベース変更、新規メンション、追加薬削除、ベースだけへ戻す操作でCとTが仕様どおり遷移 |
| M15 | dev・build・モック/実接続/IME起動でWebpackとマクロが有効。SSR警告なし、StyleX共存 |

純粋処理のテストは `.test.mjs` 方式を用い、追加ファイルを実行するスクリプトと正確なコマンドを実装時に登録する。既存接続ヘルパーテストだけを新規ロジックの検証として扱わない。
IME記録器は既存inputセレクタとvalue/selectionStart依存を撤去する。合成イベントとWindows Microsoft IME実機の記録を別の層として残す。モックLLM応答で意味理解の成功を判定しない。

## 9. 検証コマンドと完了条件

リポジトリルートから実行する。lintは自動修正なし。E2E・ビルド・IME記録は出力を生成するため「書き込みなし」とは表記しない。

```text
pnpm typecheck:frontend
pnpm --filter frontend exec biome check .
pnpm --filter frontend lint:stylex
node --experimental-strip-types --test frontend/features/chat/api/chatWebSocket.test.mjs
pnpm test:e2e
pnpm --filter frontend test:ime:manual
```

上記に新設の純粋処理テストを必ず追加する。production buildは `MEDI_CHAT_NEXT_DIST_DIR=.next-e2e-build` をPowerShellの環境変数として設定して `pnpm build` を実行し、finallyで元の環境変数へ戻す。通常devの出力を共有しない。
反復中の `pnpm --filter frontend test:e2e:mock` は全体E2Eの代替成功にしない。configured readiness、実OS health、モックChromium、実backend接続を区別する。実接続の外部LLMダブルは実通信と扱わない。

完了報告には差分、採用バージョン、コマンド・場所・終了コード・件数、M01〜M15との対応、実OS IMEの記録、未実施/skip/環境不足を含める。必須項目未実施で全体成功としない。
失敗記録の目次は計画前・エラー後の修正前・完了前に照合する。今回の修正時点では承認済み記録なし。

## 10. 参照

- [S2 Next.js導入ガイド](../../.agents/skills/react-spectrum-s2/references/guides/getting-started.md)
- [React Spectrum AI Components](https://react-spectrum.adobe.com/ai-components)
- [frontend規約](../../docs/agent-guides/frontend.md)
- [検証規約](../../docs/agent-guides/validation.md)
