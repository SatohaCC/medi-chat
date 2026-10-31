"use client";

import { Button } from "@react-spectrum/s2/Button";
import { FileTrigger } from "@react-spectrum/s2/FileTrigger";
import { Content, Heading, InlineAlert } from "@react-spectrum/s2/InlineAlert";
import * as stylex from "@stylexjs/stylex";
import { AppHeader } from "../../../shared/ui/AppHeader";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import { useAttachmentImport } from "../hooks/useAttachmentImport";
import { ImportHistory } from "./ImportHistory";
import { styles } from "./ImportScreen.styles";

export function ImportScreen() {
  const { file, setFile, sending, result, setResult, error, setError, submit } =
    useAttachmentImport();

  return (
    <div data-screen="imports" {...stylex.props(layout.root)}>
      <AppHeader />
      <main {...stylex.props(styles.main)}>
        <div {...stylex.props(styles.headerRow)}>
          <div>
            <h1 {...stylex.props(styles.title)}>添付文書XMLの取り込み</h1>
            <p {...stylex.props(styles.description)}>
              原本XMLを登録し、対象製品の検索と候補に反映します。
            </p>
          </div>
        </div>

        <form {...stylex.props(styles.form)} onSubmit={submit}>
          <FileTrigger
            acceptedFileTypes={[".xml", "application/xml", "text/xml"]}
            onSelect={(files) => {
              const selected = files?.item(0);
              if (selected) {
                setFile(selected);
                setResult(null);
                setError(null);
              }
            }}
          >
            <Button
              variant="secondary"
              isDisabled={sending}
              aria-label="XMLファイルを選択"
            >
              XMLファイルを選択
            </Button>
          </FileTrigger>
          <Button type="submit" isDisabled={!file} isPending={sending}>
            {sending ? "送信中…" : "取り込む"}
          </Button>
        </form>

        {file && <p {...stylex.props(styles.fileInfo)}>選択したファイル: {file.name}</p>}

        {error && (
          <section aria-label="取り込みエラー">
            <InlineAlert variant="negative">
              <Heading>取り込めませんでした</Heading>
              <Content>{error}</Content>
            </InlineAlert>
          </section>
        )}

        {result && (
          <section
            aria-label="取り込み結果"
            aria-live="polite"
            {...stylex.props(styles.resultCard)}
          >
            <h2 {...stylex.props(styles.resultTitle)}>
              {result.status === "superseded"
                ? "旧版／現在の検索には適用されていません"
                : "登録済み／検索に反映済み"}
            </h2>
            <p {...stylex.props(styles.resultMutedText)}>
              改訂年月ではなく、最初に登録成功した順で採用されます。
            </p>
            <p {...stylex.props(styles.resultText)}>
              現在適用中のYJ: {result.active_yj_codes.join(", ") || "なし"}
            </p>
            <p {...stylex.props(styles.resultText)}>
              公開世代: {result.generation_id} / 登録順: {result.registration_sequence}
            </p>
            {result.artifacts_deleted && (
              <p {...stylex.props(styles.resultMutedText)}>
                この旧版の所有ファイルは削除済みです。同原本の再送でも復活しません。
              </p>
            )}
            {result.cleanup_pending.length > 0 && (
              <section
                aria-label="削除待ち"
                style={{ display: "flex", flexDirection: "column", gap: 4 }}
              >
                <h3 {...stylex.props(styles.resultSectionTitle)}>
                  削除待ち（検索への登録は完了しています）
                </h3>
                <ul {...stylex.props(styles.resultList)}>
                  {result.cleanup_pending.map((item) => (
                    <li key={item.version_id}>
                      {item.version_id}: {item.reason}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {result.deleted_version_ids.length > 0 && (
              <p {...stylex.props(styles.resultMutedText)}>
                削除した旧版: {result.deleted_version_ids.join(", ")}
              </p>
            )}
            {result.reused && (
              <p {...stylex.props(styles.resultMutedText)}>
                同じ原本の登録情報です。新しい登録順は作成していません。
              </p>
            )}
            <p {...stylex.props(styles.resultText)}>{result.document_id}</p>
            <p {...stylex.props(styles.resultMutedText)}>
              原本SHA256: {result.source_sha256}
            </p>
            <p {...stylex.props(styles.resultText)}>
              項目数: {result.section_count} / 検索用項目数: {result.search_unit_count}
            </p>
            <ul {...stylex.props(styles.resultList)}>
              {result.products.map((product, index) => (
                <li key={`${product.yj_code}-${index}`}>
                  {product.brand_name} {product.yj_code}
                </li>
              ))}
            </ul>
            <ul {...stylex.props(styles.resultList)}>
              {result.revisions.map((revision, index) => (
                <li key={`${revision.source_label}-${index}`}>
                  {revision.source_label} {revision.year_month} {revision.version}
                </li>
              ))}
            </ul>
            {result.warnings.length > 0 && (
              <div {...stylex.props(styles.warningCard)}>
                <h3 {...stylex.props(styles.warningTitle)}>確認が必要な警告</h3>
                <ul {...stylex.props(styles.warningList)}>
                  {result.warnings.map((warning, index) => (
                    <li key={`${warning.code}-${index}`}>
                      {warning.code}: {warning.reference}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
        <ImportHistory />
      </main>
    </div>
  );
}
