import { LIMITATIONS_DOC_URL } from "@/lib/constants";

const tag = "rounded-control border px-2 py-0.5 font-mono text-xs font-semibold";

export function DetectionScope() {
  return (
    <section id="detection-scope" aria-labelledby="scope-heading" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <p className="font-mono text-sm text-muted">Version 0.1.0.dev0</p>
        <h2 id="scope-heading" className="mt-2 text-3xl font-semibold tracking-tight">
          Detection scope
        </h2>
        <p className="mt-3 max-w-3xl text-muted">
          What the tool does today, and what it does not. Both lists matter.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-card border border-line bg-surface p-6">
            <span className={`${tag} border-brand-fg text-brand-fg`}>Implemented</span>
            <h3 className="mt-3 text-xl font-semibold">Detects potential</h3>
            <ul className="mt-3 mb-0 list-disc space-y-3 pl-5 text-muted">
              <li>
                <strong className="font-medium text-fg">Email addresses.</strong> ASCII addresses
                only. Shown masked, for example{" "}
                <code className="font-mono text-sm text-fg">a***@***.com</code>.
              </li>
              <li>
                <strong className="font-medium text-fg">Bangladeshi mobile numbers.</strong>{" "}
                Operator prefixes 013 to 019 in{" "}
                <code className="font-mono text-sm text-fg">01…</code>,{" "}
                <code className="font-mono text-sm text-fg">+880…</code> and{" "}
                <code className="font-mono text-sm text-fg">00880…</code> forms, with ASCII or
                Bengali digits. Shown masked, for example{" "}
                <code className="font-mono text-sm text-fg">*********78</code>.
              </li>
              <li>
                <strong className="font-medium text-fg">In these file types:</strong>{" "}
                <code className="font-mono text-sm text-fg">
                  .txt .csv .json .log .ini .toml .yaml .yml .env
                </code>{" "}
                and <code className="font-mono text-sm text-fg">.env.*</code>. Other types are
                skipped.
              </li>
            </ul>
          </div>

          <div className="rounded-card border border-line bg-surface p-6">
            <span className={`${tag} border-warning text-warning`}>Not implemented</span>
            <h3 className="mt-3 text-xl font-semibold">Does not do</h3>
            <ul className="mt-3 mb-0 list-disc space-y-3 pl-5 text-muted">
              <li>
                <strong className="font-medium text-fg">Credential or secret detection.</strong>{" "}
                Passwords, API keys and tokens are not detected. Use a dedicated secret scanner.
              </li>
              <li>
                <strong className="font-medium text-fg">Sanitisation or redaction.</strong> It never
                edits your file or writes a cleaned copy.
              </li>
              <li>
                <strong className="font-medium text-fg">Metadata removal.</strong>
              </li>
              <li>
                <strong className="font-medium text-fg">Browser scanning.</strong> The website
                cannot scan a file.
              </li>
              <li>
                <strong className="font-medium text-fg">Everything else.</strong> Names, addresses,
                ID numbers and images are not detected, and a report with no findings does not prove
                a file holds no personal data.
              </li>
            </ul>
          </div>
        </div>

        <p className="mt-6 max-w-3xl text-muted">
          Findings are pattern matches, not verified facts: a phone-shaped order number can be
          flagged, and a flagged address may not belong to a person. Read the{" "}
          <a href={LIMITATIONS_DOC_URL}>detection limitations</a> before relying on a result.
        </p>
      </div>
    </section>
  );
}
