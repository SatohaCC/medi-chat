import assert from "node:assert/strict";
import test from "node:test";
import { backendBaseUrl } from "./endpoints.ts";

test("HTTP origin resolution honors explicit URLs without browser state", () => {
  const previous = process.env.NEXT_PUBLIC_API_URL;
  try {
    delete process.env.NEXT_PUBLIC_API_URL;
    assert.equal(backendBaseUrl(), "");
    process.env.NEXT_PUBLIC_API_URL = "https://example.test///";
    assert.equal(backendBaseUrl(), "https://example.test");
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = previous;
  }
});
