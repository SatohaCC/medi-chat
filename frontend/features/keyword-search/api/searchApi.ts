import { backendBaseUrl } from "../../../shared/api/endpoints";
import type { KeywordSearchResponse } from "../model/search";

export async function searchPackageInserts(
  query: string,
  yjCodes: string[] = [],
): Promise<KeywordSearchResponse> {
  const base = backendBaseUrl();
  const params = new URLSearchParams();
  params.set("q", query);
  for (const yj of yjCodes) {
    if (yj.trim()) {
      params.append("yj_codes", yj.trim());
    }
  }

  const url = `${base}/api/search?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) {
    let errorMsg = `検索エラー (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorMsg =
          typeof errJson.detail === "string"
            ? errJson.detail
            : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return res.json();
}
