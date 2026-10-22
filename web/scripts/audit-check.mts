// Runs `npm audit --json` and reports what the tool actually established.
//
// Exit codes:
//   0  the audit completed and reported no vulnerabilities
//   1  the audit completed and reported vulnerabilities
//   2  the audit could NOT complete (registry, network, authentication or other failure), or its
//      output could not be understood. This is never reported as "no vulnerabilities".
//
// Usage (through npm so that npm itself is found without a shell):
//   npm run audit:prod   ->  node scripts/audit-check.mts --omit=dev
//   npm run audit:full   ->  node scripts/audit-check.mts

import { spawnSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

export type Finding = {
  name: string;
  severity: string;
  direct: boolean;
  range: string;
  advisories: { title: string; url: string; range: string }[];
  via: string[];
};

export type AuditResult =
  | { kind: "clean" }
  | { kind: "vulnerabilities"; total: number; findings: Finding[] }
  | { kind: "failed"; reason: string };

type Json = Record<string, unknown>;

function isObject(value: unknown): value is Json {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Classify the exit status and standard output of `npm audit --json`. */
export function classifyAudit(status: number | null, stdout: string): AuditResult {
  if (status === null) {
    return {
      kind: "failed",
      reason: "the npm process did not exit normally (killed or not started)",
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return { kind: "failed", reason: "npm audit did not produce JSON output" };
  }
  if (!isObject(parsed)) {
    return { kind: "failed", reason: "npm audit JSON output was not an object" };
  }
  if (parsed["error"] !== undefined || typeof parsed["message"] === "string") {
    // npm reports a registry or network failure as {"message": "...", "error": {...}}; the
    // "error" fields can be empty, so the top-level message is the most useful text.
    const err = parsed["error"];
    const parts = [
      typeof parsed["message"] === "string" ? parsed["message"] : "",
      isObject(err) ? String(err["code"] ?? "") : "",
      isObject(err) ? String(err["summary"] ?? "") : "",
      isObject(err) ? String(err["detail"] ?? "") : "",
    ].filter((part) => part.length > 0);
    return {
      kind: "failed",
      reason: `npm audit reported an error (${parts.join("; ") || "no detail"})`,
    };
  }
  const metadata = parsed["metadata"];
  const counts = isObject(metadata) ? metadata["vulnerabilities"] : undefined;
  const total = isObject(counts) ? counts["total"] : undefined;
  if (typeof total !== "number") {
    return { kind: "failed", reason: "npm audit JSON had no vulnerability totals" };
  }
  if (total === 0) {
    return status === 0
      ? { kind: "clean" }
      : {
          kind: "failed",
          reason: `npm audit reported 0 vulnerabilities but exited with ${status}`,
        };
  }
  if (status === 0) {
    return {
      kind: "failed",
      reason: `npm audit reported ${total} vulnerabilities but exited with 0`,
    };
  }

  const findings: Finding[] = [];
  const vulnerabilities = isObject(parsed["vulnerabilities"]) ? parsed["vulnerabilities"] : {};
  for (const [name, raw] of Object.entries(vulnerabilities)) {
    if (!isObject(raw)) continue;
    const via = Array.isArray(raw["via"]) ? raw["via"] : [];
    findings.push({
      name,
      severity: String(raw["severity"] ?? "unknown"),
      direct: raw["isDirect"] === true,
      range: String(raw["range"] ?? ""),
      advisories: via.filter(isObject).map((v) => ({
        title: String(v["title"] ?? ""),
        url: String(v["url"] ?? ""),
        range: String(v["range"] ?? ""),
      })),
      via: via.filter((v): v is string => typeof v === "string"),
    });
  }
  return { kind: "vulnerabilities", total, findings };
}

export function renderSummary(label: string, result: AuditResult): string {
  const lines = [`### npm audit (${label})`];
  if (result.kind === "clean") {
    lines.push("Completed. No vulnerabilities reported.");
  } else if (result.kind === "failed") {
    lines.push(`**Audit could not be completed:** ${result.reason}. This is not a pass.`);
  } else {
    lines.push(`Completed. **${result.total} vulnerabilities reported:**`, "");
    for (const f of result.findings) {
      const how = f.direct ? "direct" : "transitive";
      lines.push(`- \`${f.name}\` (${f.severity}, ${how}, affected range \`${f.range}\`)`);
      for (const a of f.advisories) lines.push(`  - ${a.title} ${a.url} (range \`${a.range}\`)`);
      if (f.via.length > 0) lines.push(`  - via: ${f.via.join(", ")}`);
    }
  }
  return lines.join("\n") + "\n";
}

function main(): number {
  const extra = process.argv.slice(2);
  const label = extra.includes("--omit=dev") ? "production dependencies only" : "all dependencies";
  const npmCli = process.env["npm_execpath"];
  const spawned = npmCli
    ? spawnSync(process.execPath, [npmCli, "audit", "--json", ...extra], {
        encoding: "utf8",
        maxBuffer: 64 * 1024 * 1024,
      })
    : null;
  const result: AuditResult = spawned
    ? classifyAudit(spawned.status, spawned.stdout ?? "")
    : { kind: "failed", reason: "run this through `npm run` so that npm can be located" };

  const summary = renderSummary(label, result);
  process.stdout.write(summary);
  if (process.env["GITHUB_STEP_SUMMARY"]) {
    appendFileSync(process.env["GITHUB_STEP_SUMMARY"], summary + "\n");
  }
  if (process.env["GITHUB_ACTIONS"] && result.kind !== "clean") {
    const what =
      result.kind === "failed"
        ? `audit could not complete: ${result.reason}`
        : `${result.total} vulnerabilities reported`;
    process.stdout.write(`::error title=npm audit (${label})::${what}\n`);
  }
  return result.kind === "clean" ? 0 : result.kind === "vulnerabilities" ? 1 : 2;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = main();
}
