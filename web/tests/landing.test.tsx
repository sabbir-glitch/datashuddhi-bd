import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "../src/app/page";
import {
  LIMITATIONS_DOC_URL,
  REPO_URL,
  RESPONSIBLE_USE_DOC_URL,
  SECTIONS,
  THREAT_MODEL_DOC_URL,
} from "../src/lib/constants";

const html = renderToStaticMarkup(<HomePage />);
const text = html
  .replace(/<[^>]+>/g, " ")
  .replace(/&#x27;/g, "'")
  .replace(/&amp;/g, "&")
  .replace(/&gt;/g, ">")
  .replace(/\s+/g, " ");

const hrefs = [...html.matchAll(/<a\s[^>]*?href="([^"]*)"/g)].map((m) => m[1] as string);
const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1] as string);
const headings = [...html.matchAll(/<h([1-6])[\s>]/g)].map((m) => Number(m[1]));

describe("landing page content", () => {
  it("has one h1 with the product promise", () => {
    expect(html.match(/<h1[\s>]/g)).toHaveLength(1);
    expect(text).toContain("Find potential personal data before you share.");
  });

  it("explains the existing tool accurately", () => {
    expect(text).toContain("open-source, local-first command-line tool");
    expect(text).toContain("potential email addresses");
    expect(text).toContain("Bangladeshi mobile numbers");
    expect(text).toContain("masked");
    expect(text).toContain("not verified facts");
    expect(text).toContain("does not prove a file holds no personal data");
  });

  it("states what is and is not implemented with equal visibility", () => {
    expect(html).toContain(">Implemented<");
    expect(html).toContain(">Not implemented<");
    for (const limit of [
      "Credential or secret detection.",
      "Sanitisation or redaction.",
      "Metadata removal.",
      "Browser scanning.",
    ]) {
      expect(text).toContain(limit);
    }
  });

  it("says plainly that the website cannot scan files", () => {
    expect(text).toContain("this website cannot scan a file");
    expect(text).toContain("Browser-based scanning has not been implemented");
    expect(text).toContain("Browser scanner: not built yet");
    expect(text).toContain("(not available yet)");
  });

  it("never describes the CLI as modifying files", () => {
    expect(text).toContain("does not edit, redact or delete anything");
    expect(text).toContain("never modifies the files it scans");
  });

  it("does not make claims the project cannot support", () => {
    for (const banned of [
      "Safe to Share",
      "safe to share",
      "Sanitized",
      "Threats Neutralized",
      "Metadata Removed",
      "100%",
      "guaranteed",
      "military",
      "trusted by",
      "downloads",
      "testimonial",
    ]) {
      expect(text, banned).not.toContain(banned);
    }
  });
});

describe("illustrative terminal", () => {
  it("is labelled as illustrative and as not produced by the website", () => {
    expect(text).toContain("Illustrative output, not a live scan");
    expect(text).toContain("This website did not scan anything");
  });

  it("shows only masked synthetic values", () => {
    expect(text).toContain("a***@***.com");
    expect(text).toContain("*********78");
    expect(text).not.toMatch(/\b01[3-9]\d{8}\b/);
    expect(text).not.toMatch(/[A-Za-z0-9._%+-]+@(?!\*\*\*)[A-Za-z0-9.-]+\.[A-Za-z]{2,}/);
  });

  it("uses the real command-line syntax", () => {
    expect(html).toContain("python -m datashuddhi scan .\\example.txt");
  });
});

describe("navigation", () => {
  it("links every in-page anchor to an existing section id", () => {
    const fragments = hrefs.filter((href) => href.startsWith("#"));
    for (const section of SECTIONS) {
      expect(fragments).toContain(`#${section.id}`);
    }
    for (const fragment of fragments) {
      if (fragment === "#main") continue; // the skip link in layout.tsx, which is not rendered here
      expect(ids, fragment).toContain(fragment.slice(1));
    }
  });

  it("only uses destinations that exist", () => {
    const allowed = new Set<string>([
      "/",
      "/scan/",
      REPO_URL,
      LIMITATIONS_DOC_URL,
      RESPONSIBLE_USE_DOC_URL,
      THREAT_MODEL_DOC_URL,
      ...SECTIONS.map((s) => `#${s.id}`),
    ]);
    for (const href of hrefs) {
      expect(allowed.has(href), `unexpected link target: ${href}`).toBe(true);
    }
    expect(hrefs).toContain(REPO_URL);
    expect(hrefs).toContain("/scan/");
  });

  it("uses plain anchors and no client-side navigation", () => {
    const files = [
      "../src/app/page.tsx",
      "../src/components/landing/SiteHeader.tsx",
      "../src/components/landing/Hero.tsx",
      "../src/components/landing/FinalCta.tsx",
      "../src/components/landing/SiteFooter.tsx",
    ];
    for (const file of files) {
      const source = readFileSync(new URL(file, import.meta.url), "utf8");
      expect(source, file).not.toMatch(/from\s+["']next\/(link|navigation)["']/);
    }
  });
});

describe("page structure and safety", () => {
  it("has header, main, footer and labelled navigation landmarks", () => {
    expect(html).toContain("<header");
    expect(html.match(/<main[\s>]/g)).toHaveLength(1);
    expect(html).toContain("<footer");
    expect(html).toContain('aria-label="Primary"');
    expect(html).toContain('aria-label="Footer"');
  });

  it("has a logical heading hierarchy with no skipped levels", () => {
    expect(headings[0]).toBe(1);
    for (let i = 1; i < headings.length; i += 1) {
      expect((headings[i] as number) - (headings[i - 1] as number)).toBeLessThanOrEqual(1);
    }
    expect(headings.filter((level) => level === 2).length).toBeGreaterThanOrEqual(4);
  });

  it("labels every section by its heading", () => {
    const labelled = [...html.matchAll(/<section[^>]*aria-labelledby="([^"]+)"/g)].map(
      (m) => m[1] as string,
    );
    expect(labelled.length).toBeGreaterThanOrEqual(5);
    for (const id of labelled) expect(ids).toContain(id);
  });

  it("has unique ids", () => {
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("has no upload, scan or form controls and no scripts or remote resources", () => {
    for (const tag of [
      "<input",
      "<form",
      "<button",
      "<textarea",
      "<select",
      "<script",
      "<iframe",
    ]) {
      expect(html, tag).not.toContain(tag);
    }
    expect(html).not.toContain('type="file"');
    expect(html).not.toMatch(/\s(src|srcset)="https?:/);
    expect(html).not.toMatch(/<link[^>]+https?:/);
  });

  it("does not tell the visitor to upload or drop anything", () => {
    expect(text.toLowerCase()).not.toMatch(/drag|drop a file|select a file|choose a file/);
  });

  it("has link text that does not rely on generic wording", () => {
    const linkTexts = [...html.matchAll(/<a\s[^>]*>([\s\S]*?)<\/a>/g)].map((m) =>
      (m[1] as string)
        .replace(/<[^>]+>/g, "")
        .trim()
        .toLowerCase(),
    );
    for (const generic of ["click here", "here", "read more", "more", "link"]) {
      expect(linkTexts).not.toContain(generic);
    }
    for (const label of linkTexts) expect(label.length).toBeGreaterThan(0);
  });
});
