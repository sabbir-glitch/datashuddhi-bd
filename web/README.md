# DataShuddhi BD web application (Phase 0 foundation)

> **Status: Phase 0 foundation only.** This directory contains a Next.js project skeleton, a home
> page and a `/scan` placeholder. **There is no scanner here.** The browser-based scanner is not
> implemented, nothing in this project reads, uploads or processes user files, and no results are
> shown.

The only working scanner in this repository is the Python command-line tool in `src/datashuddhi/`
(see the [root README](../README.md)). It detects _potential_ email addresses and Bangladeshi mobile
numbers, and masks matched values in its reports. It does not implement credential detection,
sanitisation or metadata removal, and neither does anything in `web/`.

A future browser scanner would be a separate TypeScript implementation. It must be tested against
the Python tool's fixtures and output semantics before its results are described as equivalent.

## Requirements

- Node.js **24.22.1** (see `.nvmrc`; `engines` allows Node 24.x) and npm 11.x.
- No global installs are required.

## Commands

Run these from the `web/` directory.

| Command                | What it does                                                           |
| ---------------------- | ---------------------------------------------------------------------- |
| `npm ci`               | Install exactly what `package-lock.json` records                       |
| `npm run dev`          | Start the Next.js development server (http://localhost:3000)           |
| `npm run lint`         | ESLint 10 (core, typescript-eslint and React Hooks rules)              |
| `npm run format:check` | Prettier check (`npm run format` rewrites files)                       |
| `npm run typecheck`    | `tsc --noEmit` with strict settings                                    |
| `npm test`             | Vitest: page markup smoke tests and audit-classifier tests             |
| `npm run build`        | Static production build; output goes to `out/`                         |
| `npm run audit:prod`   | production-only audit via `scripts/audit-check.mts` (the release gate) |
| `npm run audit:full`   | audit of all dependencies via `scripts/audit-check.mts`                |

Next.js collects anonymous usage telemetry for its own tooling by default. This project adds no
analytics, but you can opt out of Next.js's telemetry with the environment variable
`NEXT_TELEMETRY_DISABLED=1` (the CI workflow sets it).

## Static export and previewing

`next.config.ts` sets `output: "export"`, so `npm run build` writes plain files to `out/`
(`out/index.html`, `out/scan/index.html`, ...). There is **no Next.js server** in this mode, so do
**not** use `next start`; there is no `start` script.

Preview the exported files with any static HTTP server. With Python (already needed for the CLI),
from `web/`:

```powershell
py -m http.server 4173 --directory out
```

then open http://localhost:4173/. (`trailingSlash: true` makes `/scan/` resolve to
`out/scan/index.html` on a plain file server.)

**Static export versus server-rendered Next.js.** A static export cannot use middleware, route
handlers, server actions or Next.js `headers()` configuration. Security headers such as
`Content-Security-Policy` must be set at the hosting layer (for example the host's header
configuration). They are **not** provided by this project and none are configured yet.

