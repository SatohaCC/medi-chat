import { type FormEvent, useRef, useState } from "react";
import { importPackageInsert } from "../api/packageInsertImport";
import type { PackageInsertImportResult } from "../model/packageInsertImport";

export function usePackageInsertImport() {
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<PackageInsertImportResult | null>(null);
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
      setResult(await importPackageInsert(file));
      window.dispatchEvent(new Event("package-insert-imported"));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "取り込みに失敗しました。");
    } finally {
      busy.current = false;
      setSending(false);
    }
  }

  return { file, setFile, sending, result, setResult, error, setError, submit };
}
