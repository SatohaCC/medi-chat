export function backendBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");
  if (configured) return configured;
  if (typeof window === "undefined" || window.location.port !== "3000") {
    return "";
  }
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

export function wsBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  if (typeof window === "undefined") {
    return "ws://localhost:8000/api/ws";
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host =
    window.location.port === "3000"
      ? `${window.location.hostname}:8000`
      : window.location.host;
  return `${protocol}//${host}/api/ws`;
}
