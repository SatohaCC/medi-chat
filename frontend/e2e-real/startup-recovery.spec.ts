import { type ChildProcess, spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { expect, test } from "@playwright/test";
import {
  ensureOwnedRestartPortAvailable,
  ensurePortAvailable,
} from "../scripts/owned-server.mjs";

const root = resolve("..");
const evidence = resolve(
  process.env.MEDI_CHAT_E2E_EVIDENCE ||
    "../for-llm/progress/20261010-browser-xml-import-evidence/unit-12",
);
const digest = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");
const xml = (
  text: string,
  products: { code: string; name: string }[],
  revision = "2026-10",
) =>
  Buffer.from(
    `<?xml version="1.0"?><PackIns drugType="Medicine"><CompanyIdentifier>000001</CompanyIdentifier><PackageInsertNo>browser</PackageInsertNo><DateOfPreparationOrRevision><PreparationOrRevision id="今回"><YearMonth>${revision}</YearMonth><Version>1</Version></PreparationOrRevision></DateOfPreparationOrRevision><ApprovalEtc>${products.map((p, i) => `<DetailBrandName id="${i === 0 ? "A" : "B"}"><ApprovalBrandName><Lang>${p.name}</Lang></ApprovalBrandName><BrandCode><YJCode>${p.code}</YJCode></BrandCode></DetailBrandName>`).join("")}</ApprovalEtc><Warnings><Detail><Lang>${text}</Lang></Detail></Warnings></PackIns>`,
  );

test("TC117 real legacy migration O→N(A)→P(B), search cleanup replay restart", async ({
  page,
  request,
}, testInfo) => {
  const isolated = mkdtempSync(join(tmpdir(), "medi-chat-registration-browser-"));
  const oldIndex = join(root, "data_tools/structured/.chat-search.sqlite3");
  const original = digest(readFileSync(oldIndex));
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
    MEDI_CHAT_STRUCTURED_DIR: join(isolated, "structured"),
    MEDI_CHAT_INDEX_PATH: join(isolated, "index.sqlite3"),
    MEDI_CHAT_DATABASE_URL: `sqlite:///${join(isolated, "index.sqlite3").replaceAll("\\", "/")}`,
    MEDI_CHAT_IMPORT_DIR: join(isolated, "imports"),
  };
  const python = join(root, "backend/.venv/Scripts/python.exe");
  const command = (args: string[]) =>
    spawnSync(python, args, {
      cwd: root,
      env: environment,
      encoding: "utf8",
      timeout: 120000,
    });
  const copy = command([
    "-m",
    "backend.tests.registration_browser_fixture",
    "--root",
    isolated,
    "--old-index",
    oldIndex,
  ]);
  expect(copy.status, copy.stderr).toBe(0);
  const ledger = JSON.parse(readFileSync(join(isolated, "copy-ledger.json"), "utf8"));
  expect(ledger.snapshot.fingerprint).toMatch(/^manifest:/);
  const before = digest(readFileSync(environment.MEDI_CHAT_INDEX_PATH));
  const rejected = command(["-m", "backend.infrastructure.cli.configured_e2e_gate"]);
  expect(rejected.status).not.toBe(0);
  expect(digest(readFileSync(environment.MEDI_CHAT_INDEX_PATH))).toBe(before);
  const initialized = command([
    "-m",
    "backend.tests.registration_browser_fixture",
    "--root",
    isolated,
    "--initialize",
  ]);
  expect(initialized.status, initialized.stderr).toBe(0);
  expect(initialized.stdout).toContain('"units": 267');
  expect(initialized.stdout).toContain('"medicines": 15');
  let owned: ChildProcess | undefined;
  let logs = copy.stdout + rejected.stdout + initialized.stdout;
  async function start() {
    if (owned) await ensureOwnedRestartPortAvailable(3211);
    else await ensurePortAvailable(3211);
    owned = spawn(
      python,
      [
        "-m",
        "backend.tests.registration_browser_server",
        "--root",
        isolated,
        "--port",
        "3211",
      ],
      { cwd: root, env: environment },
    );
    owned.stdout?.on("data", (chunk) => (logs += String(chunk)));
    owned.stderr?.on("data", (chunk) => (logs += String(chunk)));
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
  }
  async function stop() {
    if (!owned || owned.exitCode !== null || owned.signalCode !== null) return;
    const exited = new Promise<void>((done) => owned?.once("exit", () => done()));
    owned.kill();
    await exited;
  }
  async function upload(bytes: Buffer) {
    await page.goto("/imports");
    await page
      .getByLabel("XMLファイル")
      .setInputFiles({ name: "source.xml", mimeType: "application/xml", buffer: bytes });
    const pending = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/attachment-imports") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "取り込む", exact: true }).click();
    const response = await pending;
    expect(response.status()).toBe(201);
    const result = await response.json();
    expect(result.source_sha256).toBe(digest(bytes));
    expect(result.search_index_updated).toBe(true);
    await expect(page.getByText("登録済み／検索に反映済み", { exact: true })).toBeVisible(
      { timeout: 30000 },
    );
    return { result, location: response.headers().location };
  }
  async function search(code: string, sha: string, body: string) {
    const response = await request.post("http://127.0.0.1:3211/api/chat", {
      data: {
        message: "警告",
        product_yj_codes: [code],
        provider: "openai",
        model: "gpt-6-luna",
      },
    });
    expect(response.status()).toBe(200);
    const answer = await response.json();
    expect(answer.sources).toHaveLength(1);
    expect(answer.sources[0].unit_id).toBe(`000001_browser:${sha}:1`);
    expect(answer.sources[0].excerpt).toContain(body);
    return answer;
  }
  try {
    await start();
    expect(
      (await (await request.get("http://127.0.0.1:3211/health")).json()).unit_count,
    ).toBe(267);
    const a = "111111111111",
      b = "222222222222";
    const old = xml("O共通警告", [
      { code: a, name: "旧A" },
      { code: b, name: "旧B" },
    ]);
    const o = await upload(old);
    const oldPath = join(
      isolated,
      "imports/versions",
      digest(Buffer.from("000001_browser")),
      digest(old),
      "source.xml",
    );
    expect(readFileSync(oldPath)).toEqual(old);
    const oldAnswer = await search(b, digest(old), "O共通警告");
    const n = await upload(xml("N A警告", [{ code: a, name: "新A" }], "2025-01"));
    await page.goto("/");
    await expect(page.getByRole("button", { name: "新A", exact: true })).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByRole("button", { name: "旧B", exact: true })).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByRole("button", { name: "旧A", exact: true })).not.toBeVisible({
      timeout: 30000,
    });
    expect((await request.get(`http://127.0.0.1:3211${o.location}`)).status()).toBe(200);
    expect(existsSync(oldPath)).toBe(true);
    await search(a, n.result.source_sha256, "N A警告");
    await search(b, digest(old), "O共通警告");
    const p = await upload(xml("P B警告", [{ code: b, name: "新B" }]));
    await page.goto("/");
    await expect(page.getByRole("button", { name: "新B", exact: true })).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByRole("button", { name: "旧B", exact: true })).not.toBeVisible({
      timeout: 30000,
    });
    expect((await request.get(`http://127.0.0.1:3211${o.location}`)).status()).toBe(410);
    expect(existsSync(oldPath)).toBe(false);
    await search(b, p.result.source_sha256, "P B警告");
    const repeat = await request.post("http://127.0.0.1:3211/api/attachment-imports", {
      multipart: { file: { name: "old.xml", mimeType: "application/xml", buffer: old } },
    });
    expect(repeat.status()).toBe(200);
    const replay = await repeat.json();
    expect(replay.status).toBe("superseded");
    expect(replay.artifacts_deleted).toBe(true);
    expect(replay.registration_sequence).toBe(o.result.registration_sequence);
    expect(existsSync(oldPath)).toBe(false);
    const health = await (await request.get("http://127.0.0.1:3211/health")).json();
    const groups = await (
      await request.get("http://127.0.0.1:3211/api/medicines")
    ).json();
    const compact = await (
      await request.get("http://127.0.0.1:3211/api/medicines/autocomplete")
    ).json();
    expect(groups.generation_id).toBe(p.result.generation_id);
    expect(compact.generation_id).toBe(health.generation_id);
    expect(
      compact.items
        .filter((x: { y: string }) => [a, b].includes(x.y))
        .map((x: { n: string }) => x.n)
        .sort(),
    ).toEqual(["新A", "新B"]);
    await stop();
    await start();
    expect(await (await request.get("http://127.0.0.1:3211/health")).json()).toEqual(
      health,
    );
    expect((await request.get(`http://127.0.0.1:3211${o.location}`)).status()).toBe(410);
    expect((await request.get(`http://127.0.0.1:3211${n.location}`)).status()).toBe(200);
    await search(a, n.result.source_sha256, "N A警告");
    expect(oldAnswer.sources[0].excerpt).toContain("O共通警告");
    expect(existsSync(oldPath)).toBe(false);
    expect(digest(readFileSync(oldIndex))).toBe(original);
    await page.screenshot({
      path: join(evidence, "registration-browser.png"),
      fullPage: true,
    });
    writeFileSync(
      join(evidence, "registration-browser-state.json"),
      JSON.stringify(
        {
          isolated,
          ledger,
          rejected: rejected.stdout,
          initialized: initialized.stdout,
          old_index_sha256: original,
          o,
          n,
          p,
          health,
          sdk: "fixed detector/provider; no API interception",
        },
        null,
        2,
      ),
    );
  } finally {
    await stop();
    writeFileSync(join(evidence, "registration-browser-backend.log"), logs);
    await testInfo.attach("backend log", { body: logs, contentType: "text/plain" });
  }
});
