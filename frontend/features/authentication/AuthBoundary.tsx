"use client";

import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import {
  ensureAuthenticated,
  forgetAuthentication,
  type Principal,
} from "../../shared/api/authentication";

export function AuthBoundary({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const loginPage = path === "/login";

  useEffect(() => {
    if (loginPage) return;
    let active = true;
    const lost = () => {
      setPrincipal(null);
      const target = window.location.pathname + window.location.search;
      router.replace(`/login?returnTo=${encodeURIComponent(target)}`);
    };
    const ready = (event: Event) =>
      setPrincipal((event as CustomEvent<Principal>).detail);
    const channel =
      typeof BroadcastChannel !== "undefined"
        ? new BroadcastChannel("medi-chat-authentication")
        : null;
    if (channel)
      channel.onmessage = (event) => {
        if (event.data === "logout") forgetAuthentication();
      };
    window.addEventListener("medi-chat-auth-lost", lost);
    window.addEventListener("medi-chat-auth-ready", ready);
    ensureAuthenticated()
      .then((value) => {
        if (active) setPrincipal(value);
      })
      .catch(() => {
        if (active) lost();
      });
    return () => {
      active = false;
      channel?.close();
      window.removeEventListener("medi-chat-auth-lost", lost);
      window.removeEventListener("medi-chat-auth-ready", ready);
    };
  }, [loginPage, router]);

  useEffect(() => {
    if (!principal || loginPage) return;
    const timer = setTimeout(
      () => {
        void ensureAuthenticated().catch(() => {});
      },
      Math.max(0, principal.expires_at * 1000 - Date.now() + 100),
    );
    return () => clearTimeout(timer);
  }, [principal, loginPage]);

  if (loginPage) return children;
  if (!principal)
    return (
      <main aria-busy="true">
        <p role="status">ログイン状態を確認しています…</p>
      </main>
    );
  return children;
}
