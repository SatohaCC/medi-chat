import { strict as assert } from "node:assert";
import { test } from "node:test";
import { ActiveMedicineCatalog } from "./activeMedicineCatalog.ts";

const groups = (generation, code) => ({
  generation_id: generation,
  items: [
    {
      generic_name: code,
      brand_names: [code],
      yj_codes: [code],
      document_ids: ["doc"],
      matched_aliases: [],
    },
  ],
});
const compact = (generation, code) => ({
  generation_id: generation,
  items: [{ n: code, k: code, h: code, y: code, g: code, c: "他" }],
});
test("TC110 delayed older refresh cannot roll catalogue back", async () => {
  let release;
  let calls = 0;
  const old = new Promise((resolve) => {
    release = resolve;
  });
  const client = new ActiveMedicineCatalog(async (url) => {
    const number = ++calls;
    if (number <= 2) {
      await old;
      return Response.json(
        String(url).endsWith("autocomplete") ? compact("old", "A") : groups("old", "A"),
      );
    }
    return Response.json(
      String(url).endsWith("autocomplete") ? compact("new", "B") : groups("new", "B"),
    );
  });
  const pending = client.refresh();
  await client.refresh();
  release();
  await pending;
  assert.equal(client.snapshot.generation_id, "new");
  assert.equal(client.snapshot.items[0].y, "B");
  assert.deepEqual(client.snapshot.groups[0].yj_codes, ["B"]);
});
test("TC110 mismatched group/compact generations never publish mixed candidates", async () => {
  let calls = 0;
  const client = new ActiveMedicineCatalog(async (url) => {
    const number = ++calls;
    return Response.json(
      String(url).endsWith("autocomplete")
        ? compact(number <= 2 ? "old" : "new", "B")
        : groups("new", "B"),
    );
  });
  await client.refresh();
  assert.equal(client.snapshot.generation_id, "new");
  assert.deepEqual(client.snapshot.groups[0].yj_codes, [client.snapshot.items[0].y]);
});
