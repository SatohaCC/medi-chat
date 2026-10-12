import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { openChat } from "../e2e/helpers/chat";

interface NativeRecord {
  [key: string]: unknown;
}
declare global {
  interface Window {
    __mediImeEvents?: NativeRecord[];
    __mediImeDone?: boolean;
    __mediImePending?: Promise<unknown>[];
    __mediImeWsSnapshot?: () => Promise<{
      count: number;
      payloads: unknown[];
      observedAt: number;
    }>;
  }
}
const smoke = process.env.MEDI_CHAT_IME_SMOKE === "1";
for (const candidates of [false, true])
  for (const operation of ["Enter", "Tab", "Escape"]) {
    test(`native IME recorder: candidates=${candidates}, ${operation}`, async ({
      page,
      browserName,
    }, testInfo) => {
      await page.addInitScript(() =>
        document.addEventListener(
          "DOMContentLoaded",
          () => {
            const style = document.createElement("style");
            style.textContent = "nextjs-portal {display:none!important}";
            document.head.append(style);
          },
          { once: true },
        ),
      );
      const chat = await openChat(page, { candidates });
      await page.exposeFunction("__mediImeWsSnapshot", () => ({
        count: chat.requests.length,
        payloads: [...chat.requests],
        observedAt: Date.now(),
      }));
      await page.evaluate(
        ({ operation, candidates }) => {
          window.__mediImeEvents = [];
          window.__mediImePending = [];
          window.__mediImeDone = false;
          const snapshot = () => {
            const input = document.querySelector<HTMLInputElement>(
              'input[placeholder^="確認したい内容"]',
            );
            const active = document.activeElement;
            return {
              value: input?.value ?? null,
              selectionStart: input?.selectionStart ?? null,
              selectionEnd: input?.selectionEnd ?? null,
              focus: active
                ? {
                    tag: active.tagName,
                    id: active.id,
                    role: active.getAttribute("role"),
                    label: active.getAttribute("aria-label"),
                    text:
                      active === input ? "chat-input" : active.textContent?.slice(0, 80),
                  }
                : null,
              popupOpen: Boolean(document.querySelector('[role="listbox"]')),
              selectedCandidate:
                document.querySelector('[role="listbox"] [aria-selected="true"]')
                  ?.textContent ?? null,
              selectedYjText:
                Array.from(document.querySelectorAll("div")).find(
                  (node) =>
                    node.textContent?.startsWith("選択中:") && node.children.length === 0,
                )?.textContent ?? null,
            };
          };
          const append = (record: NativeRecord) => {
            window.__mediImeEvents?.push(record);
            const pending = window.__mediImeWsSnapshot?.().then((ws) =>
              Object.assign(record, {
                wsCount: ws.count,
                wsPayloads: ws.payloads,
                wsObservedAt: ws.observedAt,
                wsObservationPhase: "async-node-bridge",
              }),
            );
            if (pending) window.__mediImePending?.push(pending);
          };
          for (const type of [
            "compositionstart",
            "compositionupdate",
            "compositionend",
            "keydown",
            "keyup",
            "input",
            "focusin",
            "focusout",
          ]) {
            document.addEventListener(
              type,
              (event) => {
                const e = event;
                const keyboard = e instanceof KeyboardEvent ? e : null;
                const composition = e instanceof CompositionEvent ? e : null;
                const record = {
                  timestamp: performance.now(),
                  type: e.type,
                  key: keyboard?.key ?? null,
                  keyCode: keyboard?.keyCode ?? null,
                  isComposing: keyboard?.isComposing ?? null,
                  data: composition?.data ?? null,
                };
                append({
                  ...record,
                  phase: "capture",
                  ...snapshot(),
                });
                queueMicrotask(() =>
                  append({
                    ...record,
                    phase: "after-handlers",
                    ...snapshot(),
                  }),
                );
              },
              true,
            );
          }
          const panel = document.createElement("aside");
          panel.id = "ime-recorder-instructions";
          panel.style.cssText =
            "position:fixed;right:10px;top:10px;max-width:360px;background:#fff;color:#111;padding:10px;z-index:10000;font:14px sans-serif";
          const note = document.createElement("p");
          note.textContent = `Windows Microsoft IMEを日本語にして「てすと」を変換中に${operation}。Enterケースはcompositionend後に次のEnterも操作。候補${candidates ? "あり" : "なし"}。自動操作はしません。`;
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = "このケースの記録を保存して次へ";
          button.onclick = () => {
            window.__mediImeDone = true;
          };
          panel.append(note, button);
          document.body.append(panel);
        },
        { operation, candidates },
      );
      await chat.input.focus();
      if (smoke) {
        await chat.input.fill("recorder smoke only");
        await page
          .getByRole("button", { name: "このケースの記録を保存して次へ" })
          .click();
      } else
        console.log(
          `Microsoft IMEで手動操作してください: ${testInfo.title}, ${page.url()}`,
        );
      await page.waitForFunction(() => window.__mediImeDone === true, {}, { timeout: 0 });
      await page.evaluate(() => Promise.all(window.__mediImePending ?? []));
      const events = await page.evaluate(() => window.__mediImeEvents ?? []);
      const final = {
        focusAfterRecorderSave: await page.evaluate(() => ({
          tag: document.activeElement?.tagName,
          text: document.activeElement?.textContent?.slice(0, 80),
        })),
        value: await chat.input.inputValue(),
        selection: await chat.input.evaluate((input) => ({
          start: (input as HTMLInputElement).selectionStart,
          end: (input as HTMLInputElement).selectionEnd,
        })),
        popup: await page.getByRole("listbox").count(),
        wsCount: chat.requests.length,
        payloads: chat.requests,
      };
      const frontendRoot = resolve(__dirname, "..");
      const directory = resolve(
        frontendRoot,
        "../tmp/stylex-ime-recordings",
        `${smoke ? "smoke" : "native"}-${testInfo.project.name}`,
      );
      mkdirSync(directory, { recursive: true });
      const sourceRoot =
        testInfo.project.name === "baseline"
          ? resolve(frontendRoot, "../tmp/stylex-ime-baseline")
          : frontendRoot;
      const sourceFiles =
        testInfo.project.name === "baseline"
          ? [
              "app/components/ChatInputForm.tsx",
              "app/hooks/useChatWebSocket.ts",
              "app/components/MedicineAutocompleteInput.tsx",
              "app/hooks/useMedicineAutocomplete.ts",
            ]
          : [
              "features/chat/components/ChatInputForm.tsx",
              "features/chat/hooks/useChatWebSocket.ts",
              "features/medicine-selection/components/MedicineAutocompleteInput.tsx",
              "features/medicine-selection/hooks/useMedicineAutocomplete.ts",
            ];
      const sourceHashes = Object.fromEntries(
        sourceFiles.map((name) => [
          name,
          createHash("sha256")
            .update(readFileSync(resolve(sourceRoot, name)))
            .digest("hex"),
        ]),
      );
      const record = {
        status: smoke ? "SMOKE_ONLY_NOT_NATIVE_IME" : "RECORDED_UNREVIEWED",
        phase: testInfo.project.name,
        baselineHead: "7b46073b2fc07b9cad43072bf97ae86cbe13b916",
        nativeBaselineCollected: !smoke && testInfo.project.name === "baseline",
        comparisonReviewed: false,
        candidates,
        operation,
        browserName,
        viewport: page.viewportSize(),
        locale: "ja-JP",
        sourceHashes,
        events,
        final,
      };
      const filename = resolve(
        directory,
        `${candidates ? "candidates" : "none"}-${operation}.json`,
      );
      writeFileSync(filename, JSON.stringify(record, null, 2));
      await testInfo.attach("ime-record", {
        body: JSON.stringify(record),
        contentType: "application/json",
      });
      await expect(page.getByText("connected", { exact: true })).toBeVisible();
    });
  }
