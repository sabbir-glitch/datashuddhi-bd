import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Reads the real tokens from globals.css and computes WCAG 2.x contrast ratios (the formula WCAG 2.2
// uses). This checks colour pairs only. It is not a manual accessibility review.
const css = readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8");

function tokens(block: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of block.matchAll(/--ds-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    out[m[1] as string] = m[2] as string;
  }
  return out;
}

const darkBlock = css.slice(css.indexOf(":root {"), css.indexOf(':root[data-theme="light"]'));
const lightBlock = css.slice(css.indexOf(':root[data-theme="light"]'), css.indexOf("html {"));
const themes = { dark: tokens(darkBlock), light: tokens(lightBlock) };

function luminance(hex: string): number {
  const channel = (i: number) => {
    const c = parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2);
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe.each(Object.entries(themes))("%s theme contrast", (_name, t) => {
  const backgrounds = ["page", "surface", "surface-2"];

  it("defines every token used", () => {
    for (const key of [
      "page",
      "surface",
      "surface-2",
      "border",
      "border-strong",
      "text",
      "text-muted",
      "brand",
      "brand-fg",
      "success",
      "warning",
      "danger",
    ]) {
      expect(t[key], key).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  it.each(["text", "text-muted", "brand-fg", "warning", "success", "danger"])(
    "%s text meets 4.5:1 on every surface",
    (fg) => {
      for (const bg of backgrounds) {
        expect(ratio(t[fg] as string, t[bg] as string), `${fg} on ${bg}`).toBeGreaterThanOrEqual(
          4.5,
        );
      }
    },
  );

  it("primary button label (page colour on brand) meets 4.5:1", () => {
    expect(ratio(t["page"] as string, t["brand"] as string)).toBeGreaterThanOrEqual(4.5);
  });

  it("control outlines and the focus ring meet 3:1 against the page", () => {
    expect(ratio(t["border-strong"] as string, t["page"] as string)).toBeGreaterThanOrEqual(3);
    expect(ratio(t["brand-fg"] as string, t["page"] as string)).toBeGreaterThanOrEqual(3);
    expect(ratio(t["brand-fg"] as string, t["surface"] as string)).toBeGreaterThanOrEqual(3);
  });
});
