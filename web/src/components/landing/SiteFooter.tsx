import { REPO_URL } from "@/lib/constants";

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-6 px-4 py-8 text-sm text-muted sm:px-6">
        <div className="max-w-xl">
          <p className="m-0 font-semibold text-fg">DataShuddhi BD</p>
          <p className="mt-2 mb-0">
            Independent, open-source project. Not affiliated with or endorsed by any government
            agency, bank, telecom operator or company. Status: pre-release (0.1.0.dev0). The Python
            command-line tool works; the browser scanner does not exist yet.
          </p>
        </div>
        <nav aria-label="Footer" className="-mx-3 flex flex-wrap">
          <a
            href={REPO_URL}
            className="inline-flex min-h-11 items-center px-3 text-muted underline hover:text-fg"
          >
            GitHub repository
          </a>
          <a
            href="/scan/"
            className="inline-flex min-h-11 items-center px-3 text-muted underline hover:text-fg"
          >
            Browser scanner status
          </a>
          <a
            href="#overview"
            className="inline-flex min-h-11 items-center px-3 text-muted underline hover:text-fg"
          >
            Back to top
          </a>
        </nav>
      </div>
    </footer>
  );
}
