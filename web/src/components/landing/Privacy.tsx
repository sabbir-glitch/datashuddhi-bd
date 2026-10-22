import { RESPONSIBLE_USE_DOC_URL, THREAT_MODEL_DOC_URL } from "@/lib/constants";

export function Privacy() {
  return (
    <section id="privacy" aria-labelledby="privacy-heading" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <p className="font-mono text-sm text-muted">Local-first by design</p>
        <h2 id="privacy-heading" className="mt-2 text-3xl font-semibold tracking-tight">
          Privacy and local processing
        </h2>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-card border border-line bg-surface p-6">
            <h3 className="text-xl font-semibold">The command-line tool</h3>
            <ul className="mt-3 mb-0 list-disc space-y-3 pl-5 text-muted">
              <li>Scans files on your machine and does not upload them.</li>
              <li>Has no telemetry.</li>
              <li>Reads your files only; it never modifies the files it scans.</li>
              <li>Masks matched values in its reports. There is no option to reveal them.</li>
            </ul>
          </div>
          <div className="rounded-card border border-line bg-surface p-6">
            <h3 className="text-xl font-semibold">This website</h3>
            <ul className="mt-3 mb-0 list-disc space-y-3 pl-5 text-muted">
              <li>
                Does <strong className="font-medium text-fg">not</strong> accept, read or scan
                files. Browser-based scanning has not been implemented.
              </li>
              <li>
                Is served as static pages. It has no upload form, API, database, accounts, analytics
                or advertising scripts.
              </li>
              <li>
                Whoever hosts the pages may keep ordinary server logs. This project does not control
                that.
              </li>
            </ul>
          </div>
        </div>
        <p className="mt-6 max-w-3xl text-muted">
          These statements describe the current code, not a guarantee against every risk. The tool
          cannot prevent a data breach; it helps you notice some personal data before you share a
          file. See the <a href={THREAT_MODEL_DOC_URL}>threat model</a> and the{" "}
          <a href={RESPONSIBLE_USE_DOC_URL}>responsible-use guidance</a>.
        </p>
      </div>
    </section>
  );
}
