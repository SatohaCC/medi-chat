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
