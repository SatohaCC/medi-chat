import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { ensurePortAvailable } from "../scripts/owned-server.mjs";

import { cleanupFixture } from "./helpers/postgres-fixture";

const root = resolve("..");

test("WR-034 WR-050 real route heartbeat during preparation and silence, stop and queue", async ({
  page,
  request,
}) => {
  const isolated = mkdtempSync(join(tmpdir(), "medi-chat-reliability-browser-"));
  const metricsFile = join(isolated, "sdk-metrics.json");
  const python =
    process.platform === "win32"
      ? join(root, "backend/.venv/Scripts/python.exe")
      : join(root, "backend/.venv/bin/python");
  const environment = {
    ...process.env,
    PYTHON_DOTENV_DISABLED: "1",
    OPENAI_API_KEY: "",
    GEMINI_API_KEY: "",
    GOOGLE_API_KEY: "",
    ANTHROPIC_API_KEY: "",
    JEV_API_KEY: "",
    TYPESAFE_API_KEY: "",
    ALLOWED_ORIGINS: "http://127.0.0.1:3110",
  };
  const prepared = spawnSync(
    python,
    ["-m", "backend.tests.support.registration_browser_fixture", "--root", isolated],
    { cwd: root, env: environment, encoding: "utf8", timeout: 120000 },
  );
  expect(prepared.status, prepared.stdout + prepared.stderr).toBe(0);
  await ensurePortAvailable(3211);
  const owned = spawn(
    python,
    [
      "-m",
      "backend.tests.support.registration_browser_server",
      "--root",
      isolated,
      "--port",
      "3211",
      "--ws-lifetime",
      "--metrics-file",
      metricsFile,
    ],
    { cwd: root, env: environment },
  );

  const frames: Record<string, unknown>[] = [];
  const sent: Record<string, unknown>[] = [];
  page.on("websocket", (socket) => {
    if (socket.url() !== "ws://127.0.0.1:3211/api/ws") return;
    socket.on("framereceived", (event) => {
      frames.push(JSON.parse(String(event.payload)));
    });
    socket.on("framesent", (event) => {
      sent.push(JSON.parse(String(event.payload)));
    });
  });
  const metrics = () => JSON.parse(readFileSync(metricsFile, "utf8"));
  try {
    await expect
      .poll(
        async () => {
          try {
            return (await request.get("http://127.0.0.1:3211/health")).status();
          } catch {
            return 0;
          }
        },
        { timeout: 30000 },
      )
      .toBe(200);
    await page.addInitScript(() => {
      const Native = window.WebSocket;
      const sockets: WebSocket[] = [];
      Object.assign(window, { reliabilitySockets: sockets });
      window.WebSocket = class extends Native {
        constructor(url: string | URL, protocols?: string | string[]) {
          super(url, protocols);
          sockets.push(this);
        }
      };
    });
    await page.goto("/");
    await expect(page.getByText("connected", { exact: true })).toBeVisible();
    await page.clock.install();
    await page.clock.pauseAt(new Date(Date.now() + 1000));
    const input = page.getByRole("textbox", { name: "質問を入力" });
    const send = page.getByRole("button", { name: "送信", exact: true });
    for (const [marker, started, closed] of [
      ["[テスト準備待機]", "preparation_started", "preparation_closed"],
      ["[テスト無音]", "silent_started", "silent_closed"],
    ]) {
      await input.fill(`イグザレルトの注意 ${marker}`);
      await send.click();
      await expect.poll(() => metrics()[started]).toBe(1);
      const id = String(sent.findLast((frame) => frame.type === "message")?.request_id);
      const before = frames.filter((frame) => frame.type === "pong").length;
      await page.clock.fastForward(30000);
      await expect
        .poll(() => frames.filter((frame) => frame.type === "pong").length)
        .toBeGreaterThan(before);
      expect(metrics()[closed] ?? 0).toBe(0);
      await page.getByRole("button", { name: "回答を停止", exact: true }).click();
      await expect.poll(() => metrics()[closed]).toBe(1);
      await expect
        .poll(
          () =>
            frames.filter((frame) => frame.request_id === id && frame.type === "aborted")
              .length,
        )
        .toBe(1);
      expect(
        frames.filter(
          (frame) =>
            frame.request_id === id &&
            ["text_done", "error", "aborted"].includes(String(frame.type)),
        ),
      ).toHaveLength(1);
    }
    const count = sent.filter((frame) => frame.type === "message").length;
    await page.evaluate(() => {
      const state = window as unknown as { reliabilitySockets: WebSocket[] };
      state.reliabilitySockets.at(-1)?.close();
    });
    await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
    await input.fill("イグザレルトのテスト保留質問");
    await send.click();
    await expect(page.getByRole("region", { name: "未送信の保留" })).toBeVisible();
    expect(sent.filter((frame) => frame.type === "message")).toHaveLength(count);
    await page.clock.fastForward(6000);
    await expect
      .poll(() => sent.filter((frame) => frame.type === "message").length)
      .toBe(count + 1);
    await expect
      .poll(() => frames.filter((frame) => frame.type === "text_done").length)
      .toBe(1);
    const last = sent.findLast((frame) => frame.type === "message");
    expect(last?.messages).toEqual([
      { role: "user", content: "イグザレルトのテスト保留質問" },
    ]);
    await page.evaluate(() => {
      const state = window as unknown as { reliabilitySockets: WebSocket[] };
      state.reliabilitySockets.at(-1)?.close();
    });
    await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
    await input.fill("取消するテスト質問");
    await send.click();
    await page.getByRole("button", { name: "保留を取消", exact: true }).click();
    await page.getByRole("button", { name: "再編集", exact: true }).click();
    await expect(input).toContainText("取消するテスト質問");
    await page.clock.fastForward(6000);
    expect(sent.filter((frame) => frame.type === "message")).toHaveLength(count + 1);
  } finally {
    if (owned.exitCode === null && owned.signalCode === null) {
      const stopped = new Promise<void>((done) => owned.once("exit", () => done()));
      owned.kill();
      await stopped;
    }
    cleanupFixture(root, isolated);
  }
});
