import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { analyzeTranscriptOverhead, formatHarnessMetrics, summarizeHarnessMetrics } from "./harness-metrics.mjs";

test("summarizeHarnessMetrics aggregates stop receipts, reports, edit loops, defense state, and transcript overhead", () => {
  const root = mkdtempSync(join(tmpdir(), "harness-metrics-"));
  try {
    const hooksDir = join(root, "hooks");
    const qualityDir = join(root, "quality");
    mkdirSync(hooksDir, { recursive: true });
    mkdirSync(qualityDir, { recursive: true });

    // 2 stop receipts: 1 passed, 1 stagnated
    writeFileSync(
      join(hooksDir, "turn1.json"),
      JSON.stringify({
        signature: "sig-1",
        spec_signature: "spec-1",
        result: 0,
        status: "passed",
        attempts: 1,
        repeated_failures: 0,
      }),
    );
    writeFileSync(
      join(hooksDir, "turn2.json"),
      JSON.stringify({
        signature: "sig-2",
        spec_signature: "spec-1",
        result: 1,
        status: "stagnated",
        attempts: 3,
        repeated_failures: 3,
      }),
    );

    // 1 edit state with 1 warning
    writeFileSync(
      join(hooksDir, "turn2.edits.json"),
      JSON.stringify({
        version: 1,
        counts: { "backend/main.py": 5, "scripts/checks/quality.mjs": 2 },
        warned: ["backend/main.py"],
      }),
    );

    // 1 defense error state
    writeFileSync(
      join(hooksDir, "turn2.errors.json"),
      JSON.stringify({
        consecutive_errors: 4,
        reset_injected: true,
        last_error: "Mypy error",
      }),
    );

    // 1 hook report + 1 tmp/quality report + 1 task.json (which should be ignored as a report)
    writeFileSync(
      join(hooksDir, "turn2.report.json"),
      JSON.stringify({
        version: 1,
        status: "failed",
        tasks: [
          { label: "Backend Mypy", status: "failed", durationMs: 12000 },
          { label: "Layer boundaries", status: "passed", durationMs: 500 },
        ],
      }),
    );
    writeFileSync(
      join(qualityDir, "result.json"),
      JSON.stringify({
        version: 1,
        status: "passed",
        tasks: [
          { label: "Backend Mypy", status: "passed", durationMs: 8000 },
          { label: "Acceptance", status: "passed", durationMs: 300 },
        ],
      }),
    );
    writeFileSync(
      join(qualityDir, "task.json"),
      JSON.stringify({ version: 1, task: "demo", requirements: [] }),
    );

    // JSONL transcript with 1 harness write and 1 product code write
    const transcriptPath = join(root, "transcript.jsonl");
    const harnessCall = {
      name: "write_file",
      arguments: JSON.stringify({ Path: "tmp/quality/task.json", Content: "x".repeat(100) }),
    };
    const productCall = {
      name: "write_file",
      arguments: JSON.stringify({ Path: "backend/app.py", Content: "y".repeat(300) }),
    };
    writeFileSync(
      transcriptPath,
      [
        JSON.stringify({ type: "USER_INPUT", content: "implement feature" }),
        JSON.stringify({ type: "PLANNER_RESPONSE", content: "", tool_calls: [harnessCall, productCall] }),
      ].join("\n"),
    );

    const summary = summarizeHarnessMetrics({ hooksDir, qualityDir, transcriptPath });
    assert.equal(summary.stop.totalRuns, 2);
    assert.equal(summary.stop.passed, 1);
    assert.equal(summary.stop.stagnated, 1);
    assert.equal(summary.stop.blockRate, 0.5);
    assert.equal(summary.stop.totalRepairAttempts, 4);
    assert.equal(summary.stop.maxRepeatedFailures, 3);

    assert.equal(summary.reports.reportCount, 2);
    assert.equal(summary.reports.totalCheckDurationMs, 20800);
    assert.equal(summary.reports.slowestTasks[0].label, "Backend Mypy");
    assert.equal(summary.reports.slowestTasks[0].totalDurationMs, 20000);
    assert.equal(summary.reports.slowestTasks[0].failures, 1);

    assert.equal(summary.edits.turnsWithEdits, 1);
    assert.equal(summary.edits.totalTrackedEdits, 7);
    assert.equal(summary.edits.editLoopWarnings, 1);

    assert.equal(summary.defense.cognitiveResetsTriggered, 1);
    assert.equal(summary.defense.maxConsecutiveErrors, 4);

    assert.ok(summary.transcript.totalOutputChars > 0);
    assert.ok(summary.transcript.harnessOverheadChars > 0);
    assert.ok(summary.transcript.harnessOverheadRatio > 0.2 && summary.transcript.harnessOverheadRatio < 0.4);

    const text = formatHarnessMetrics(summary);
    assert.match(text, /Stop runs: 2/);
    assert.match(text, /Backend Mypy: total 20\.00s/);
    assert.match(text, /Transcript harness overhead:/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("analyzeTranscriptOverhead returns zeros when transcript path is absent", () => {
  assert.deepEqual(analyzeTranscriptOverhead(null), {
    totalOutputChars: 0,
    harnessOverheadChars: 0,
    harnessOverheadRatio: 0,
  });
});
