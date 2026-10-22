import { REPO_URL, SECTIONS } from "@/lib/constants";

const linkClass =
  "inline-flex min-h-11 items-center rounded-control px-3 text-sm text-muted no-underline hover:text-fg";

// Plain anchors only. Internal navigation deliberately avoids next/link; see tests/pages.test.tsx.
export function SiteHeader() {
  return (
    <header className="border-b border-line bg-page">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-1 px-4 py-2 sm:px-6">
        <a
          href="/"
          className="inline-flex min-h-11 items-center gap-2 font-semibold tracking-tight text-fg no-underline"
        >
          <span
            aria-hidden="true"
            className="grid size-6 place-items-center rounded-[0.3rem] border border-line-strong font-mono text-xs text-brand-fg"
          >
            ds
          </span>
          DataShuddhi BD
        </a>
        <nav aria-label="Primary" className="-mx-3 flex flex-wrap items-center">
          {SECTIONS.map((section) => (
            <a key={section.id} href={`#${section.id}`} className={linkClass}>
              {section.label}
            </a>
          ))}
          <a href="/scan/" className={linkClass}>
            Browser scanner status
          </a>
          <a href={REPO_URL} className={`${linkClass} text-fg`}>
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}
