# 実旧manifest SQLite fixture

`pre_registration_manifest_v3.sqlite3.gz` は旧manifest方式の実PMDA索引をread-only SQLite backupで保全したものです。公開PMDA 7文書 / 1686旧fragment units / 15 medicinesを持ち、未管理v3 schema、registration tableなし、freelist=0、integrity_check=okです。現行sourceの7文書に対応するXML原本SHAと薬剤metadataの一致を採取時に検証しました。個人home絶対pathは含みません。

- 由来: 2026-10-12に保全した実旧manifest索引。原物SHA256 `877b8dbd4b003fd40c8ba446874fbc26ed5df0ddafea52d9825b3e5d0dc00d35`。原物はread-onlyで保持し、更新していません。
- 展開backup: 8,511,488 bytes / SHA256 `b079a9696e99e95e3e0ee9e48e4ea9640df91fa09e3817c9ab192ecb6afe6681`。
- gzip: 1,209,831 bytes / SHA256 `dd571bd3c28ba13479240fb8422c4404df1c29f391f15e66ffddd5d3e02983a4`、mtime=0。
- 全schema/rowを含むlogical snapshot SHA256 `40399571c204e996f059e8ad683b0002df1a86eeccde3cb5890c8c7a11caf720`。
- 保存fingerprintは`manifest:193:1790496847878189900:`で始まる歴史的値を維持しています。原物からbackupへの論理snapshot一致を確認しました。

startup回帰はgzip CRC・全展開byte SHA・schema/content・manifest・件数を確認し、pytestの一時copyだけを既存検証済みstamp経路で`0001_v3_schema`にします。その後、既存の旧版OS起動拒否→明示Alembic/初期登録→同一copyのOS health回復を検証します。運用DB/原物はテストから読みません。

既存の`pre_registration_v3.sqlite3.gz`（7/267/15、content-v1、0001）とは別の歴史的入力です。正規化・VACUUM・新鮮builderの出力への置換は行っていません。
