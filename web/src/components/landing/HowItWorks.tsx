const STEPS = [
  {
    title: "Run it locally",
    body: (
      <>
        Point the Python command-line tool at a supported file or folder on your own machine, for
        example{" "}
        <code className="font-mono text-sm text-fg">python -m datashuddhi scan .\notes.txt</code>.
        See the repository README for setup.
      </>
    ),
  },
  {
    title: "Review the masked report",
    body: (
      <>
        Each potential finding is listed with a rule ID, a location (path, line and column), a
        masked value and a plain-language explanation. Choose a console or JSON report.
      </>
    ),
  },
  {
    title: "Decide what to do yourself",
    body: (
      <>
        The tool only reports. It does <strong className="font-medium text-fg">not</strong> edit,
        redact or delete anything, and your original file is left as it was. You decide whether to
        change the file, or whether sharing it is authorised and necessary.
      </>
    ),
  },
] as const;

export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-heading" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <p className="font-mono text-sm text-muted">Current workflow · command line</p>
        <h2 id="how-heading" className="mt-2 text-3xl font-semibold tracking-tight">
          How it works
        </h2>
        <ol className="mt-8 grid list-none gap-4 p-0 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step.title} className="rounded-card border border-line bg-surface p-5">
              <span className="font-mono text-sm text-brand-fg">Step {index + 1}</span>
              <h3 className="mt-2 text-lg font-semibold">{step.title}</h3>
              <p className="mt-2 mb-0 text-muted">{step.body}</p>
            </li>
          ))}
        </ol>
        <p className="mt-6 max-w-3xl text-muted">
          This is the workflow of the command-line tool. It is not a browser feature: this website
          cannot scan a file.
        </p>
      </div>
    </section>
  );
}
