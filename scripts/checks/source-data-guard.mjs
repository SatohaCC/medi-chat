import { readFileSync, readdirSync } from "node:fs";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const TEST_DIRECTORIES = [
  "frontend/features",
  "frontend/shared",
  "frontend/scripts",
  "scripts",
];
const IGNORED_SOURCE_DATA_PATH = /(?:^|[^\w.-])data[\\/]pmda[\\/](?:originals|structured)(?=$|[\\/])/i;
const SOURCE_DATA_SEGMENTS = /(["'`])data\1\s*,\s*(["'`])pmda\2\s*,\s*(["'`])(?:originals|structured)\3/i;
const READ_CALL = /\b(?:readFileSync|readFile|openSync|open|createReadStream)\s*\(/g;
const PATH_CALL = /\b(?:join|resolve)\s*\(/g;

function callsWithArguments(source, pattern) {
  return [...source.matchAll(pattern)].flatMap((match) => {
    const opening = match.index + match[0].lastIndexOf("(");
    let depth = 1;
    let quote = null;
    let escaped = false;
    for (let index = opening + 1; index < source.length; index++) {
      const character = source[index];
      if (quote) {
        if (escaped) escaped = false;
        else if (character === "\\") escaped = true;
        else if (character === quote) quote = null;
        continue;
      }
      if (character === "\"" || character === "'" || character === "`") quote = character;
      else if (character === "(") depth++;
      else if (character === ")" && --depth === 0) {
        return [{
          index: match.index,
          line: source.slice(0, match.index).split(/\r?\n/).length,
          text: source.slice(match.index, index + 1),
          arguments: source.slice(opening + 1, index),
        }];
      }
    }
    return [];
  });
}

export function findIgnoredSourceDataReferences(file, source) {
  const directReferences = source.split(/\r?\n/).flatMap((line, index) =>
    IGNORED_SOURCE_DATA_PATH.test(line)
      ? [{ file, line: index + 1 }]
      : [],
  );
  const reads = callsWithArguments(source, READ_CALL);
  const dynamicReferences = callsWithArguments(source, PATH_CALL)
    .filter((builder) => SOURCE_DATA_SEGMENTS.test(builder.arguments))
    .filter((builder) => {
      const declaration = source.slice(0, builder.index).match(/\b(?:const|let|var)\s+([\w$]+)\s*=\s*(?:[\w$]+\.)?$/);
      const assignedPath = declaration?.[1];
      return reads.some((read) =>
        read.arguments.includes(builder.text)
        || (assignedPath && new RegExp(`\\b${assignedPath}\\b`).test(read.arguments)),
      );
    })
    .map((builder) => ({ file, line: builder.line }));
  return [...directReferences, ...dynamicReferences].sort((left, right) => left.line - right.line);
}

export function scanTestFiles(root = ROOT, directories = TEST_DIRECTORIES) {
  const findings = [];
  for (const directory of directories) {
    const absoluteDirectory = resolve(root, directory);
    for (const entry of readdirSync(absoluteDirectory, { recursive: true, withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.endsWith(".test.mjs")) continue;
      const absoluteFile = resolve(entry.parentPath, entry.name);
      const relativeFile = relative(root, absoluteFile).replaceAll("\\", "/");
      findings.push(...findIgnoredSourceDataReferences(
        relativeFile,
        readFileSync(absoluteFile, "utf8"),
      ));
    }
  }
  return findings.sort((left, right) =>
    left.file.localeCompare(right.file) || left.line - right.line,
  );
}

export function main(args = process.argv.slice(2)) {
  if (args.length !== 1 || args[0] !== "--check") {
    console.error("Usage: node scripts/checks/source-data-guard.mjs --check");
    return 2;
  }
  const findings = scanTestFiles();
  if (findings.length) {
    console.error("Unit tests must not read Git-ignored PMDA originals or generated structured data:");
    for (const finding of findings) console.error(`  ${finding.file}:${finding.line}`);
    return 1;
  }
  console.log("Source-data dependency guard passed.");
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main();
}
