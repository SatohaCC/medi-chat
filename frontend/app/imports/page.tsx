"use client";

import Link from "next/link";
import { type FormEvent, useRef, useState } from "react";
import { importAttachment } from "../lib/attachmentImport";
import type { AttachmentImportResult } from "../types/attachmentImport";

export default function ImportsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<AttachmentImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy.current) return;
    busy.current = true;
    setSending(true);
    setResult(null);
    setError(null);
    try {
      setResult(await importAttachment(file));
      window.dispatchEvent(new Event("attachment-imported"));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "取り込みに失敗しました。");
    } finally {
      busy.current = false;
      setSending(false);
    }
  }

  return (
    <main className="container">
      <Link href="/">チャットへ戻る</Link>
      <h1>添付文書XMLの取り込み</h1>
      <p>原本XMLを登録し、対象製品の検索と候補に反映します。</p>
      <form onSubmit={submit}>
        <label htmlFor="attachment-xml">XMLファイル</label>
        <input
          id="attachment-xml"
          type="file"
          accept=".xml,application/xml,text/xml"
          disabled={sending}
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setResult(null);
            setError(null);
          }}
        />
        {file && <p>選択したファイル: {file.name}</p>}
        <button type="submit" disabled={!file || sending}>
          {sending ? "送信中…" : "取り込む"}
        </button>
      </form>
      {error && (
        <p role="alert" aria-label="取り込みエラー">
          {error}
        </p>
      )}
      {result && (
        <section aria-label="取り込み結果" aria-live="polite">
          <h2>
            {result.status === "superseded"
              ? "旧版／現在の検索には適用されていません"
              : "登録済み／検索に反映済み"}
          </h2>
          <p>改訂年月ではなく、最初に登録成功した順で採用されます。</p>
          <p>現在適用中のYJ: {result.active_yj_codes.join(", ") || "なし"}</p>
          <p>
            公開世代: {result.generation_id} / 登録順: {result.registration_sequence}
          </p>
          {result.artifacts_deleted && (
            <p>この旧版の所有ファイルは削除済みです。同原本の再送でも復活しません。</p>
          )}
          {result.cleanup_pending.length > 0 && (
            <section aria-label="削除待ち">
              <h3>削除待ち（検索への登録は完了しています）</h3>
              <ul>
                {result.cleanup_pending.map((item) => (
                  <li key={item.version_id}>
                    {item.version_id}: {item.reason}
                  </li>
                ))}
              </ul>
            </section>
          )}
          {result.deleted_version_ids.length > 0 && (
            <p>削除した旧版: {result.deleted_version_ids.join(", ")}</p>
          )}
          {result.reused && (
            <p>同じ原本の登録情報です。新しい登録順は作成していません。</p>
          )}
          <p>{result.document_id}</p>
          <p>原本SHA256: {result.source_sha256}</p>
          <p>
            項目数: {result.section_count} / 検索用項目数: {result.search_unit_count}
          </p>
          <ul>
            {result.products.map((product, index) => (
              <li key={`${product.yj_code}-${index}`}>
                {product.brand_name} {product.yj_code}
              </li>
            ))}
          </ul>
          <ul>
            {result.revisions.map((revision, index) => (
              <li key={`${revision.source_label}-${index}`}>
                {revision.source_label} {revision.year_month} {revision.version}
              </li>
            ))}
          </ul>
          {result.warnings.length > 0 && (
            <>
              <h3>確認が必要な警告</h3>
              <ul>
                {result.warnings.map((warning, index) => (
                  <li key={`${warning.code}-${index}`}>
                    {warning.code}: {warning.reference}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </main>
  );
}
