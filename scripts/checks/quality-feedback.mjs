import { createHash } from "node:crypto";

export function acceptanceEvidence(output, runner = "auto") {
  output = output.replace(/\u001b\[[0-9;]*m/g, "");
  if (runner === "configured-backend") {
    const receipts = output.split(/\r?\n/).flatMap((line) => {
      try {
        const receipt = JSON.parse(line);
        return receipt && typeof receipt === "object" && !Array.isArray(receipt) ? [receipt] : [];
      } catch {
        return [];
      }
    });
    const health = [...receipts].reverse().find((receipt) => receipt.readiness !== undefined);
    const passed = health?.backend === "postgresql"
      && health.readiness === "passed"
      && health.os_health?.status === "ok";
    return { passed: passed ? 1 : 0, incomplete: !passed };
  }
  const nodeSummary = [...output.matchAll(/^(?:#|ℹ)\s*tests\s+\d+/gm)].at(-1);
  if ((runner === "node" || runner === "auto") && nodeSummary) output = output.slice(nodeSummary.index);
  else if (runner === "pytest") {
    const summary = output.split(/\r?\n/).filter((line) => /\b\d+ (?:passed|failed|skipped|xfailed|xpassed)\b/.test(line)).at(-1);
    if (summary) output = summary;
  }
  const passedPattern = runner === "playwright" ? /\b(\d+) passed\b/g : /(?:\b(\d+) passed\b|(?:#|ℹ)\s*pass\s+(\d+))/g;
  const passed = [...output.matchAll(passedPattern)]
    .reduce((total, match) => total + Number(match[1] ?? match[2]), 0);
  const incomplete = [...output.matchAll(/(?:\b(\d+) (?:skipped|xfailed|xpassed|todo)\b|(?:#|ℹ)\s*(?:skipped|todo)\s+(\d+))/g)]
    .some((match) => Number(match[1] ?? match[2]) > 0);
  return { passed, incomplete };
}

export function failureFeedback(task, status, output = "", exitCode = null) {
  if (status === "passed") return null;
  const rawClean = output.replace(/\u001b\[[0-9;]*m/g, "");
  let docs = "docs/development/validation.md";
  if (task.label === "Quality specification" || /quality specification|Requirements need unique ids|Unknown integration suite|Unsafe test path|Test must be an existing file/i.test(rawClean)) {
    docs = "scripts/README.md";
  } else if (task.label === "Frontend boundaries" || /UI library imports belong to shared\/ui|Features must use shared\/|Feature UI bypass|Forbidden (?:routing )?dependency|shared imports must be statically resolvable/i.test(rawClean)) {
    docs = "docs/architecture/frontend-shared.md";
  } else if (task.label === "Domain architecture" || /\bDOM\d{3}\b/.test(rawClean)) {
    docs = "docs/architecture/domain-architecture.md";
  } else if (task.label === "Application architecture" || /\bAPP\d{3}\b/.test(rawClean)) {
    docs = "docs/architecture/application-architecture.md";
  } else if (task.label === "Infrastructure architecture" || /\bINF\d{3}\b/.test(rawClean)) {
    docs = "docs/architecture/infrastructure-architecture.md";
  } else if (task.label === "Layer boundaries" || /\bLAY\d{3}\b|BROKEN CONTRACT/.test(rawClean)) {
    docs = "docs/architecture/backend-design.md";
  }

  const rawDiagnostics = rawClean.split(/\r?\n/).flatMap((line, index, lines) => {
    if (/^[A-Z]+\d{3,4}\b/.test(line)) {
      const location = lines.slice(index + 1, index + 4).join("\n").match(/-->\s+(.+?):\d+:\d+/);
      if (location) return [`${location[1].replaceAll("\\", "/")}: ${line.trim()}`];
    }
    const ruffFormat = line.match(/^Would reformat:\s*(.+)$/);
    if (ruffFormat) return [`Would reformat: ${ruffFormat[1].replaceAll("\\", "/")}`];

    const brokenContract = line.match(/^\s*(?:BROKEN CONTRACT:\s*(.+)|Module ['"](.+)['"] is not allowed to import ['"](.+)['"])/);
    if (brokenContract) return [brokenContract[0].trim()];

    const archRule = line.match(/^([\w./\\-]+):\d+:\s*((?:LAY|DOM|APP|INF)\d{3}\s+.+)$/);
    if (archRule) return [`${archRule[1].replaceAll("\\", "/")}: ${archRule[2].trim()}`];

    const boundaryViolation = line.match(/(?:.+:\d+:\s*(?:UI library imports belong to shared\/ui|Features must use shared\/component).+|.+:\s*shared imports must be statically resolvable|(?:Feature UI bypass|Forbidden (?:routing )?dependency|Features must use shared\/|Domain layer cannot import|Application layer cannot import|Infrastructure layer cannot import).+)/);
    if (boundaryViolation) return [boundaryViolation[0].trim()];

    const ntstatus = line.match(/(?:returned non-zero exit status|exit (?:status (?:exit )?)?code:?)\s*(?:3221225794|3228369022|3221225477|3221225781|-1073741502|-1066598274|-1073741819|-1073741515|0xC0000142|0xC06D007E|0xC0000005|0xC0000135)|DLL load failed while importing .+/i);
    if (ntstatus) return [`Windows process initialization failure: ${ntstatus[0].trim()}`];

    const pytestCollection = line.match(/ERROR collecting (.+)|collected 0 items|no tests ran in|^ERROR:\s*(?:usage:|file or directory not found|unrecognized arguments).*/i);
    if (pytestCollection) return [pytestCollection[0].trim()];

    const specIssue = line.match(/^(?:A quality specification is required.+|Invalid (?:quality specification|task|requirement id|acceptance criterion|pytest test selector).*|Specification requires version 1.+|Requirements need unique ids.+|Unknown integration suite.*|Unsafe test path.*|Test must be an existing file.+|Unsupported test kind.+)$/);
    if (specIssue) return [specIssue[0].trim()];

    const failed = line.match(/(?:FAILED\s+)([^\s]+::[^\s]+)(?:\s+-\s+(.+))?/);
    if (failed) return [failed[1] + (failed[2] ? ` - ${failed[2]}` : "")];

    const node = line.match(/^\s*(?:✖\s+|not ok \d+ - )(.+?)(?:\s+\([\d.]+m?s\))?$/);
    if (node && !/^(failing tests|tests \d+)/.test(node[1])) return [node[1]];

    const gate = line.match(/^\s*Configured gate failed:\s*(.+)$/);
    if (gate) return [gate[1]];

    if (/ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL/.test(line)) return [];

    const exception = line.match(/^\s*((?:AssertionError|TypeError|ReferenceError|Error|ImportError|ModuleNotFoundError|SyntaxError)(?:\s*\[[A-Z_]+\])?:.*|error:\s+.+)$/);
    if (exception) return [exception[1]];

    const diagnostic = line.match(/([\w./\\-]+\.(?:py|[cm]?[jt]sx?))(?::\d+(?::\d+)?|\(\d+,\d+\))\s*:?\s*(?:-\s*)?(.*(?:error|[A-Z]\d{3}).*)/i);
    if (diagnostic) return [`${diagnostic[1].replaceAll("\\", "/")}: ${diagnostic[2].replace(/\s+/g, " ").trim()}`];
    return [];
  });

  const isExitCodeWindowsCrash = typeof exitCode === "number" && (exitCode >= 0xC0000000 || exitCode <= -1000000000);
  const isOutputWindowsCrash = /(?:3221225794|3228369022|3221225477|3221225781|-1073741502|-1066598274|-1073741819|-1073741515|0xC0000142|0xC06D007E|0xC0000005|0xC0000135|DLL load failed while importing)/i.test(rawClean);
  const isWindowsProcessCrash = isExitCodeWindowsCrash || isOutputWindowsCrash;

  if (isExitCodeWindowsCrash && !rawDiagnostics.some((d) => d.startsWith("Windows process initialization failure:"))) {
    rawDiagnostics.push(`Windows process initialization failure: exit code ${exitCode}`);
  }
  const isPytestTask = task.testRunner === "pytest" || /pytest|test/i.test(task.label);
  if (isPytestTask && exitCode === 5 && !rawDiagnostics.some((d) => /collected 0 items|no tests ran/i.test(d))) {
    rawDiagnostics.push("pytest exit code 5: no tests collected");
  }
  if (isPytestTask && exitCode === 2 && !rawDiagnostics.length) {
    rawDiagnostics.push("pytest exit code 2: collection or execution interrupted");
  }
  if (isPytestTask && exitCode === 4 && !rawDiagnostics.length) {
    rawDiagnostics.push("pytest exit code 4: command line usage error");
  }

  const diagnostics = [...new Set(rawDiagnostics)].sort();
  let suggestion;
  if (task.label === "Quality specification" || /quality specification|Requirements need unique ids|Unknown integration suite|Unsafe test path|Test must be an existing file/i.test(rawClean)) {
    suggestion = "tmp/quality/task.json を現在の作業の受入条件と登録済みテスト（実在するテストファイルパスおよび正しいkind/selector）で作成・更新してください。";
  } else if (isWindowsProcessCrash) {
    suggestion = "Windowsプロセス初期化異常（STATUS_DLL_INIT_FAILED / 0xC0000142 等）または実行可能ファイルの起動失敗を検知した。仮想環境のlauncher、DLL配置、またはロック中の別プロセスを確認する。コードの期待値を変更しない。";
  } else if (status === "incomplete") {
    suggestion = "受入テストの成功件数を確認できないか、skip/xfail/todoが残っている。テスト選択と実行前提を確認し、未実施の条件を成功と扱わない。";
  } else if (status === "start_error") {
    suggestion = "実行ファイルと依存環境を確認し、lock済み環境を復旧する。コードの期待値を変更しない。";
  } else if (status === "timeout") {
    suggestion = "ログから停止した検査を特定し、所有するprocess・接続先・待ち条件を調べる。タイムアウト延長だけで解消扱いにしない。";
  } else if ((isPytestTask && exitCode === 5) || /collected 0 items|no tests ran in/i.test(rawClean)) {
    suggestion = "指定したテストが見つからないか、全テストがdeselectedされた（pytest終了コード5）。テストファイルパスとセレクター（-k / -m / ::test_name）を確認する。";
  } else if ((isPytestTask && exitCode === 4) || /^ERROR:\s*(?:usage:|file or directory not found|unrecognized arguments)/im.test(rawClean)) {
    suggestion = "pytestのコマンドライン引数エラーまたは対象ファイル未検出（終了コード4）。テストパス・マーカー式・設定ファイルを確認する。";
  } else if ((isPytestTask && exitCode === 2) || /ERROR collecting|ImportError|ModuleNotFoundError/i.test(rawClean)) {
    suggestion = "テスト収集時エラーまたはImportErrorが発生した（pytest終了コード2）。対象モジュール・テストファイルのimport経路と公開シンボル名を確認する。";
  } else if (task.testRunner === "configured-backend") {
    if (/environment_unavailable|connection refused|is the server running|not reachable/i.test(rawClean)) {
      if (/docker compose --env-file \.env\.postgres up -d --wait/i.test(rawClean)) {
        suggestion = "PostgreSQLへの接続が拒否された。ローカルDBコンテナを起動してください: docker compose --env-file .env.postgres up -d --wait";
      } else {
        suggestion = "PostgreSQLへ接続できない。readiness reasonを確認し、接続先・名前解決・network timeoutを切り分ける。リモート接続先へローカルDockerの案内を適用しない。";
      }
    } else {
      suggestion = "configured PostgreSQL readinessまたは実アプリのOS healthが失敗した。接続設定・schema revision・登録状態・port 3212を確認する。検査はDBを自動修復しない。";
    }
  } else if (/ENOTFOUND|EAI_AGAIN|PermissionError|EACCES|EPERM|certificate|SSL|ECONNREFUSED/i.test(rawClean)) {
    suggestion = "環境・接続・権限の失敗候補。chained exceptionを読み、sandbox内の失敗と製品不具合を切り分ける。権限が必要なら通常の承認経路を使い、検査の無効化や自動的な権限拡張で回避しない。";
  } else if (/\bF401\b/.test(rawClean)) {
    suggestion = "F401の指す未使用importを削除する。公開APIの再exportなら既存の公開契約に従って明示し、ファイル全体をlint除外しない。";
  } else if (/mypy|pyright|types/i.test(task.label)) {
    suggestion = "診断の型と公開署名を照合し、呼出側でNoneを絞り込むか契約に沿った引数へ修正する。cast・ignoreで隠す前に呼出経路を確認する。";
  } else if (/BROKEN CONTRACT|boundar|shared-boundaries|Features must use shared|UI library imports belong to shared|Forbidden (?:routing )?dependency|\b(?:LAY|DOM|APP|INF)\d{3}\b/i.test(rawClean) || /boundaries|architecture/i.test(task.label)) {
    suggestion = "レイヤー・コンテキスト境界または設計規約の違反。該当モジュールのimport方向・配置と参照ドキュメントを確認し、内側層から外側層への依存や境界バイパスを排除する。";
  } else if (/Would reformat:/i.test(rawClean) || /format/i.test(task.label)) {
    suggestion = "書式検査の不一致。対象ファイルにフォーマッタ（ruff format または biome format --write）を実行して書式を揃える。";
  } else if (/lint/i.test(task.label)) {
    suggestion = "該当ファイル・違反コードと設計規約を読み、担当範囲のimport・配置・書式を修正する。禁止規則を緩和しない。";
  } else {
    suggestion = "失敗したテストの期待値を受入条件と照合し、最小の再現で実装を修正する。仕様の根拠なくassertionやfixtureを弱めない。";
  }
  const identity = diagnostics.length ? createHash("sha256").update(JSON.stringify([task.label, status, diagnostics])).digest("hex") : null;
  return { identity, diagnostics, suggestion, docs, requirements: task.requirements ?? [] };
}
