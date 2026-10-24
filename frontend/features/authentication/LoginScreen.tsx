"use client";

import { Button } from "@react-spectrum/s2/Button";
import { Form } from "@react-spectrum/s2/Form";
import { TextField } from "@react-spectrum/s2/TextField";
import * as stylex from "@stylexjs/stylex";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login, safeReturnTo } from "../../shared/api/authentication";
import { styles } from "./LoginScreen.styles";

export function LoginScreen() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  return (
    <main {...stylex.props(styles.main)}>
      <section {...stylex.props(styles.section)} aria-labelledby="login-title">
        <div>
          <h1 id="login-title">medi-chat にログイン</h1>
          <p>発行されたログインIDとパスワードを入力してください。</p>
        </div>
        <Form
          onSubmit={async (event) => {
            event.preventDefault();
            if (pending) return;
            const data = new FormData(event.currentTarget);
            setPending(true);
            setError("");
            try {
              await login(
                String(data.get("login_id") || ""),
                String(data.get("password") || ""),
              );
              router.replace(
                safeReturnTo(new URLSearchParams(window.location.search).get("returnTo")),
              );
            } catch (error) {
              setError(
                error instanceof Error ? error.message : "ログインできませんでした。",
              );
            } finally {
              setPending(false);
            }
          }}
        >
          <TextField
            label="ログインID"
            name="login_id"
            autoComplete="username"
            isRequired
            maxLength={128}
          />
          <TextField
            label="パスワード"
            name="password"
            type="password"
            autoComplete="current-password"
            isRequired
            minLength={15}
            maxLength={128}
          />
          {error && <p role="alert">{error}</p>}
          <Button type="submit" variant="primary" isPending={pending}>
            ログイン
          </Button>
        </Form>
        <p>ログインできない場合は管理者にお問い合わせください。</p>
      </section>
    </main>
  );
}
