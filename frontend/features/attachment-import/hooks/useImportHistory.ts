import { useEffect, useState } from "react";
import { listAttachmentImports } from "../api/attachmentImport";
import type { AttachmentImportPage } from "../model/attachmentImport";

export function useImportHistory() {
  const [request, setRequest] = useState({ offset: 0 });
  const [page, setPage] = useState<AttachmentImportPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listAttachmentImports(request.offset, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setPage(value);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) {
          setError(
            failure instanceof Error ? failure.message : "一覧の取得に失敗しました。",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [request]);

  useEffect(() => {
    const imported = () => {
      setRequest({ offset: 0 });
    };
    window.addEventListener("attachment-imported", imported);
    return () => window.removeEventListener("attachment-imported", imported);
  }, []);

  return {
    page,
    loading,
    error,
    setOffset: (offset: number) => setRequest({ offset }),
    refresh: () => setRequest((value) => ({ offset: value.offset })),
  };
}
