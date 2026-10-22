import { REPO_URL } from "@/lib/constants";

export function FinalCta() {
  return (
    <section aria-labelledby="cta-heading" className="border-t border-line bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 id="cta-heading" className="text-3xl font-semibold tracking-tight">
          Read the code, run the tool
        </h2>
        <p className="mt-3 max-w-2xl text-muted">
          DataShuddhi BD is pre-release and developed in the open. The source, documentation and
          issue tracker are in the GitHub repository. There is no packaged download yet.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
          <a
            href={REPO_URL}
            className="inline-flex min-h-11 items-center rounded-control bg-brand px-5 font-medium text-page no-underline hover:brightness-110"
          >
            Open the GitHub repository
          </a>
          <a href="/scan/" className="inline-flex min-h-11 items-center">
            Browser scanner status
          </a>
        </div>
      </div>
    </section>
  );
}
