# 登録前v3 SQLite fixture

`pre_registration_v3.sqlite3.gz` は、明示初期登録の直前に採取・保全した実7文書の整合SQLite backupを標準gzipで保存したfixture。TC111/119の入力は旧 `0001_v3_schema`、7 documents / 267 units / 15 medicines、登録tableなし、integrity_check = ok。

- 由来: 2026-10-10 の承認済み運用初期登録前backup。テスト実行時は証跡ディレクトリや運用DBを参照しない。
- 展開DB: 11,993,088 bytes。
- 展開SHA256: `959480741dea2792d4c79b7d45f5f071cd93664d338529a91e8a489c4116a9f0`。
- gzip: 3,831,039 bytes / SHA256 `4c1aa389ab992ec44cb4b4e6ec51ea0e7bcda19b04a449242ad27670c6628b10`。mtime = 0。
- `gzip.decompress` のCRC検証後、pytest固有tmpへ展開し、全byte SHA・schema・件数・未登録stateを独立assertする。そこから明示migration / 初期登録 / 故障注入 / 全table-row復元 / 実OS healthを行う。

現在の運用DBは登録済みheadへ進んでいるため、旧入力の代用には使わない。展開DBのVACUUMや期待件数の緩和は行わない。
