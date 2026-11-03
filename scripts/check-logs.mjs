#!/usr/bin/env node

import { lstatSync, readFileSync, realpathSync, statSync } from "node:fs";
import { basename, dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(SCRIPT_DIRECTORY, "..");
export const LOG_DIRECTORY = resolve(PROJECT_ROOT, "tmp", "logs");

const LOG_FILENAME = /^dev-backend-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z-\d+-[0-9a-f-]{36}\.log$/;
const ISO_TIMESTAMP = /^(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})T(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(?:\.\d+)?(?<zone>Z|[+-]\d{2}:\d{2})$/;
const SESSION_LINE = /^(?<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z) \[(?<stream>stdout|stderr)\] (?<message>.*)$/;
const ACCESS_5XX = /"[A-Z]+\s+\S+\s+HTTP\/\d(?:\.\d)?"\s+(?<status>5\d{2})\b/;

function isWithinDirectory(directory, target) {
  const path = relative(directory, target);
  return path !== "" && path !== ".." && !path.startsWith(`..${sep}`) && !isAbsolute(path);
}

export function resolveSessionLogPath(candidate, {
  projectRoot = PROJECT_ROOT,
  logDirectory = resolve(projectRoot, "tmp", "logs"),
} = {}) {
  if (typeof candidate !== "string" || !candidate.trim()) {
    throw new Error("Choose a generated session log under tmp/logs.");
  }

  const target = isAbsolute(candidate) ? resolve(candidate) : resolve(projectRoot, candidate);
  const expectedDirectory = resolve(logDirectory);
  if (!isWithinDirectory(expectedDirectory, target) || relative(expectedDirectory, target).includes(sep)) {
    throw new Error("Session log must be directly under tmp/logs.");
  }
  if (!LOG_FILENAME.test(basename(target))) {
    throw new Error("Session log must be a generated session log under tmp/logs.");
  }

  try {
    if (lstatSync(expectedDirectory).isSymbolicLink()) {
      throw new Error("Session log directory symlinks are not allowed.");
    }
    if (lstatSync(target).isSymbolicLink()) {
      throw new Error("Session log symlinks are not allowed.");
    }
    const realProjectRoot = realpathSync(projectRoot);
    const realDirectory = realpathSync(expectedDirectory);
    const realTarget = realpathSync(target);
    if (realDirectory !== resolve(realProjectRoot, "tmp", "logs")) {
      throw new Error("Session log directory must be tmp/logs.");
    }
    if (!isWithinDirectory(realDirectory, realTarget) || relative(realDirectory, realTarget).includes(sep)) {
      throw new Error("Session log must be directly under tmp/logs.");
    }
    if (!statSync(realTarget).isFile()) {
      throw new Error("Session log must be a file.");
    }
    return realTarget;
  } catch (error) {
    if (error instanceof Error && /^(?:Session log|Choose a generated)/.test(error.message)) throw error;
    throw new Error("Generated session log was not found under tmp/logs.");
  }
}

export function parseSince(value) {
  const match = typeof value === "string" ? ISO_TIMESTAMP.exec(value) : null;
  if (!match) throw new Error("--since requires an ISO date-time with a timezone.");

  const { year, month, day, hour, minute, second } = match.groups;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  if (
    Number(year) < 1000
    || date.getUTCFullYear() !== Number(year)
    || date.getUTCMonth() !== Number(month) - 1
    || date.getUTCDate() !== Number(day)
    || Number(hour) > 23
    || Number(minute) > 59
    || Number(second) > 59
    || !Number.isFinite(Date.parse(value))
  ) {
    throw new Error("--since requires a valid ISO date-time with a timezone.");
  }
  return Date.parse(value);
}

export function scanSessionLog(contents, since = null) {
  const cutoff = since === null ? null : typeof since === "number" ? since : parseSince(since);
  const lines = contents.split(/\r?\n/);
  if (lines.at(-1) === "") lines.pop();
  const findings = [];

  for (const [index, line] of lines.entries()) {
    const match = SESSION_LINE.exec(line);
    if (!match || !Number.isFinite(Date.parse(match.groups.timestamp))) {
      throw new Error(`Session log format is invalid at line ${index + 1}.`);
    }
    if (cutoff !== null && Date.parse(match.groups.timestamp) < cutoff) continue;

    const categories = [];
    if (/^(?:ERROR|CRITICAL):/i.test(match.groups.message)) {
      categories.push(match.groups.message.startsWith("CRITICAL:") ? "CRITICAL" : "ERROR");
    }
    const accessMatch = ACCESS_5XX.exec(match.groups.message);
    if (accessMatch) categories.push(`HTTP ${accessMatch.groups.status}`);
    if (categories.length) findings.push({ line: index + 1, categories });
  }

  return findings;
}

function readSessionLog(path) {
  try {
    return readFileSync(path, "utf8");
  } catch {
    throw new Error("Generated session log could not be read.");
  }
}

export function checkSessionLog(candidate, { projectRoot = PROJECT_ROOT, logDirectory, since = null } = {}) {
  const path = resolveSessionLogPath(candidate, { projectRoot, logDirectory });
  return { path, findings: scanSessionLog(readSessionLog(path), since) };
}

function parseArguments(args) {
  const values = args[0] === "--" ? args.slice(1) : args;
  if (values.length === 1) return { candidate: values[0], since: null };
  if (values.length === 3 && values[1] === "--since") {
    return { candidate: values[0], since: parseSince(values[2]) };
  }
  throw new Error("Usage: pnpm logs:check -- <session-log> [--since <ISO date-time>]");
}

export function main(args) {
  try {
    const { candidate, since } = parseArguments(args);
    const path = resolveSessionLogPath(candidate);
    const findings = scanSessionLog(readSessionLog(path), since);
    const label = relative(PROJECT_ROOT, path).replaceAll("\\", "/");
    if (!findings.length) {
      console.log(`[logs:check] 0 findings in ${label}`);
      return 0;
    }
    for (const finding of findings) {
      console.log(`[logs:check] ${label}:${finding.line} ${finding.categories.join(", ")}`);
    }
    return 1;
  } catch (error) {
    console.error(`[logs:check] ${error.message}`);
    return 2;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}
