import { type FormEvent, useRef, useState } from "react";
import { importAttachment } from "../api/attachmentImport";
import type { AttachmentImportResult } from "../model/attachmentImport";

export function useAttachmentImport() {
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

  return { file, setFile, sending, result, setResult, error, setError, submit };
}
