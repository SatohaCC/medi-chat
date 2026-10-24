# 添付文書の取り込み・登録

`/imports`でPMDAのXMLを1つ選択して送信します。原本bytea・完全構造・検索投影をDBへ保存し、登録成功時にactive世代と医薬品候補へ即時反映します。保管だけを行う操作ではありません。文書情報・改訂・件数・図欠落などの警告に加えて、登録・置換・削除待ちの状態を表示します。

同じYJコードは原XMLの改訂年月（YYYY-MM）が最も新しい添付文書を採用します。古い文書を後から登録しても公開先を戻しません。同じ改訂年月の別原本は409、改訂年月の欠落は422で拒否します。旧文書の別YJがまだactiveなら旧版を保持し、active参照がなくなった版の保持payloadをDBで回収します。進行中の読取はread-only REPEATABLE READ/MVCCで旧版を一貫して参照できます。同一原本の再送は以前の版を再有効化しません。

保存先は`MEDI_CHAT_DATABASE_URL`で明示したPostgreSQLです。旧SQLite/JSONLの移行・互換読取は提供せず、空DBへ原本から初期登録します。起動時の自動DDL・初期登録・清掃はありません。整合した清掃待ちは起動を妨げず、`pnpm db:maintenance`または登録後の限定再試行で収束させます。原本exportや完全構造からの検索投影rebuildは[backendの手順](../architecture/backend-design.md#検索インデックスの構築)を参照してください。XMLは10MiB、multipart全体は11MiB、変換成果物は32MiBまでです。

`POST /api/attachment-imports`はmultipartの`file`1つを受け取り、新規201・同一原本の再送200とLocationを返します。LocationへのGETで保存結果を再読込できます。原本や保存先を取得する公開APIはありません。

XML取り込み画面には登録履歴を新しい登録順で表示します。`GET /api/attachment-imports?limit=20&offset=0`はファイル名・製品・改訂年月・現在適用中のYJ・保存データ削除状態を返します（limitは1～100、既定50）。削除済み旧版も履歴に残り、ファイル名が失われている場合は文書IDを表示します。一覧は初回・手動更新・取り込み成功時に取得し、定期ポーリングは行いません。

開発環境とE2Eの実行方法は[ローカル開発](local-development.md)を参照してください。
