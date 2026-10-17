import { expect, test } from "@playwright/test";

test("TC110 focus changes both candidates and warns without replacing vanished YJ", async ({
  page,
}) => {
  let generation = "old";
  const requests: { product_yj_codes: string[] }[] = [];
  await page.route("**/api/medicines", (route) =>
    route.fulfill({
      json: {
        generation_id: generation,
        items: [
          {
            generic_name: "成分",
            brand_names: [generation === "old" ? "旧薬" : "新薬"],
            yj_codes: [generation === "old" ? "3339003F5020" : "222222222222"],
            document_ids: ["doc"],
            matched_aliases: [],
          },
        ],
      },
    }),
  );
  await page.route("**/data/medicines.json", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/medicines/autocomplete", (route) =>
    route.fulfill({
      json: {
        generation_id: generation,
        items: [
          {
            n: generation === "old" ? "旧薬" : "新薬",
            k: "シンヤク",
            h: "しんやく",
            y: generation === "old" ? "3339003F5020" : "222222222222",
            g: "成分",
            c: "他",
          },
        ],
      },
    }),
  );
  await page.routeWebSocket("**/api/ws", (ws) =>
    ws.onMessage((data) => requests.push(JSON.parse(String(data)))),
  );
  await page.goto("/");
  await expect(page.getByRole("button", { name: "旧薬", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  generation = "new";
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByRole("button", { name: "新薬", exact: true })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.getByRole("alert", { name: "選択YJの消失" })).toContainText(
    "3339003F5020",
  );
  await expect(page.getByRole("alert", { name: "選択YJの消失" })).toContainText(
    "自動変更していません",
  );
  const input = page.getByPlaceholder("確認したい内容を入力", { exact: false });
  await input.fill("しんやく");
  await expect(page.getByText("新薬", { exact: true })).toHaveCount(2);
  await input.fill("副作用を確認");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect.poll(() => requests.length).toBe(1);
  expect(requests[0].product_yj_codes).toEqual(["3339003F5020"]);
});
