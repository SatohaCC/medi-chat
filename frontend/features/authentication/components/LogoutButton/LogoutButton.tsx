"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import { logout } from "../../api";

export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      {error && <span role="alert">{error}</span>}
      <Button
        appearance="secondary"
        pending={pending}
        onActivate={async () => {
          setPending(true);
          setError("");
          try {
            await logout();
            router.replace("/login");
          } catch (error) {
            setError(
              error instanceof Error ? error.message : "ログアウトできませんでした。",
            );
          } finally {
            setPending(false);
          }
        }}
      >
        ログアウト
      </Button>
    </>
  );
}
