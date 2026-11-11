// Aggregate hook receipts, quality reports, edit-loop states, and optional JSONL transcripts
// to quantify harness overhead (wait time, stop block rate, stagnation, and record-keeping ratio).
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = fileURLToPath(new URL("../../", import.meta.url));

function readJsonSafe(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function isReceiptFile(name) {
  if (!name.endsWith(".json")) return false;
  return ![
    ".report.json",
    ".edits.json",
    ".errors.json",
    ".warn.json",
    ".quality-feedback.json",
    ".quality-stop.json",
    ".privacy.json",
  ].some((suffix) => name.endsWith(suffix));
}

export function analyzeTranscriptOverhead(transcriptPath) {
  if (!transcriptPath || !existsSync(transcriptPath)) {
    return {
      totalOutputChars: 0,
      harnessOverheadChars: 0,
      harnessOverheadRatio: 0,
    };
  }
  const lines = readFileSync(transcriptPath, "utf8").split(/\r?\n/).filter(Boolean);
  let totalOutputChars = 0;
  let harnessOverheadChars = 0;

  for (const line of lines) {
    let step;
    try {
      step = JSON.parse(line);
    } catch {
      continue;
    }
    if (step?.type !== "PLANNER_RESPONSE") continue;
    const content = typeof step.content === "string" ? step.content : "";
    totalOutputChars += content.length;

    const toolCalls = Array.isArray(step.tool_calls) ? step.tool_calls : [];
    for (const call of toolCalls) {
      const argsText = typeof call?.arguments === "string"
        ? call.arguments
        : JSON.stringify(call?.arguments ?? call?.args ?? {});
      totalOutputChars += argsText.length;
      if (/(?:for-llm\/|tmp\/quality\/task\.json|\.agents\/work\/\.hooks)/.test(argsText)) {
        harnessOverheadChars += argsText.length;
      }
    }
  }

  return {
    totalOutputChars,
    harnessOverheadChars,
    harnessOverheadRatio: totalOutputChars > 0
      ? Number((harnessOverheadChars / totalOutputChars).toFixed(4))
      : 0,
  };
}

export function summarizeHarnessMetrics({
  hooksDir = resolve(ROOT, ".agents/work/.hooks"),
  qualityDir = resolve(ROOT, "tmp/quality"),
  transcriptPath = null,
} = {}) {
  const stopStats = {
    totalRuns: 0,
    passed: 0,
    failed: 0,
    stagnated: 0,
    attemptLimit: 0,
    timeout: 0,
    startError: 0,
    blockRate: 0,
    totalRepairAttempts: 0,
    maxRepeatedFailures: 0,
  };
  const editStats = {
    turnsWithEdits: 0,
    totalTrackedEdits: 0,
    editLoopWarnings: 0,
  };
  const defenseStats = {
    cognitiveResetsTriggered: 0,
    maxConsecutiveErrors: 0,
  };
  const taskMap = new Map();
  let reportCount = 0;
  let totalCheckDurationMs = 0;

  function ingestReport(report) {
    if (!report || report.version !== 1 || !Array.isArray(report.tasks)) return;
    reportCount++;
    for (const task of report.tasks) {
      const label = typeof task.label === "string" ? task.label : "unknown";
      const durationMs = typeof task.durationMs === "number" && task.durationMs > 0 ? task.durationMs : 0;
      const failed = ["failed", "incomplete", "timeout", "start_error"].includes(task.status);
      totalCheckDurationMs += durationMs;
      const entry = taskMap.get(label) ?? {
        label,
        runs: 0,
        totalDurationMs: 0,
        maxDurationMs: 0,
        failures: 0,
      };
      entry.runs += 1;
      entry.totalDurationMs += durationMs;
      entry.maxDurationMs = Math.max(entry.maxDurationMs, durationMs);
      if (failed) entry.failures += 1;
      taskMap.set(label, entry);
    }
  }

  if (existsSync(hooksDir)) {
    for (const entry of readdirSync(hooksDir, { withFileTypes: true })) {
      if (!entry.isFile()) continue;
      const fullPath = resolve(hooksDir, entry.name);
      if (entry.name.endsWith(".report.json")) {
        ingestReport(readJsonSafe(fullPath));
      } else if (entry.name.endsWith(".edits.json")) {
        const data = readJsonSafe(fullPath);
        if (data && data.version === 1 && data.counts && typeof data.counts === "object") {
          editStats.turnsWithEdits += 1;
          for (const count of Object.values(data.counts)) {
            if (typeof count === "number" && count > 0) editStats.totalTrackedEdits += count;
          }
          if (Array.isArray(data.warned)) {
            editStats.editLoopWarnings += data.warned.length;
          }
        }
      } else if (entry.name.endsWith(".errors.json")) {
        const data = readJsonSafe(fullPath);
        if (data && typeof data === "object") {
          if (data.reset_injected) defenseStats.cognitiveResetsTriggered += 1;
          const consecutive = typeof data.consecutive_errors === "number" ? data.consecutive_errors : 0;
          defenseStats.maxConsecutiveErrors = Math.max(defenseStats.maxConsecutiveErrors, consecutive);
        }
      } else if (isReceiptFile(entry.name)) {
        const data = readJsonSafe(fullPath);
        if (data && typeof data.signature === "string" && typeof data.status === "string") {
          stopStats.totalRuns += 1;
          if (data.status === "passed") stopStats.passed += 1;
          else if (data.status === "stagnated") stopStats.stagnated += 1;
          else if (data.status === "attempt_limit") stopStats.attemptLimit += 1;
          else if (data.status === "timeout") stopStats.timeout += 1;
          else if (data.status === "start_error") stopStats.startError += 1;
          else stopStats.failed += 1;

          if (typeof data.attempts === "number" && data.attempts > 0) {
            stopStats.totalRepairAttempts += data.attempts;
          }
          if (typeof data.repeated_failures === "number" && data.repeated_failures > 0) {
            stopStats.maxRepeatedFailures = Math.max(
              stopStats.maxRepeatedFailures,
              data.repeated_failures,
            );
          }
        }
      }
    }
  }

  if (existsSync(qualityDir)) {
    for (const entry of readdirSync(qualityDir, { withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.endsWith(".json") || entry.name === "task.json") continue;
      ingestReport(readJsonSafe(resolve(qualityDir, entry.name)));
    }
  }

  if (stopStats.totalRuns > 0) {
    const blocked = stopStats.totalRuns - stopStats.passed;
    stopStats.blockRate = Number((blocked / stopStats.totalRuns).toFixed(4));
  }

  const slowestTasks = [...taskMap.values()]
    .sort((a, b) => b.totalDurationMs - a.totalDurationMs || b.maxDurationMs - a.maxDurationMs)
    .slice(0, 5);

  return {
    version: 1,
    stop: stopStats,
    reports: {
      reportCount,
      totalCheckDurationMs,
      slowestTasks,
    },
    edits: editStats,
    defense: defenseStats,
    transcript: analyzeTranscriptOverhead(transcriptPath),
  };
}

export function formatHarnessMetrics(summary) {
  const lines = [
    `[harness-metrics] Stop runs: ${summary.stop.totalRuns} (passed: ${summary.stop.passed}, blockRate: ${(summary.stop.blockRate * 100).toFixed(1)}%, stagnated: ${summary.stop.stagnated}, attemptLimit: ${summary.stop.attemptLimit})`,
    `[harness-metrics] Quality reports: ${summary.reports.reportCount}, total check time: ${(summary.reports.totalCheckDurationMs / 1000).toFixed(2)}s`,
    `[harness-metrics] Edit tracking: ${summary.edits.totalTrackedEdits} edits across ${summary.edits.turnsWithEdits} turns (5-edit warnings: ${summary.edits.editLoopWarnings})`,
    `[harness-metrics] Defense resets: ${summary.defense.cognitiveResetsTriggered} (max consecutive errors: ${summary.defense.maxConsecutiveErrors})`,
  ];
  if (summary.transcript.totalOutputChars > 0) {
    lines.push(
      `[harness-metrics] Transcript harness overhead: ${(summary.transcript.harnessOverheadRatio * 100).toFixed(1)}% (${summary.transcript.harnessOverheadChars}/${summary.transcript.totalOutputChars} chars)`,
    );
  }
  if (summary.reports.slowestTasks.length > 0) {
    lines.push("[harness-metrics] Top tasks by cumulative duration:");
    for (const task of summary.reports.slowestTasks) {
      lines.push(
        `  - ${task.label}: total ${(task.totalDurationMs / 1000).toFixed(2)}s, max ${(task.maxDurationMs / 1000).toFixed(2)}s (${task.runs} runs, ${task.failures} failed)`,
      );
    }
  }
  return lines.join("\n");
}

export function main(args = process.argv.slice(2)) {
  const argValue = (flag) => {
    const idx = args.indexOf(flag);
    return idx >= 0 && args[idx + 1] && !args[idx + 1].startsWith("--") ? resolve(args[idx + 1]) : undefined;
  };
  const summary = summarizeHarnessMetrics({
    hooksDir: argValue("--hooks-dir"),
    qualityDir: argValue("--quality-dir"),
    transcriptPath: argValue("--transcript") ?? null,
  });
  if (args.includes("--json")) {
    console.log(JSON.stringify(summary, null, 2));
  } else {
    console.log(formatHarnessMetrics(summary));
  }
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main();
}
