"use client";

import * as stylex from "@stylexjs/stylex";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import { Form } from "../../../../shared/component/Form";
import { TextInput as TextField } from "../../../../shared/component/TextInput";
import { login, safeReturnTo } from "../../api";
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
          onSubmit={async (data) => {
            if (pending) return;
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
            required
            maxLength={128}
          />
          <TextField
            label="パスワード"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            minLength={15}
            maxLength={128}
          />
          {error && <p role="alert">{error}</p>}
          <Button type="submit" appearance="primary" pending={pending}>
            ログイン
          </Button>
        </Form>
        <p>ログインできない場合は管理者にお問い合わせください。</p>
      </section>
    </main>
  );
}
