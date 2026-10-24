import { backendBaseUrl } from "./endpoints";

export interface Principal {
  user_id: string;
  expires_at: number;
}

let current: Principal | null = null;
let pending: Promise<Principal> | null = null;

export function safeReturnTo(value: string | null): string {
  if (
    !value?.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    Array.from(value).some((character) => character.charCodeAt(0) < 32)
  )
    return "/";
  try {
    const url = new URL(value, "https://medi-chat.invalid");
    if (url.origin !== "https://medi-chat.invalid" || url.pathname === "/login")
      return "/";
    return url.pathname + url.search + url.hash;
  } catch {
    return "/";
  }
}

export function forgetAuthentication(): void {
  current = null;
  if (typeof window !== "undefined")
    window.dispatchEvent(new Event("medi-chat-auth-lost"));
}

function accepted(value: Principal): Principal {
  if (
    !value.user_id ||
    !Number.isSafeInteger(value.expires_at) ||
    value.expires_at * 1000 <= Date.now()
  )
    throw new Error("認証情報を確認できませんでした。再度ログインしてください。");
  current = value;
  if (typeof window !== "undefined")
    window.dispatchEvent(new CustomEvent("medi-chat-auth-ready", { detail: value }));
  return value;
}

async function requestMe(): Promise<Response> {
  return fetch(`${backendBaseUrl()}/api/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });
}

export async function ensureAuthenticated(): Promise<Principal> {
  if (current && current.expires_at * 1000 > Date.now()) return current;
  if (pending) return pending;
  pending = (async () => {
    const response = await requestMe();
    if (response.ok) return accepted(await response.json());
    if (response.status !== 401)
      throw new Error("認証サービスに接続できません。再度ログインしてください。");
    if (!navigator.locks)
      throw new Error("セッションが切れました。再度ログインしてください。");
    return navigator.locks.request("medi-chat-auth-refresh", async () => {
      // A different tab may already have rotated the shared HttpOnly cookies.
      const latest = await requestMe();
      if (latest.ok) return accepted(await latest.json());
      if (latest.status !== 401) throw new Error("認証サービスに接続できません。");
      const refreshed = await fetch(`${backendBaseUrl()}/api/auth/refresh`, {
        method: "POST",
        credentials: "include",
        cache: "no-store",
        headers: { "X-Medi-Chat-CSRF": "1" },
      });
      if (!refreshed.ok)
        throw new Error("セッションが切れました。再度ログインしてください。");
      return accepted(await refreshed.json());
    });
  })();
  try {
    return await pending;
  } catch (error) {
    forgetAuthentication();
    throw error;
  } finally {
    pending = null;
  }
}

export async function login(loginId: string, password: string): Promise<void> {
  const response = await fetch(`${backendBaseUrl()}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-Medi-Chat-CSRF": "1" },
    body: JSON.stringify({ login_id: loginId, password }),
  });
  if (!response.ok) {
    if (response.status === 429)
      throw new Error("試行回数が多いため、時間をおいてお試しください。");
    if (response.status === 503)
      throw new Error("認証サービスを利用できません。時間をおいてお試しください。");
    throw new Error("ログインIDまたはパスワードを確認してください。");
  }
  accepted(await response.json());
}

export async function logout(): Promise<void> {
  const operation = async () => {
    const response = await fetch(`${backendBaseUrl()}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
      cache: "no-store",
      headers: { "X-Medi-Chat-CSRF": "1" },
    });
    if (!response.ok)
      throw new Error("ログアウトを完了できませんでした。再度お試しください。");
    forgetAuthentication();
    if (typeof BroadcastChannel !== "undefined") {
      const channel = new BroadcastChannel("medi-chat-authentication");
      channel.postMessage("logout");
      channel.close();
    }
  };
  if (navigator.locks) await navigator.locks.request("medi-chat-auth-refresh", operation);
  else await operation();
}

/** Never automatically repeat a mutation or an LLM generation. */
export const authenticatedFetch: typeof fetch = async (input, init) => {
  await ensureAuthenticated();
  const headers = new Headers(init?.headers);
  const method = (
    init?.method || (input instanceof Request ? input.method : "GET")
  ).toUpperCase();
  if (!["GET", "HEAD"].includes(method)) headers.set("X-Medi-Chat-CSRF", "1");
  const options = { ...init, headers, credentials: "include" as const };
  const response = await fetch(input, options);
  if (response.status !== 401) return response;
  current = null;
  await ensureAuthenticated();
  if (method === "GET" || method === "HEAD") return fetch(input, options);
  throw new Error("セッションを更新しました。操作をもう一度実行してください。");
};
