import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { classifyAudit, renderSummary } from "../scripts/audit-check.mts";

function fixture(name: string): string {
  return readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8");
}

// npm-audit-vulnerabilities.json and npm-audit-registry-failure.json are real `npm audit --json`
// outputs (the first from the Phase 0 v1 lockfile, the second from a refused registry connection).
// npm-audit-clean.json is a hand-written minimal clean report in the same format.
describe("classifyAudit", () => {
  it("accepts a completed audit with no vulnerabilities", () => {
    expect(classifyAudit(0, fixture("npm-audit-clean.json"))).toEqual({ kind: "clean" });
  });

  it("reports vulnerabilities with package, severity and advisory details", () => {
    const result = classifyAudit(1, fixture("npm-audit-vulnerabilities.json"));
    expect(result.kind).toBe("vulnerabilities");
    if (result.kind !== "vulnerabilities") return;
    expect(result.total).toBe(5);
    const braces = result.findings.find((f) => f.name === "braces");
    expect(braces?.severity).toBe("high");
    expect(braces?.direct).toBe(false);
    expect(braces?.advisories[0]?.url).toBe("https://github.com/advisories/GHSA-vfj7-8cjw-p6xm");
    expect(result.findings.find((f) => f.name === "eslint-config-next")?.direct).toBe(true);
  });

  it("does not turn a registry failure into advisories or a pass", () => {
    const result = classifyAudit(1, fixture("npm-audit-registry-failure.json"));
    expect(result.kind).toBe("failed");
    if (result.kind === "failed") expect(result.reason).toContain("ECONNREFUSED");
  });

  it("treats unusable output as a failure, not a pass", () => {
    expect(classifyAudit(0, "").kind).toBe("failed");
    expect(classifyAudit(0, "not json").kind).toBe("failed");
    expect(classifyAudit(0, "[]").kind).toBe("failed");
    expect(classifyAudit(0, "{}").kind).toBe("failed");
    expect(classifyAudit(null, fixture("npm-audit-clean.json")).kind).toBe("failed");
  });

  it("rejects contradictory exit codes and totals", () => {
    expect(classifyAudit(1, fixture("npm-audit-clean.json")).kind).toBe("failed");
    expect(classifyAudit(0, fixture("npm-audit-vulnerabilities.json")).kind).toBe("failed");
  });
});

describe("renderSummary", () => {
  it("never describes a failed audit as a pass", () => {
    const text = renderSummary("all dependencies", { kind: "failed", reason: "boom" });
    expect(text).toContain("could not be completed");
    expect(text).toContain("not a pass");
    expect(text).not.toContain("No vulnerabilities");
  });

  it("lists reported findings", () => {
    const result = classifyAudit(1, fixture("npm-audit-vulnerabilities.json"));
    const text = renderSummary("all dependencies", result);
    expect(text).toContain("5 vulnerabilities reported");
    expect(text).toContain("braces");
    expect(text).toContain("GHSA-vfj7-8cjw-p6xm");
  });
});
