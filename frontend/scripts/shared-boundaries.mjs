import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const slash = (path) => path.replaceAll("\\", "/");
const uiLibrary = /^(?:@react-spectrum\/|react-aria-components(?:\/|$))/;

/** Resolve imports as TypeScript does, including type-only imports and barrels. */
export function checkSharedBoundaries(root = frontendRoot) {
  const configPath = resolve(root, "tsconfig.json");
  const config = ts.readConfigFile(configPath, ts.sys.readFile);
  if (config.error)
    throw new Error(ts.flattenDiagnosticMessageText(config.error.messageText, "\n"));
  const { options } = ts.parseJsonConfigFileContent(config.config, ts.sys, root);
  const cache = ts.createModuleResolutionCache(root, (path) => path, options);
  const graph = new Map();
  const routing = new Set();
  const issues = [];
  const local = (path) => slash(relative(root, path));
  function visit(file) {
    if (graph.has(file)) return;
    const edges = [];
    graph.set(file, edges);
    if (file.endsWith(".json")) return;
    const source = ts.createSourceFile(
      file,
      readFileSync(file, "utf8"),
      ts.ScriptTarget.Latest,
      true,
    );
    function add(specifier, node) {
      const owner = local(file);
      const line = source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1;
      if (
        !owner.startsWith("shared/ui/") &&
        !owner.startsWith("shared/providers/") &&
        uiLibrary.test(specifier)
      ) {
        issues.push(
          `${owner}:${line}: UI library imports belong to shared/ui (${specifier})`,
        );
      }
      if (specifier === "next/navigation") routing.add(file);
      const target = ts.resolveModuleName(
        specifier,
        file,
        options,
        ts.sys,
        cache,
      ).resolvedModule;
      if (target?.isExternalLibraryImport) return;
      const fallback = specifier.startsWith("@/")
        ? resolve(root, specifier.slice(2))
        : specifier.startsWith(".")
          ? resolve(dirname(file), specifier)
          : undefined;
      const path = target ? resolve(target.resolvedFileName) : fallback;
      if (
        path &&
        /^(features|app)\//.test(owner) &&
        local(path).startsWith("shared/ui/")
      ) {
        issues.push(
          `${owner}:${line}: Features must use shared/component, not shared/ui (${specifier})`,
        );
      }
      if (!path || !/\.(?:[cm]?[jt]sx?|json|css)$/.test(path) || !existsSync(path))
        return;
      edges.push(path);
      visit(path);
    }
    function walk(node) {
      if (
        (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
        node.moduleSpecifier &&
        ts.isStringLiteral(node.moduleSpecifier)
      ) {
        add(node.moduleSpecifier.text, node);
      } else if (
        ts.isImportEqualsDeclaration(node) &&
        ts.isExternalModuleReference(node.moduleReference) &&
        node.moduleReference.expression &&
        ts.isStringLiteral(node.moduleReference.expression)
      ) {
        add(node.moduleReference.expression.text, node);
      } else if (
        ts.isImportTypeNode(node) &&
        ts.isLiteralTypeNode(node.argument) &&
        ts.isStringLiteral(node.argument.literal)
      ) {
        add(node.argument.literal.text, node);
      } else if (
        ts.isCallExpression(node) &&
        (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
          (ts.isIdentifier(node.expression) && node.expression.text === "require"))
      ) {
        const argument = node.arguments[0];
        if (argument && ts.isStringLiteralLike(argument)) add(argument.text, node);
        else if (local(file).startsWith("shared/"))
          issues.push(`${local(file)}: shared imports must be statically resolvable`);
      }
      ts.forEachChild(node, walk);
    }
    if (file.endsWith(".css")) {
      for (const match of readFileSync(file, "utf8").matchAll(
        /@import\s+(?:url\()?['"]([^'"]+)['"]/g,
      ))
        add(match[1], source);
    } else walk(source);
  }
  function collect(directory) {
    if (!existsSync(directory)) return;
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) collect(path);
      else if (
        /\.[cm]?[jt]sx?$/.test(entry.name) &&
        !/\.test\.[cm]?[jt]sx?$/.test(entry.name)
      )
        visit(path);
    }
  }
  for (const area of ["shared", "features", "app", "styles"])
    collect(resolve(root, area));
  for (const origin of graph.keys()) {
    const owner = local(origin);
    if (/^(features|app)\//.test(owner)) {
      const seen = new Set([origin]);
      const queue = [[origin, [owner]]];
      while (queue.length) {
        const [file, chain] = queue.shift();
        for (const target of graph.get(file) ?? []) {
          if (seen.has(target)) continue;
          seen.add(target);
          const name = local(target);
          // A component is the intentional adaptation boundary, not a bypass.
          if (name.startsWith("shared/component/")) continue;
          const path = [...chain, name];
          if (name.startsWith("shared/ui/"))
            issues.push(`Feature UI bypass: ${path.join(" -> ")}`);
          queue.push([target, path]);
        }
      }
    }
    if (!owner.startsWith("shared/")) continue;
    const seen = new Set([origin]);
    const queue = [[origin, [owner]]];
    while (queue.length) {
      const [file, chain] = queue.shift();
      if (/^shared\/(ui|component)\//.test(owner) && routing.has(file)) {
        issues.push(
          `Forbidden routing dependency: ${chain.join(" -> ")} -> next/navigation; routing belongs to the calling feature`,
        );
      }
      for (const target of graph.get(file) ?? []) {
        if (seen.has(target)) continue;
        seen.add(target);
        const name = local(target);
        const path = [...chain, name];
        if (
          /^(features|app)\//.test(name) ||
          (/^shared\/(ui|component)\//.test(owner) && name.startsWith("shared/api/")) ||
          (owner.startsWith("shared/ui/") && name.startsWith("shared/component/"))
        ) {
          issues.push(`Forbidden dependency: ${path.join(" -> ")}`);
        }
        queue.push([target, path]);
      }
    }
  }
  return [...new Set(issues)];
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const issues = checkSharedBoundaries();
  for (const issue of issues) console.error(issue);
  console.log(`Shared boundary violations: ${issues.length}`);
  process.exitCode = issues.length ? 1 : 0;
}
