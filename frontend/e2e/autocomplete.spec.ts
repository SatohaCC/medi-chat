import { expect, test } from "@playwright/test";
import { openChat } from "./helpers/chat";

for (const operation of ["pointer", "Enter", "Tab"] as const) {
  test(`SX-07: ${operation}補完はカーソル前だけを置換する`, async ({ page }) => {
    const chat = await openChat(page);
    await chat.input.fill("前置き テスト 後置き");
    await chat.input.press("Home");
    for (let i = 0; i < 7; i++) await chat.input.press("ArrowRight");
    const options = page
      .getByRole("listbox", { name: "医薬品サジェスト候補" })
      .getByRole("option");
    await expect(options).toHaveCount(2);
    if (operation === "pointer") await options.first().click();
    else await chat.input.press(operation);
    await expect(chat.input).toHaveValue("前置き テスト医薬品A 後置き");
    await expect(chat.input).toBeFocused();
    expect(
      await chat.input.evaluate((input: HTMLInputElement) => [
        input.selectionStart,
        input.selectionEnd,
      ]),
    ).toEqual([11, 11]);
    expect(chat.requests).toHaveLength(0);
    await expect(
      page.getByRole("button", { name: "テスト医薬品A", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    // Closing the popup is observed before any subsequent editing or submission.
    await expect(chat.input).toHaveAttribute("aria-expanded", "false");
  });
}

test("SX-08: 候補の循環・Escapeとカーソル語の基準", async ({ page }) => {
  const chat = await openChat(page);
  for (const [text, count] of [
    ["て", 0],
    ["てす", 2],
    ["薬", 2],
    ["テスト ", 0],
    ["一致なし", 0],
  ] as const) {
    await chat.input.fill(text);
    await expect(
      page.getByRole("listbox", { name: "医薬品サジェスト候補" }).getByRole("option"),
    ).toHaveCount(count);
  }
  await chat.input.fill("テスト");
  const options = page
    .getByRole("listbox", { name: "医薬品サジェスト候補" })
    .getByRole("option");
  await expect(options.first()).toHaveAttribute("aria-selected", "true");
  await chat.input.press("ArrowUp");
  await expect(options.last()).toHaveAttribute("aria-selected", "true");
  await chat.input.press("ArrowDown");
  await expect(options.first()).toHaveAttribute("aria-selected", "true");
  await chat.input.press("Escape");
  await expect(chat.input).toHaveValue("テスト");
  await expect(options).toHaveCount(0);
  expect(chat.requests).toHaveLength(0);
  await chat.input.press("Home");
  await expect(options).toHaveCount(0);
  await chat.input.press("End");
  await expect(options).toHaveCount(2);
  await chat.input.press("ArrowLeft");
  await expect(options).toHaveCount(2);
  await chat.input.press("ArrowRight");
  await expect(options).toHaveCount(2);
});

for (const candidates of [false, true]) {
  for (const key of ["Enter", "Tab", "Escape"]) {
    test(`SX-09合成補助: 候補${candidates ? "あり" : "なし"} composition中${key}`, async ({
      page,
    }, testInfo) => {
      const chat = await openChat(page);
      await chat.input.fill(candidates ? "てすと" : "確認する質問");
      await chat.input.evaluate((input) => {
        input.dataset.compositionEvents = "[]";
        for (const name of [
          "compositionstart",
          "compositionupdate",
          "compositionend",
          "keydown",
          "keyup",
        ]) {
          input.addEventListener(name, (event) => {
            const trace = JSON.parse(input.dataset.compositionEvents || "[]");
            trace.push(
              event instanceof KeyboardEvent
                ? {
                    type: event.type,
                    key: event.key,
                    keyCode: event.keyCode,
                    isComposing: event.isComposing,
                  }
                : { type: event.type, data: (event as CompositionEvent).data },
            );
            input.dataset.compositionEvents = JSON.stringify(trace);
          });
        }
      });
      await chat.input.evaluate((input) =>
        input.dispatchEvent(
          new CompositionEvent("compositionstart", { bubbles: true, data: "" }),
        ),
      );
      await chat.input.evaluate((input) =>
        input.dispatchEvent(
          new CompositionEvent("compositionupdate", { bubbles: true, data: "てすと" }),
        ),
      );
      await chat.input.dispatchEvent("keydown", { key, isComposing: true, keyCode: 229 });
      await chat.input.dispatchEvent("keyup", { key, isComposing: true, keyCode: 229 });
      await chat.input.evaluate((input) =>
        input.dispatchEvent(
          new CompositionEvent("compositionend", { bubbles: true, data: "てすと" }),
        ),
      );
      const observed = await chat.input.evaluate((input: HTMLInputElement) => ({
        value: input.value,
        selection: [input.selectionStart, input.selectionEnd],
        expanded: input.getAttribute("aria-expanded"),
        focused: document.activeElement === input,
      }));
      const accepted = candidates && key !== "Escape";
      expect(observed).toEqual({
        value: accepted ? "テスト医薬品A" : candidates ? "てすと" : "確認する質問",
        selection: accepted ? [7, 7] : candidates ? [3, 3] : [6, 6],
        expanded: accepted ? "true" : "false",
        focused: true,
      });
      await testInfo.attach("synthetic-composition-observation", {
        body: JSON.stringify({ candidates, key, observed, requests: chat.requests }),
        contentType: "application/json",
      });
      console.log(
        "SYNTHETIC_IME_BASELINE",
        JSON.stringify({ candidates, key, observed, requests: chat.requests }),
      );
      expect(chat.requests).toHaveLength(0);
      await chat.input.press("Enter");
      if (accepted) {
        await expect(chat.input).toHaveAttribute("aria-expanded", "false");
        await expect(chat.input).toHaveValue("テスト医薬品A");
        expect(chat.requests).toHaveLength(0);
      } else {
        await expect.poll(() => chat.requests.length).toBe(1);
        expect(chat.requests[0].product_yj_codes).toEqual(["3339003F5020"]);
      }
      const events = await chat.input.evaluate((input) =>
        JSON.parse(input.dataset.compositionEvents || "[]"),
      );
      expect(events.slice(0, 5)).toEqual([
        { type: "compositionstart", data: "" },
        { type: "compositionupdate", data: "てすと" },
        { type: "keydown", key, keyCode: 229, isComposing: true },
        { type: "keyup", key, keyCode: 229, isComposing: true },
        { type: "compositionend", data: "てすと" },
      ]);
      console.log(
        "SYNTHETIC_IME_EVENTS",
        JSON.stringify({ candidates, key, events, requests: chat.requests }),
      );
    });
  }
}
