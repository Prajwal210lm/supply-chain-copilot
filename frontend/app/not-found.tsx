import Link from "next/link";

/** Themed 404: rendered in the machine's own refusal voice. */
export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center bg-paper px-5">
      <div className="w-full max-w-lg">
        <div className="rounded-lg border border-line border-l-2 border-l-highlight bg-panel">
          <div className="border-b border-line px-4 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-highlight">
              interpreted as · refusal
            </span>
          </div>
          <div className="px-4 py-4">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
              <div>
                <dt className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-ink-3">
                  route
                </dt>
                <dd className="mt-1 font-mono text-[12.5px] text-ink">not in catalog</dd>
              </div>
              <div>
                <dt className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-ink-3">
                  status
                </dt>
                <dd className="mt-1 font-mono text-[12.5px] text-ink">404</dd>
              </div>
            </dl>
          </div>
        </div>
        <h1 className="mt-8 font-display text-3xl font-semibold tracking-tight text-ink">
          This query returned no results.
        </h1>
        <p className="mt-3 text-[14.5px] leading-relaxed text-ink-2">
          The page you asked for isn&rsquo;t in the catalog. Like every refusal here,
          this one is explicit rather than improvised.
        </p>
        <Link
          href="/"
          className="mt-7 inline-block rounded-lg bg-accent-deep px-5 py-2.5 text-[13.5px] font-medium text-white shadow-sm transition-transform duration-200 motion-reduce:transition-none hover:-translate-y-px motion-reduce:hover:translate-y-0"
        >
          Back to the copilot
        </Link>
      </div>
    </main>
  );
}
