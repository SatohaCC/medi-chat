"use client";

import * as stylex from "@stylexjs/stylex";
import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import { FilePicker } from "../../../../shared/component/FilePicker";
import { Notice } from "../../../../shared/component/Notice";
import { PageLayout } from "../../../../shared/component/PageLayout";
import { AppHeader } from "../../../app-shell/components/AppHeader";
import { usePackageInsertImport } from "../../hooks/usePackageInsertImport";
import { ImportHistory } from "../ImportHistory";
import { styles } from "./ImportScreen.styles";

export function ImportScreen() {
  const { file, setFile, sending, result, setResult, error, setError, submit } =
    usePackageInsertImport();

  return (
    <PageLayout screen="imports">
      <AppHeader />
      <main {...stylex.props(styles.main)}>
        <div {...stylex.props(styles.headerRow)}>
          <div>
            <h1 {...stylex.props(styles.title)}>添付文書XMLを登録</h1>
            <p {...stylex.props(styles.description)}>
              対象製品の電子添文XMLを登録すると、その製品の検索に利用できます。
            </p>
          </div>
        </div>

        <section aria-labelledby="import-steps-title">
          <h2 id="import-steps-title">登録方法</h2>
          <ol>
            <li>対象製品の電子添文XMLを用意します。</li>
            <li>「XMLファイルを選択」からファイルを選び、「XMLを登録」を押します。</li>
            <li>登録結果で、検索に適用されている製品と改訂年月を確認します。</li>
          </ol>
          <p>
            同じ製品の複数の改訂版がある場合、改訂年月ではなく登録に成功した順で検索に使う版が決まります。登録後は、画面の適用状況を確認してください。
          </p>
        </section>

        <form {...stylex.props(styles.form)} onSubmit={submit}>
          <FilePicker
            label="XMLファイルを選択"
            accept={[".xml", "application/xml", "text/xml"]}
            disabled={sending}
            onSelect={(selected) => {
              setFile(selected);
              setResult(null);
              setError(null);
            }}
          />
          <Button type="submit" disabled={!file} pending={sending}>
            {sending ? "登録中…" : "XMLを登録"}
          </Button>
        </form>

        {file && <p {...stylex.props(styles.fileInfo)}>選択したファイル: {file.name}</p>}

        {error && (
          <section aria-label="取り込みエラー">
            <Notice title="取り込めませんでした">{error}</Notice>
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
                ? "登録しました（現在の検索には適用されていません）"
                : "登録しました（検索に適用されています）"}
            </h2>
            <p {...stylex.props(styles.resultMutedText)}>
              登録した製品と改訂年月を確認してください。
            </p>
            <h3 {...stylex.props(styles.resultSectionTitle)}>登録した製品</h3>
            <ul>
              {result.products.map((product, index) => (
                <li key={`${product.yj_code}-${index}`}>
                  {product.brand_name || "製品名不明"}
                </li>
              ))}
            </ul>
            <h3 {...stylex.props(styles.resultSectionTitle)}>改訂年月</h3>
            <ul {...stylex.props(styles.resultList)}>
              {result.revisions.map((revision, index) => (
                <li key={`${revision.source_label}-${index}`}>
                  {revision.year_month || "不明"}
                  {revision.version ? `（${revision.version}）` : ""}
                  {revision.source_label ? ` · ${revision.source_label}` : ""}
                </li>
              ))}
            </ul>
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
            <details>
              <summary>管理用の登録情報を表示</summary>
              <p {...stylex.props(styles.resultText)}>
                現在適用中のYJコード: {result.active_yj_codes.join(", ") || "なし"}
              </p>
              <p {...stylex.props(styles.resultText)}>
                公開世代: {result.generation_id || "なし"} / 登録順:{" "}
                {result.registration_sequence ?? "なし"}
              </p>
              <p {...stylex.props(styles.resultText)}>
                項目数: {result.section_count} / 検索用項目数: {result.search_unit_count}
              </p>
              <p {...stylex.props(styles.resultText)}>登録ID: {result.document_id}</p>
              <p {...stylex.props(styles.resultMutedText)}>
                原本SHA256: {result.source_sha256}
              </p>
              <ul {...stylex.props(styles.resultList)}>
                {result.products.map((product, index) => (
                  <li key={`${product.yj_code}-${index}`}>
                    {product.yj_code || "YJコードなし"}
                  </li>
                ))}
              </ul>
            </details>
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
    </PageLayout>
  );
}
