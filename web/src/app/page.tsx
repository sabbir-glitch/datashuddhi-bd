import { REPO_URL } from "@/lib/constants";

export default function HomePage() {
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <p className="font-mono text-sm text-muted">Phase 0 foundation</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight">DataShuddhi BD</h1>
      <p className="mt-4 text-lg text-muted">
        An independent, open-source command-line tool that helps you find <em>potential</em>{" "}
        personal information in files before you share them. It reports syntactic matches for email
        addresses and Bangladeshi mobile numbers, with the matched values masked in its reports. A
        match is not proof that a value is real or belongs to a person.
      </p>

      <section
        aria-labelledby="status-heading"
        className="mt-10 rounded-card border border-line bg-surface p-6"
      >
        <h2 id="status-heading" className="text-xl font-semibold">
          What exists today
        </h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-muted">
          <li>
            The <strong className="text-fg">Python command-line tool</strong> is the only scanner.
            It runs locally and does not upload files.
          </li>
          <li>
            This website is an <strong className="text-fg">unfinished foundation</strong>. It does
            not scan anything.
          </li>
          <li>
            A <strong className="text-fg">browser-based scanner</strong> is planned but not built.
            When it exists, it will be tested against the command-line tool&apos;s fixtures before
            its results are described as equivalent.
          </li>
          <li>
            Credential detection, document sanitisation and metadata removal are{" "}
            <strong className="text-fg">not implemented</strong>.
          </li>
        </ul>
      </section>

      <nav aria-label="Primary" className="mt-8 flex flex-wrap gap-4">
        {/* Plain anchor on purpose: see the comment in tests/pages.test.tsx. */}
        <a
          href="/scan/"
          className="rounded-control bg-brand px-4 py-2 font-medium text-page no-underline"
        >
          Scanner status (placeholder)
        </a>
        <a
          href={REPO_URL}
          className="rounded-control border border-line px-4 py-2 font-medium text-fg no-underline"
        >
          GitHub repository
        </a>
      </nav>
    </main>
  );
}
