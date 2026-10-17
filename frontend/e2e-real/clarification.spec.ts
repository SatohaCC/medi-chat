import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { ensurePortAvailable } from "../scripts/owned-server.mjs";
import { restoreHistoricalManifest } from "./helpers/sqlite-fixture";

const root = resolve("..");
const evidence = resolve(
  process.env.MEDI_CHAT_E2E_EVIDENCE ||
    "../for-llm/progress/20261010-browser-xml-import-evidence/unit-16",
);

test("TC137 real browser three confirmations and normal single/pair without API interception", async ({
  page,
  request,
}) => {
  const isolated = mkdtempSync(join(tmpdir(), "medi-chat-confirmation-browser-"));
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
  const oldIndex = restoreHistoricalManifest(root, isolated, environment);
  for (const args of [
    ["--root", isolated, "--old-index", oldIndex],
    ["--root", isolated, "--initialize"],
  ]) {
    const result = spawnSync(
      python,
      ["-m", "backend.tests.support.registration_browser_fixture", ...args],
      { cwd: root, env: environment, encoding: "utf8", timeout: 120000 },
    );
    expect(result.status, result.stdout + result.stderr).toBe(0);
  }
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
      "--metrics-file",
      metricsFile,
    ],
    { cwd: root, env: environment },
  );
  let logs = "";
  owned.stdout.on("data", (chunk) => {
    logs += String(chunk);
  });
  owned.stderr.on("data", (chunk) => {
    logs += String(chunk);
  });
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
  const questions: string[] = [];
  const metrics = () => JSON.parse(readFileSync(metricsFile, "utf8"));
  async function ask(question: string) {
    questions.push(question);
    const start = frames.length;
    await page.getByPlaceholder("確認したい内容を入力", { exact: false }).fill(question);
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect
      .poll(
        () => frames.slice(start).filter((frame) => frame.type === "text_done").length,
      )
      .toBe(1);
    return frames.slice(start);
  }
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
    await page.goto("/");
    await expect(page.getByText("connected", { exact: true })).toBeVisible({
      timeout: 30000,
    });
    const cases = [
      [
        "アマリールの効能は？",
        "質問の医薬品名と選択されたYJコードが一致していません。対象製品を確認し、YJコードを選択し直してください。",
      ],
      [
        "イグザレルトとイトラコナゾールの飲み合わせ",
        "飲み合わせを確認する両方の医薬品のYJコードを選択してください。",
      ],
    ];
    for (const [question, answer] of cases) {
      const events = await ask(question);
      expect(events).toEqual([
        { type: "retrieval_status", stage: "unavailable" },
        { type: "text_delta", content: answer },
        { type: "text_done" },
      ]);
      await expect(page.getByText(answer, { exact: true })).toBeVisible();
      expect(sent.at(-1)?.product_yj_codes).toEqual(["3339003F5020"]);
      expect(metrics()).toEqual({ factory_calls: 0, stream_calls: 0, questions });
    }
    const single = await ask("イグザレルトの飲み合わせ");
    const singleSources = single.find((frame) => frame.type === "sources")?.sources;
    expect(Array.isArray(singleSources)).toBe(true);
    expect(singleSources).toHaveLength(4);
    await page.getByRole("button", { name: /^イトリゾールカプセル/ }).click();
    await page.getByRole("button", { name: /^イトラコナゾールカプセル/ }).click();
    const pair = await ask("イグザレルトとイトラコナゾールの飲み合わせ");
    expect(pair.find((frame) => frame.type === "sources")?.sources).toHaveLength(10);
    const sourceFile = join(isolated, "normal-sources.json");
    writeFileSync(
      sourceFile,
      JSON.stringify({
        single: singleSources,
        pair: pair.find((frame) => frame.type === "sources")?.sources,
      }),
    );
    const oracle = spawnSync(
      python,
      [
        "-c",
        "import json,sys; from backend.tests.integration.test_interaction_xml_oracle import ORACLE,assert_public_source; observed=json.load(open(sys.argv[1],encoding='utf8')); expected=sorted([(d,c) for d in ORACLE for c in d['sections']],key=lambda x:(tuple(map(int,x[1].split('.'))),x[0]['sections'][x[1]]['unit_id'])); assert [s['unit_id'] for s in observed['single']]==[d['sections'][c]['unit_id'] for d,c in expected if d==ORACLE[0]]; assert [s['unit_id'] for s in observed['pair']]==[d['sections'][c]['unit_id'] for d,c in expected]; [assert_public_source(s,d,c) for s,(d,c) in zip(observed['pair'],expected,strict=True)]; [assert_public_source(s,ORACLE[0],c) for s,c in zip(observed['single'],ORACLE[0]['sections'],strict=True)]; print('original XML fixed oracle: all single/pair IDs, full body, tables, references and metadata match')",
        sourceFile,
      ],
      { cwd: root, env: environment, encoding: "utf8" },
    );
    expect(oracle.status, oracle.stdout + oracle.stderr).toBe(0);
    expect(metrics()).toEqual({ factory_calls: 2, stream_calls: 2, questions });
    await expect(page.getByText("固定SDK回答（通信なし）", { exact: true })).toHaveCount(
      2,
    );
    const toggleButtons = page.getByRole("button", { name: /添付文書の根拠を表示/ });
    await expect(toggleButtons).toHaveCount(2);
    await toggleButtons.last().click();
    const panels = page.getByRole("complementary", { name: "添付文書の根拠引用" });
    await expect(panels).toHaveCount(1);
    const cards = panels.last().locator("[data-evidence-card]");
    await expect(cards).toHaveCount(10);
    const originalOracle: { sections: Record<string, { unit_id: string }> }[] =
      JSON.parse(
        readFileSync(
          join(root, "backend/tests/fixtures/interaction_oracle_v6.json"),
          "utf8",
        ),
      );
    expect(
      (await cards.allTextContents())
        .map((text) => text.match(/単位ID: (.+)$/)?.[1])
        .sort(),
    ).toEqual(
      originalOracle
        .flatMap((document) =>
          Object.values(document.sections).map((section) => section.unit_id),
        )
        .sort(),
    );
    await page.screenshot({
      path: join(evidence, "clarification-browser.png"),
      fullPage: true,
    });
    writeFileSync(
      join(evidence, "clarification-observation.json"),
      JSON.stringify(
        {
          isolated,
          frames,
          sent,
          metrics: metrics(),
          external_sdk_double: true,
          api_interception: false,
        },
        null,
        2,
      ),
    );
  } finally {
    writeFileSync(join(evidence, "clarification-backend.log"), logs);
    if (owned.exitCode === null && owned.signalCode === null) {
      const stopped = new Promise<void>((done) => owned.once("exit", () => done()));
      owned.kill();
      await stopped;
    }
  }
});
