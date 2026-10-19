import { type ChildProcess, spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { request as httpRequest } from "node:http";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { expect, test } from "@playwright/test";
import {
  ensureOwnedRestartPortAvailable,
  ensurePortAvailable,
} from "../scripts/owned-server.mjs";
import {
  assertCurrentImport,
  cleanupFixture,
  logicalSnapshot,
  pythonBinary,
} from "./helpers/postgres-fixture";

const root = resolve("..");
const evidence = resolve(
  process.env.MEDI_CHAT_E2E_EVIDENCE ||
    "../for-llm/progress/20261010-browser-xml-import-evidence/unit-12",
);
const isolated = mkdtempSync(join(tmpdir(), "medi-chat-import-e2e-"));
const hash = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");

test("real browser upload, resend, process restart GET and active registration", async ({
  page,
  request,
}, testInfo) => {
  let process: ChildProcess | undefined;
  let logs = "";
  async function start() {
    if (process) await ensureOwnedRestartPortAvailable(3211);
    else await ensurePortAvailable(3211);
    process = spawn(
      pythonBinary(root),
      [
        "-m",
        "backend.tests.support.attachment_import_e2e_server",
        "--root",
        isolated,
        "--port",
        "3211",
      ],
      {
        cwd: root,
        env: {
          ...globalThis.process.env,
          PYTHON_DOTENV_DISABLED: "1",
          OPENAI_API_KEY: "",
          GEMINI_API_KEY: "",
          GOOGLE_API_KEY: "",
          JEV_API_KEY: "",
          TYPESAFE_API_KEY: "",
          ANTHROPIC_API_KEY: "",
          ALLOWED_ORIGINS: "http://127.0.0.1:3110",
        },
      },
    );
    process.stdout?.on("data", (chunk) => {
      logs += String(chunk);
    });
    process.stderr?.on("data", (chunk) => {
      logs += String(chunk);
    });
    await expect
      .poll(
        async () => {
          try {
            return (await request.get("http://127.0.0.1:3211/health")).status();
          } catch {
            return 0;
          }
        },
        { timeout: 30_000 },
      )
      .toBe(200);
  }
  async function stop() {
    if (!process || process.exitCode !== null || process.signalCode !== null) return;
    const exited = new Promise<void>((resolve) => process?.once("exit", () => resolve()));
    process.kill();
    await exited;
  }
  try {
    await start();
    const streamed = await new Promise<{ status: number; body: string }>(
      (resolve, reject) => {
        const request = httpRequest(
          "http://127.0.0.1:3211/api/attachment-imports",
          { method: "POST", headers: { "content-type": "application/octet-stream" } },
          (response) => {
            let body = "";
            response.on("data", (chunk) => {
              body += String(chunk);
            });
            response.on("end", () => resolve({ status: response.statusCode || 0, body }));
          },
        );
        request.on("error", reject);
        for (let remaining = 11 * 1024 * 1024 + 1; remaining > 0; remaining -= 65536)
          request.write(Buffer.alloc(Math.min(remaining, 65536), 120));
        request.end();
      },
    );
    expect(streamed.status).toBe(413);
    expect(JSON.parse(streamed.body)).toEqual({
      detail: {
        code: "request_too_large",
        message: "受信データが上限を超えています。",
        phase: "validation",
      },
    });
    const index = isolated;
    const initial = logicalSnapshot(root, index);
    expect(initial.integrity).toBe("ok");
    const medicinesBefore = await (
      await request.get("http://127.0.0.1:3211/api/medicines")
    ).json();
    const source = readFileSync(
      join(
        root,
        "data/pmda/originals/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml",
      ),
    );

    await page.goto("/imports");
    await page.getByLabel("XMLファイル").setInputFiles({
      name: "630004_3339003F5020_1_08.xml",
      mimeType: "application/xml",
      buffer: source,
    });
    const uploaded = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/attachment-imports") &&
        response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "取り込む", exact: true }).click();
    const response = await uploaded;
    expect(response.status(), await response.text()).toBe(201);
    const result = await response.json();
    expect(result.source_sha256).toBe(hash(source));
    expect(result.search_index_updated).toBe(true);
    expect(result.warnings).toContainEqual({
      code: "missing_figure",
      reference: "630004_3339003F5020_1_08_fig01.gif",
    });
    await expect(
      page.getByText("登録済み／検索に反映済み", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("630004_3339003F5020_1_08_fig01.gif", { exact: false }),
    ).toBeVisible();
    await page.screenshot({
      path: join(evidence, "real-import-result.png"),
      fullPage: true,
    });
    const location = response.headers().location;
    const registered = logicalSnapshot(root, index);
    expect(registered.integrity).toBe("ok");
    expect(registered).not.toEqual(initial);
    const registeredData = JSON.stringify(registered.tables);
    expect(registeredData).toContain(result.document_id);
    expect(registeredData).toContain(result.source_sha256);
    expect(registeredData).toContain("3339003F5020");
    expect(registeredData).toContain(result.generation_id);
    const receipts = registered.tables.registration_receipts;
    const receipt = receipts.rows.find(
      (row) => row[receipts.columns.indexOf("document_id")] === result.document_id,
    );
    expect(receipt?.[receipts.columns.indexOf("source_sha256")]).toBe(
      result.source_sha256,
    );
    expect(receipt?.[receipts.columns.indexOf("sequence")]).toBe(
      result.registration_sequence,
    );
    const candidates = await (
      await request.get("http://127.0.0.1:3211/api/medicines")
    ).json();
    expect(candidates.generation_id).toBe(result.generation_id);
    expect(candidates.generation_id).not.toBe(medicinesBefore.generation_id);
    const databaseDiagnosis = JSON.stringify({ initial, registered });
    writeFileSync(join(evidence, "database-diagnosis.json"), databaseDiagnosis);
    await testInfo.attach("database-diagnosis", {
      body: databaseDiagnosis,
      contentType: "application/json",
    });
    const repeated = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/attachment-imports") &&
        response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "取り込む", exact: true }).click();
    const repeat = await repeated;
    expect(repeat.status()).toBe(200);
    expect(repeat.headers().location).toBe(location);
    const repeatResult = await repeat.json();
    expect(repeatResult.registration_sequence).toBe(result.registration_sequence);
    expect(repeatResult.generation_id).toBe(result.generation_id);
    expect(repeatResult.reused).toBe(true);
    expect(logicalSnapshot(root, index)).toEqual(registered);
    const versionId = `${result.document_id}:${result.source_sha256}`;
    expect(assertCurrentImport(root, isolated, versionId)).toEqual({
      sections: 22,
      source_tree: "passed",
      stored_index: "passed",
    });
    await stop();
    await start();
    const saved = await request.get(`http://127.0.0.1:3211${location}`);
    expect(saved.status()).toBe(200);
    expect(await saved.json()).toEqual(result);
    expect(logicalSnapshot(root, index)).toEqual(registered);
    const medicinesAfter = await (
      await request.get("http://127.0.0.1:3211/api/medicines")
    ).json();
    expect(medicinesAfter.generation_id).toBe(result.generation_id);
    expect(medicinesAfter.generation_id).not.toBe(medicinesBefore.generation_id);
    expect(
      medicinesAfter.items.flatMap((item: { yj_codes: string[] }) => item.yj_codes),
    ).toContain("3339003F5020");
    const xmlVersion = (month: string, products: string[], body: string) =>
      Buffer.from(`<PackIns drugType="Medicine"><CompanyIdentifier>test</CompanyIdentifier><PackageInsertNo>browser</PackageInsertNo><DateOfPreparationOrRevision><PreparationOrRevision id="今回"><YearMonth>${month}</YearMonth><Version>1</Version></PreparationOrRevision></DateOfPreparationOrRevision><ApprovalEtc>${products.map((code, index) => `<DetailBrandName id="${index}"><ApprovalBrandName><Lang>テスト製品${code === "777777777777" ? "A" : "B"}</Lang></ApprovalBrandName><BrandCode><YJCode>${code}</YJCode></BrandCode></DetailBrandName>`).join("")}</ApprovalEtc><Warnings><Detail><Lang>${body}</Lang></Detail></Warnings></PackIns>`);
    const uploadVersion = async (buffer: Buffer) => {
      await page.getByLabel("XMLファイル").setInputFiles({ name: "テスト改訂.xml", mimeType: "application/xml", buffer });
      const pending = page.waitForResponse((response) => response.url().endsWith("/api/attachment-imports") && response.request().method() === "POST");
      await page.getByRole("button", { name: "取り込む", exact: true }).click();
      const response = await pending;
      expect([200, 201]).toContain(response.status());
      return { result: await response.json(), location: response.headers().location, status: response.status() };
    };
    const a = "777777777777", b = "888888888888";
    const oldBytes = xmlVersion("2026-10", [a, b], "テスト旧ブラウザ警告");
    const old = await uploadVersion(oldBytes);
    expect(old.status).toBe(201);
    const newerA = await uploadVersion(xmlVersion("2026-11", [a], "テスト新版A警告"));
    expect(newerA.result.replaced_yj_codes).toEqual([a]);
    const retained = await request.get(`http://127.0.0.1:3211${old.location}`);
    expect(retained.status()).toBe(200);
    expect((await retained.json()).active_yj_codes).toEqual([b]);
    const oldB = await (await request.get(`http://127.0.0.1:3211/api/search?q=テスト旧ブラウザ&yj_codes=${b}`)).json();
    expect(oldB.total_count).toBe(1);
    expect(oldB.items[0].product_yj_codes).toEqual([b]);
    const newerB = await uploadVersion(xmlVersion("2026-12", [b], "テスト新版B警告"));
    expect(newerB.result.deleted_version_ids).toContain(`${old.result.document_id}:${old.result.source_sha256}`);
    expect((await request.get(`http://127.0.0.1:3211${old.location}`)).status()).toBe(410);
    const replay = await uploadVersion(oldBytes);
    expect(replay.status).toBe(200);
    expect(replay.result.reused).toBe(true);
    expect(replay.result.artifacts_deleted).toBe(true);
    expect(replay.result.active_yj_codes).toEqual([]);
    expect(replay.result.generation_id).toBe(newerB.result.generation_id);
    await expect(page.getByText("この旧版の所有ファイルは削除済みです。同原本の再送でも復活しません。")).toBeVisible();
    await page.screenshot({ path: join(evidence, "real-version-nonrevival.png"), fullPage: true });
    await stop();
    await start();
    expect((await request.get(`http://127.0.0.1:3211${old.location}`)).status()).toBe(410);
    expect((await request.get(`http://127.0.0.1:3211${newerA.location}`)).status()).toBe(200);
    const currentB = await (await request.get(`http://127.0.0.1:3211/api/search?q=テスト新版B&yj_codes=${b}`)).json();
    expect(currentB.total_count).toBe(1);
    expect(currentB.items[0].unit_id).toContain(newerB.result.source_sha256);
    writeFileSync(join(evidence, "real-version-sequence.json"), JSON.stringify({ old, newerA, newerB, replay, retained: await retained.json(), oldB, currentB }, null, 2));
    await testInfo.attach("real-state", {
      body: JSON.stringify({
        isolated,
        result,
        location,
        initial_logical_sha256: initial.logical_sha256,
      }),
      contentType: "application/json",
    });
    writeFileSync(
      join(evidence, "real-state.json"),
      JSON.stringify(
        { isolated, result, location, initial_logical_sha256: initial.logical_sha256 },
        null,
        2,
      ),
    );
  } finally {
    await stop();
    cleanupFixture(root, isolated);
    await testInfo.attach("backend-log", { body: logs, contentType: "text/plain" });
    writeFileSync(join(evidence, "real-backend.log"), logs);
  }
});
