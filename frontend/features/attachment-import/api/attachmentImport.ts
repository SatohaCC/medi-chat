import { backendBaseUrl } from "../../../shared/api/endpoints";
import type {
  AttachmentImportPage,
  AttachmentImportResult,
} from "../model/attachmentImport";

export async function listAttachmentImports(
  offset: number,
  signal: AbortSignal,
): Promise<AttachmentImportPage> {
  const response = await fetch(
    `${backendBaseUrl()}/api/attachment-imports?limit=20&offset=${offset}`,
    { cache: "no-store", signal },
  );
  if (!response.ok) throw new Error("取り込み済みXMLの一覧を取得できませんでした。");
  return response.json();
}

export async function importAttachment(file: File): Promise<AttachmentImportResult> {
  // Keep every HTTP body below the Function payload limit. Small originals use
  // multipart; larger originals are assembled and verified in PostgreSQL.
  if (file.size > 3 * 1024 * 1024) return importLargeAttachment(file);
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${backendBaseUrl()}/api/attachment-imports`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.detail?.message || "取り込みに失敗しました。再送してください。",
    );
  }
  return response.json();
}

async function uploadRequest(path: string, body?: BodyInit, contentType?: string) {
  const response = await fetch(`${backendBaseUrl()}/api/attachment-imports${path}`, {
    method: "POST",
    headers: contentType ? { "Content-Type": contentType } : undefined,
    body,
  });
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new Error(
      result?.detail?.message || "取り込みに失敗しました。再送してください。",
    );
  }
  return response;
}

async function importLargeAttachment(file: File): Promise<AttachmentImportResult> {
  if (file.size > 10 * 1024 * 1024)
    throw new Error("XMLファイルは10MiB以内で選択してください。");
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  const sourceSha256 = Array.from(new Uint8Array(digest), (value) =>
    value.toString(16).padStart(2, "0"),
  ).join("");
  const started = await uploadRequest(
    "/uploads",
    JSON.stringify({
      filename: file.name,
      byte_size: file.size,
      source_sha256: sourceSha256,
    }),
    "application/json",
  );
  const session: { upload_id: string; chunk_bytes: number } = await started.json();
  if (
    !Number.isSafeInteger(session.chunk_bytes) ||
    session.chunk_bytes < 1 ||
    session.chunk_bytes > 3 * 1024 * 1024
  ) {
    throw new Error("送信設定を確認できませんでした。再送してください。");
  }
  for (
    let offset = 0, index = 0;
    offset < file.size;
    offset += session.chunk_bytes, index++
  ) {
    await uploadRequest(
      `/uploads/${session.upload_id}/parts/${index}`,
      file.slice(offset, offset + session.chunk_bytes),
      "application/octet-stream",
    );
  }
  const completed = await uploadRequest(`/uploads/${session.upload_id}/complete`);
  return completed.json();
}
