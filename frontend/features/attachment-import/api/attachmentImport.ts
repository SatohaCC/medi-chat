import { backendBaseUrl } from "../../../shared/api/endpoints";
import type { AttachmentImportResult } from "../model/attachmentImport";

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
