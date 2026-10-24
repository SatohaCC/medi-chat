"use client";

import { Button } from "@react-spectrum/s2/Button";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { logout } from "../api/authentication";

export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      {error && <span role="alert">{error}</span>}
      <Button
        variant="secondary"
        isPending={pending}
        onPress={async () => {
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
