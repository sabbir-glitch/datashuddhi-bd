import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "../src/app/page";
import { REPO_URL } from "../src/lib/constants";
import ScanPage from "../src/app/scan/page";

describe("home page", () => {
  const html = renderToStaticMarkup(<HomePage />);

  it("identifies the project and its only scanner", () => {
    expect(html).toContain("DataShuddhi BD");
    expect(html).toContain("local-first command-line tool");
    expect(html).toContain("this website cannot scan a file");
  });

  it("links to the repository and to the scan placeholder", () => {
    expect(html).toContain(`href="${REPO_URL}"`);
    expect(html).toContain('href="/scan/"');
  });

  it("does not claim capabilities that do not exist", () => {
    expect(html).toContain("Not implemented");
    for (const banned of [
      "Safe to Share",
      "Sanitized",
      "Threats Neutralized",
      "Metadata Removed",
    ]) {
      expect(html).not.toContain(banned);
    }
  });
});

describe("scan placeholder", () => {
  const html = renderToStaticMarkup(<ScanPage />);

  it("states that the scanner is under development and not available", () => {
    expect(html).toContain("Under development");
    expect(html).toContain("not available yet");
    expect(html).toContain("nothing on this site can scan a file");
  });

  it("offers no upload control and shows no results", () => {
    expect(html).not.toContain("<input");
    expect(html).not.toContain('type="file"');
    expect(html).not.toContain("<form");
    expect(html).not.toContain("findings");
  });
});

// Internal navigation uses plain anchors, not next/link. With `output: "export"`, next/link
// prefetches per-route React Server Component payload files (for example
// `/scan/__next.scan.__PAGE__.txt`). On Windows, Next.js 16.4.2 can write those files in nested
// folders instead (vercel/next.js#85374, fix proposed in vercel/next.js#99058, not merged when
// this was written), so prefetch requests return 404. Full-page navigation between the two static
// pages is acceptable in Phase 0. Revisit once an upstream fix is released and verified on Windows.
describe("internal navigation", () => {
  const sources = ["../src/app/page.tsx", "../src/app/scan/page.tsx"];

  it("does not use next/link in the static pages", () => {
    for (const relative of sources) {
      const source = readFileSync(new URL(relative, import.meta.url), "utf8");
      expect(source, relative).not.toMatch(/from\s+["']next\/link["']/);
    }
  });

  it("links the placeholder page back to the home page with a plain anchor", () => {
    expect(renderToStaticMarkup(<ScanPage />)).toContain('<a href="/">Back to the home page</a>');
  });
});
