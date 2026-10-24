# 個人認証の検証記録

実施日: 2026-10-24。以下は認証実装と開発監視・hooks修正に対するローカル検証結果。リモートCIの結果はPRで別途確認する。

## 実装した範囲

- FastAPIの個人ログイン・更新・ログアウト・meと、HTTP/WS全体の認証境界。
- アクセスJWT30分、更新系列7日の絶対期限。更新トークンはDBにハッシュ保存し、原子的交換・再利用検出・系列失効を実装。
- アプリのUserId、ローカル資格情報、外部識別子対応を分離。通常APIの認証経路はDB非依存。
- Argon2id、共有ログイン試行制限、ハッシュ計算の並列数制限、Cookie・Origin・CSRF対策。
- ログイン画面、更新のsingle-flightとWeb Locks、ログアウトのタブ通知、WS期限切れと生成キャンセル。旧秘密URL方式を削除。
- 管理CLI、鍵生成、設定例、Alembic追加revision、依存ロック・pylock・Vercel requirementsの正規更新。

## 実行結果

| 検証 | 結果・範囲 |
| --- | --- |
| `pnpm quality:changed` | コミット前の最終共通実行は終了コード0。鍵ファイル対応・スキーマ型修正・開発監視・hooks修正を含め、backend・frontend・開発ツールの品質検査を実施 |
| `pnpm quality:backend` | 最終backend差分で終了コード0。Ruff・Import Linter・Application/Domainハーネス・型・DB不要テストを実施 |
| DB不要pytest | 1,134 passed、345 deselected。実DB・非公開原本を必要とする試験を成功件数へ含めない |
| Application/Domainハーネスの検出能力 | 66 passed / 73 passed。構造適合と業務挙動の検証は別 |
| frontendのNode単体 | 85 passed。更新集約、2タブ相当のロック、再送抑止、returnTo、既存WS等 |
| 開発ツールNode / hooks Python | 18 passed、Windowsのsignal試験2件skip / 10 passed。skipを成功に含めない |
| frontend lint・format・StyleX・型 | 共通品質入口で成功 |
| `pnpm build` | 最終frontend差分で成功。loginを含む6ページのrouteを生成 |
| `pnpm --filter frontend test:e2e:access` | 最終実行3 passed。実Next.js/Chromium＋APIモック。ログイン・元画面復帰・2タブの単一更新とログアウト通知・375px幅を観測 |
| 既存ブラウザ回帰4ファイル | 23 passed、1 failed。チャット・取り込み・分割送信・SSRを実施。残る1件は下記 |
| 設定・鍵生成の限定試験 | 専用ファイル対応後8 passed。公開環境の鍵管理成功とは扱わない |
| 通常dotenvのconfigured gate | 実OSのFastAPI起動・認証付きread-only health成功。実行した専用portのprocessは試験終了時に終了 |

初回の起動・検証では、設定不足、pytestの隔離mini-projectからのproject import、型・import順・StyleX指定・clientディレクティブ等の失敗が発生した。上表は修正後の結果であり、途中失敗を成功へ混ぜていない。

## 残るブラウザ失敗

`frontend/e2e/chat.spec.ts`の「薬剤・モデルを指定して質問し、回答と根拠を表示して次の会話へ引き継ぐ」は、`Google (Gemini 3.8 Flash)`の選択でtimeoutする。

画面と`frontend/features/chat/model/chat.ts`を確認すると、この選択肢は非表示である。現在のHEADでも同モデルはコメントアウトされており、モデル設定は本差分で変更していない。認証変更前の実ブラウザbaseline自体は未実施であり、「変更前の同試験を実行して失敗確認した」とは扱わない。認証対応のために非表示モデルを再有効化したり、試験をskipへ変更したりしていない。

## ローカル開発起動の復旧

ユーザー提示の`Authentication configuration is missing or invalid`は、通常開発環境にAUTH設定がないため発生した。開発用3072bit RSA鍵をGit管理外の`.auth/`へ作成し、`.env.local`にはFastAPI専用の秘密鍵ファイルパスを設定した。共有dotenv本文には秘密PEMを残さない。

