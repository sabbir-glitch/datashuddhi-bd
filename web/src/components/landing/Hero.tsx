import { REPO_URL } from "@/lib/constants";
import { Terminal } from "./Terminal";

const chip = "rounded-control border px-2.5 py-1 font-mono text-xs";

export function Hero() {
  return (
    <section id="overview" aria-labelledby="hero-heading" className="ds-grid-bg">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:py-20">
        <div>
          <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
            <li className={`${chip} border-line-strong text-muted`}>
              Python CLI · v0.1.0.dev0 · pre-release
            </li>
            <li className={`${chip} border-warning text-warning`}>
              Browser scanner: not built yet
            </li>
          </ul>
          <h1
            id="hero-heading"
            className="mt-5 text-4xl leading-[1.1] font-semibold tracking-tight text-balance sm:text-5xl"
          >
            Find potential personal data before you share.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-muted">
            DataShuddhi BD is an open-source, local-first command-line tool. It scans supported text
            files for <strong className="font-medium text-fg">potential email addresses</strong> and{" "}
            <strong className="font-medium text-fg">Bangladeshi mobile numbers</strong>, and reports
            what it finds with the values masked, so you can decide what to do before a file leaves
            your hands.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
            <a
              href={REPO_URL}
              className="inline-flex min-h-11 items-center rounded-control bg-brand px-5 font-medium text-page no-underline hover:brightness-110"
            >
              View the project on GitHub
            </a>
            <a href="/scan/" className="inline-flex min-h-11 items-center">
              Browser scanner status
              <span className="ml-2 text-sm text-warning">(not available yet)</span>
            </a>
          </div>
        </div>
        <Terminal />
      </div>
    </section>
  );
}
