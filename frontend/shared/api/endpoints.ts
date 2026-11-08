export function backendBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");
  if (configured) return configured;
  if (typeof window === "undefined" || window.location.port !== "3000") {
    return "";
  }
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}