**Internal links use plain `<a>` elements, not `next/link`.** With `output: "export"`, `next/link`
prefetches per-route React Server Component payload files such as `/scan/__next.scan.__PAGE__.txt`.
On Windows, Next.js 16.4.2 can write those files into nested folders instead of flat files, so the
prefetch requests return 404 ([vercel/next.js#85374](https://github.com/vercel/next.js/issues/85374);
a fix is proposed in [#99058](https://github.com/vercel/next.js/pull/99058), which was not merged when
this was written). Moving between the home page and `/scan/` is therefore a normal full-page
navigation. Revisit this when a Next.js release contains an upstream fix and it has been verified on
Windows. The static export still contains the payload `.txt` files; plain links never request them.

## Structure

```
web/
  package.json, package-lock.json   exact versions, committed lockfile
  tsconfig.json                     strict TypeScript (noUncheckedIndexedAccess on)
  next.config.ts                    static export, trailing slashes
  postcss.config.mjs                Tailwind CSS 4 PostCSS plugin
  eslint.config.mjs                 ESLint 10 flat config (see Linting)
  scripts/audit-check.mts           runs npm audit --json and classifies the result
  vitest.config.mts                 Node environment, "@" alias, automatic JSX
  .prettierrc.json, .prettierignore formatting rules (LF line endings)
  .gitattributes, .gitignore        LF in web/; build, test and env output ignored
  .nvmrc                            Node 24.22.1
  public/                           static assets (empty for now)
  src/app/                          layout, home page, /scan placeholder, global CSS tokens
  src/lib/constants.ts              repository URL
  tests/pages.test.tsx              page smoke tests
  tests/audit-check.test.ts         audit classifier tests (fixtures in tests/fixtures/)
```

## Design tokens

`src/app/globals.css` defines dark-first semantic tokens (page, surfaces, borders, text, brand,
success, warning, danger, radii, spacing) with a defined light set under
`:root[data-theme="light"]`. There is no theme switch yet. It uses a system font stack, so builds
never depend on an online font download. Keyboard focus styles and `prefers-reduced-motion` are
included.

**Not yet verified:** WCAG colour contrast, full keyboard testing and an accessibility review. These
are required before the real interface is approved in Phase 1.

## Privacy boundary

Phase 0 adds no backend routes, API endpoints, server actions, uploads, databases, authentication,
analytics, telemetry code, or persistence. The future scanner is intended to run in the browser
without uploading file contents; that is a design intention, not an implemented feature.

## Dependency decisions

| Package                                     | Version                 | Note                                                                                                                                                                                                   |
| ------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| next                                        | 16.4.2                  | npm `latest` when checked; peers `react ^19`, Node >= 20.9                                                                                                                                             |
| react, react-dom                            | 19.3.1                  | matching versions                                                                                                                                                                                      |
| tailwindcss, @tailwindcss/postcss           | 4.3.3                   | CSS-first config; the plugin brings its own `postcss`                                                                                                                                                  |
| typescript                                  | 6.0.3                   | **Not 7.0.2**: `typescript-eslint` 8.72.0 declares `typescript >=4.8.4 <6.1.0`, and `npm run lint` aborted with "typescript-eslint does not support TS 7.0" when 7.0.2 was installed in a scratch test |
| eslint                                      | 10.13.0                 | current major line; ESLint 9 is end-of-life (see Linting)                                                                                                                                              |
| @eslint/js                                  | 10.0.1                  | peer `eslint ^10.0.0`                                                                                                                                                                                  |
| typescript-eslint                           | 8.72.0                  | peers `eslint ^8.57 \|\| ^9 \|\| ^10`, `typescript >=4.8.4 <6.1.0`                                                                                                                                     |
| eslint-plugin-react-hooks                   | 7.1.1                   | peers include `eslint ^10.0.0`                                                                                                                                                                         |
| prettier                                    | 3.9.10                  |                                                                                                                                                                                                        |
| vitest                                      | 5.0.5                   | needs Node >= 22.12; no jsdom needed                                                                                                                                                                   |
| @types/node, @types/react, @types/react-dom | 24.19.2, 19.3.0, 19.3.0 | types matching the Node 24 baseline and React 19                                                                                                                                                       |

`motion`, `lucide-react`, Playwright and axe-core are **not** installed: Phase 0 has no animation,
icons or browser tests.

## Linting

**Selected:** ESLint 10.13.0 with `@eslint/js` recommended rules, `typescript-eslint` recommended
rules and the `eslint-plugin-react-hooks` flat recommended config (`eslint.config.mjs`).

**Why not ESLint 9:** npm marks `eslint@9.39.5` as "no longer supported", and the project owner
reports that the ESLint support page lists ESLint 9 as end-of-life from 6 August 2026. (This
workspace could not open eslint.org to confirm that page; the npm deprecation notice is the evidence
observed here.)

**Why not `eslint-config-next`:** its plugin set does not support ESLint 10. Package metadata read
from the npm registry:

- `eslint-plugin-react` 7.37.5: peer `eslint ^3 \|\| ... \|\| ^9.7` (no ESLint 10)
- `eslint-plugin-jsx-a11y` 6.10.2: peer `eslint ^3 \|\| ... \|\| ^9` (no ESLint 10)
- `eslint-plugin-import` (dependency of `eslint-config-next`): peer `eslint ... \|\| ^8 \|\| ^9` (no ESLint 10)
- `@next/eslint-plugin-next` 16.4.2 declares no ESLint peer, but depends on `fast-glob` 3.3.1, which
  is the path to the `braces` advisory below.

Forcing ESLint 10 onto those plugins would need peer overrides, which this project does not use.
`npm install` of the selected set printed no peer-dependency conflict, and `npm ls --all` reports no
invalid or missing required packages.

**Trade-offs (not hidden):** the Next.js-specific rules (`@next/next/*`) and `jsx-a11y` rules are not
enabled, so there is no lint check for Next.js-specific mistakes (for example `<img>` or `<a>` misuse)
or for static accessibility patterns. TypeScript strictness, Hooks rules and a real build still run.
Accessibility checks are planned for Phase 1 (for example axe-core in a browser test). Revisit
`eslint-config-next` when its plugins declare ESLint 10 support and no longer pull in an advisory.

**Check that lint is meaningful:** a scratch file with an unused variable, an explicit `any` and a
conditional `useState` call made `eslint` exit 1 with `@typescript-eslint/no-unused-vars`,
`@typescript-eslint/no-explicit-any` and `react-hooks/rules-of-hooks` errors. (The scratch file was
removed.)

## Install scripts

In the v1 package, `npm install` warned that `unrs-resolver@1.12.2` (a transitive development
dependency with a `postinstall` script) was not covered by npm 11's `allowScripts`. It came in as
`eslint-config-next` -> `eslint-import-resolver-typescript` -> `unrs-resolver`. Its script calls
`napi-postinstall` to check and prepare the package's native binding. `unrs-resolver` is **not** in
the current lockfile, and `npm ci` printed no install-script warning here. The only package left
with an install script flag in the lockfile is the macOS-only optional `fsevents`, which is not
installed on Linux or Windows. No scripts were approved. Whether `unrs-resolver` would have fallen
back to another implementation without its script was not tested, because the package is gone.
Windows installation was **not** tested; run the commands below on Windows 10 to confirm.

## Dependency audit

`npm run audit:prod` and `npm run audit:full` both run `scripts/audit-check.mts`, which calls
`npm audit --json` and reports one of three outcomes:

| Outcome            | Exit code | Meaning                                                                                                 |
| ------------------ | --------- | ------------------------------------------------------------------------------------------------------- |
| Clean              | 0         | the audit completed and reported no vulnerabilities                                                     |
| Vulnerabilities    | 1         | the audit completed; packages, severities and advisory URLs are printed                                 |
| Could not complete | 2         | registry, network or other failure, or output that could not be understood; **never** treated as a pass |

Observed on the committed lockfile (Linux, Node 24.22.1, npm 11.19.1): both audits exit 0 with "No
vulnerabilities reported". That is the result of those two runs on that date, not a guarantee about
the dependency tree. A new advisory makes both scripts fail; the audit-failure path was checked
against a refused registry connection (exit 2).

**The `braces` advisory from v1 is gone from the tree, not excepted.** v1 reported 5 high-severity,
development-only findings, all one chain: `eslint-config-next` -> `@next/eslint-plugin-next` 16.4.2 ->
`fast-glob` 3.3.1 -> `micromatch` 4.0.8 -> `braces` 3.0.3
([GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm), "braces vulnerable to
stack-exhaustion denial of service through deeply nested patterns", affecting `braces <= 3.0.3`).
`braces` 3.0.3 was the latest npm release, so no patched version existed. Removing
`eslint-config-next` removes the path: `npm ls braces fast-glob micromatch unrs-resolver` now shows
none of them, and the audit is clean. No override, downgrade or exception was used, so no review date
is needed. If `eslint-config-next` is added back, this advisory returns until `braces` is patched.

## Testing plan (later phases)

Phase 0 has Vitest tests only (page markup and the audit classifier). Browser tests and accessibility checks (for example Playwright
and axe-core) are planned for when there is real interface behaviour to test, and are deliberately
not installed yet.

## CI

`.github/workflows/web.yml` runs install (`npm ci`), lint, format check, type check, tests, static
build, the production audit (blocking) and the full audit (also blocking, always run so its result
is visible). It has **not** been run on GitHub; its steps were run locally in a separate checkout on
Linux.
