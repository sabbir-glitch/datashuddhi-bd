import type { Metadata } from "next";

import { REPO_URL } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Scanner placeholder | DataShuddhi BD",
};

export default function ScanPage() {
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <p className="font-mono text-sm text-warning">Under development</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">
        Browser scanner: not available yet
      </h1>
      <p className="mt-4 text-muted">
        This page is a placeholder. The browser-based scanner is under development and has not been
        implemented, so nothing on this site can scan a file. There is no upload control here, no
        file is read or sent anywhere, and no results are shown.
      </p>
      <p className="mt-4 text-muted">
        To scan files today, use the Python command-line tool described in the{" "}
        <a href={REPO_URL}>project repository</a>.
      </p>
      <p className="mt-8">
        <a href="/">Back to the home page</a>
      </p>
    </main>
  );
}
