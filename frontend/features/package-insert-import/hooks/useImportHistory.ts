import { useEffect, useState } from "react";
import { listPackageInsertImports } from "../api/packageInsertImport";
import type { PackageInsertImportPage } from "../model/packageInsertImport";

export function useImportHistory() {
  const [request, setRequest] = useState({ offset: 0 });
  const [page, setPage] = useState<PackageInsertImportPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listPackageInsertImports(request.offset, controller.signal)
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
    window.addEventListener("package-insert-imported", imported);
    return () => window.removeEventListener("package-insert-imported", imported);
  }, []);

  return {
    page,
    loading,
    error,
    setOffset: (offset: number) => setRequest({ offset }),
    refresh: () => setRequest((value) => ({ offset: value.offset })),
  };
}
