import { createHash } from "node:crypto";

export function acceptanceEvidence(output) {
  const nodeSummary = [...output.matchAll(/^(?:#|ℹ)\s*tests\s+\d+/gm)].at(-1);
  if (nodeSummary) output = output.slice(nodeSummary.index);
  else {
    const summary = output.split(/\r?\n/).filter((line) => /\b\d+ (?:passed|failed|skipped|xfailed|xpassed)\b/.test(line)).at(-1);
    if (summary) output = summary;
  }
  const passed = [...output.matchAll(/(?:\b(\d+) passed\b|(?:#|ℹ)\s*pass\s+(\d+))/g)].at(-1);
  const incomplete = [...output.matchAll(/(?:\b(\d+) (?:skipped|xfailed|xpassed|todo)\b|(?:#|ℹ)\s*(?:skipped|todo)\s+(\d+))/g)]
    .some((match) => Number(match[1] ?? match[2]) > 0);
  return { passed: Number(passed?.[1] ?? passed?.[2] ?? 0), incomplete };
}

export function failureFeedback(task, status, output = "") {
  if (status === "passed") return null;
  const docs = "docs/development/validation.md";
  const diagnostics = [...new Set(output.replace(/\u001b\[[0-9;]*m/g, "").split(/\r?\n/).flatMap((line, index, lines) => {
    if (/^[A-Z]+\d{3,4}\b/.test(line)) {
      const location = lines.slice(index + 1, index + 4).join("\n").match(/-->\s+(.+?):\d+:\d+/);
      if (location) return [`${location[1].replaceAll("\\", "/")}: ${line.trim()}`];
    }
    const failed = line.match(/(?:FAILED\s+)([^\s]+::[^\s]+)(?:\s+-\s+(.+))?/);
    if (failed) return [failed[1] + (failed[2] ? ` - ${failed[2]}` : "")];
    const node = line.match(/^\s*(?:✖\s+|not ok \d+ - )(.+?)(?:\s+\([\d.]+m?s\))?$/);
    if (node && !/^(failing tests|tests \d+)/.test(node[1])) return [node[1]];
    const exception = line.match(/^\s*((?:AssertionError|TypeError|ReferenceError|Error)(?:\s*\[[A-Z_]+\])?:.*|error:\s+.+)$/);
    if (exception) return [exception[1]];
    const diagnostic = line.match(/([\w./\\-]+\.(?:py|[cm]?[jt]sx?))(?::\d+(?::\d+)?|\(\d+,\d+\))\s*:?\s*(?:-\s*)?(.*(?:error|[A-Z]\d{3}).*)/i);
    if (diagnostic) return [`${diagnostic[1].replaceAll("\\", "/")}: ${diagnostic[2].replace(/\s+/g, " ").trim()}`];
    return [];
  }))].sort();
  let suggestion;
  if (status === "incomplete") suggestion = "受入テストの成功件数を確認できないか、skip/xfail/todoが残っている。テスト選択と実行前提を確認し、未実施の条件を成功と扱わない。";
  else if (status === "start_error") suggestion = "実行ファイルと依存環境を確認し、lock済み環境を復旧する。コードの期待値を変更しない。";
  else if (status === "timeout") suggestion = "ログから停止した検査を特定し、所有するprocess・接続先・待ち条件を調べる。タイムアウト延長だけで解消扱いにしない。";
  else if (/ENOTFOUND|EAI_AGAIN|PermissionError|EACCES|EPERM|certificate|SSL|ECONNREFUSED/i.test(output)) suggestion = "環境・接続・権限の失敗候補。chained exceptionを読み、sandbox内の失敗と製品不具合を切り分ける。権限が必要なら通常の承認経路を使い、検査の無効化や自動的な権限拡張で回避しない。";
  else if (/\bF401\b/.test(output)) suggestion = "F401の指す未使用importを削除する。公開APIの再exportなら既存の公開契約に従って明示し、ファイル全体をlint除外しない。";
  else if (/mypy|pyright|types/i.test(task.label)) suggestion = "診断の型と公開署名を照合し、呼出側でNoneを絞り込むか契約に沿った引数へ修正する。cast・ignoreで隠す前に呼出経路を確認する。";
  else if (/lint|format|architecture/i.test(task.label)) suggestion = "該当ファイル・違反コードと設計規約を読み、担当範囲のimport・配置・書式を修正する。禁止規則を緩和しない。";
  else suggestion = "失敗したテストの期待値を受入条件と照合し、最小の再現で実装を修正する。仕様の根拠なくassertionやfixtureを弱めない。";
  const identity = diagnostics.length ? createHash("sha256").update(JSON.stringify([task.label, status, diagnostics])).digest("hex") : null;
  return { identity, diagnostics, suggestion, docs, requirements: task.requirements ?? [] };
}
