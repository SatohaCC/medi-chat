import assert from "node:assert/strict";
import test from "node:test";
import { backendBaseUrl, wsBaseUrl } from "./endpoints.ts";

test("SX-18: explicit URLs, SSR, port 3000 and same-origin protocols remain", () => {
  const api = process.env.NEXT_PUBLIC_API_URL,
    ws = process.env.NEXT_PUBLIC_WS_URL;
  try {
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_WS_URL;
    assert.equal(backendBaseUrl(), "");
    assert.equal(wsBaseUrl(), "ws://localhost:8000/api/ws");
    for (const [protocol, port, host, http, websocket] of [
      [
        "http:",
        "3000",
        "example.test:3000",
        "http://example.test:8000",
        "ws://example.test:8000/api/ws",
      ],
      ["https:", "443", "example.test", "", "wss://example.test/api/ws"],
      ["http:", "3100", "example.test:3100", "", "ws://example.test:3100/api/ws"],
    ]) {
      globalThis.window = {
        location: { protocol, port, host, hostname: "example.test" },
      };
      assert.equal(backendBaseUrl(), http);
      assert.equal(wsBaseUrl(), websocket);
    }
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test///";
    process.env.NEXT_PUBLIC_WS_URL = "wss://ws.example.test/custom";
    assert.equal(backendBaseUrl(), "https://api.example.test");
    assert.equal(wsBaseUrl(), "wss://ws.example.test/custom");
  } finally {
    delete globalThis.window;
    if (api === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = api;
    if (ws === undefined) delete process.env.NEXT_PUBLIC_WS_URL;
    else process.env.NEXT_PUBLIC_WS_URL = ws;
  }
});