確認した接続先はloopbackの`medi_chat_dev`。revisionを`pg_20261019_04`から`pg_20261024_05`へ更新し、認証テーブル6件を追加した。原本・既存業務データは削除していない。runtime roleの認証テーブルDML権限もread-onlyで確認した。

Dockerの資格情報取得・保存についてユーザーの明示許可を得たが、ownerパスワードはコンテナ環境へ保存されていなかった。代わりに既存のコンテナ内owner接続を使い、Alembicが生成した当該revisionのSQLを適用した。パスワードの抽出・保存は行っておらず、移行用URLを推測して追加していない。

設定後、通常dotenvと新revisionでconfigured gateが成功した。これは起動・read-only healthの確認であり、実PostgreSQLの全認証契約試験の代用ではない。

初期アカウントは未作成。管理者が次の対話CLIでログインID・パスワードを設定する。

```powershell
uv run --project backend python -m backend.infrastructure.cli.authentication create
pnpm dev
```

## 負荷の参考測定

Windows・Python 3.14・論理CPU16、RSA2048の試験鍵、DBなしの局所測定。実開発鍵のRSA3072やVercel性能へそのまま換算しない。CPU秒は当該Pythonプロセス、RSSは測定終了時63.73MiBで、ピークメモリではない。

| 対象 | samples / workers | p50 ms | p95 ms | wall秒 / CPU秒 |
| --- | --- | --- | --- | --- |
| JWT検証 | 1000 / 1 | 0.128 | 0.225 | 0.147 / 0.156 |
| JWT検証 | 1000 / 8 | 1.214 | 1.556 | 0.168 / 0.219 |
| Argon2id照合 | 20 / 1 | 22.464 | 23.869 | 0.451 / 0.438 |
| Argon2id照合 | 20 / 2 | 25.467 | 26.767 | 0.257 / 0.516 |

通常APIの認証には署名検証だけを使い、パスワード照合を行わない。認証用DB・外部通信を呼ばない契約をユースケースとHTTP試験でも観測した。上記はAPI全体のレイテンシ・同時利用可能人数・本番SLOの達成を示さない。更新トランザクションの実DB負荷測定は未実施。

## 開発監視の誤再起動修正（2026-10-24）

`scripts/dev-backend.mjs`が旧401コード`access_required`を期待し、現在の`authentication_required`を異常と判断していた。稼働中の8000番への未認証・読み取り専用probeでも現在の401コードを確認した。判定を現行契約に変更し、試験子プロセスの寿命を延ばして修正前の誤再起動を再現した（終了コード1）。修正後の監視試験は9 passed、Windowsシグナル試験2 skipped。任意の401と認証利用不能503は正常扱いせず、応答途絶時の再起動も検証した。通常pnpm dev全体の長時間連続運転は未検証。反映には監視プロセスの再起動が必要。

## 未実施事項

- 実PostgreSQL契約8件を`backend/tests/integration/test_postgres_authentication.py`へ追加。既存CIの`pnpm test:postgres`対象だが、この作業中のCI実行は未実施。
- 実DBを使うブラウザ回帰のfixtureには明示的な試験利用者を用意したが、当該ブラウザ層は未実施。APIモック付きChromiumと区別する。
- ブラウザ全体のvisual snapshot再生成・全ファイル実行、Vercel Preview、実OIDC、外部LLM通信は未実施。
- 本番設定・本番DB・実ユーザー作成・本番公開は未実施。

## 証跡と再発防止候補

作業ログはリポジトリルートからの相対パス`tmp/auth-validation/`へ保存した。`backend-final.txt`、`quality-complete.txt`、`auth-browser-final.txt`、`browser-regression.txt`、`build-final.txt`、`load.json`を区別する。これらはローカル試験成果物で、Git管理へ追加していない。

必須認証設定導入時の通常起動確認について、`.agents/lessons/pending_review/LESSON-013.md`へ承認待ちの観察・提案を記録した。未承認のため規約・INDEXへ登録していない。Next.jsが生成した`frontend/AGENTS.md`の見出し変更は、そのガイドに従って保持した。
