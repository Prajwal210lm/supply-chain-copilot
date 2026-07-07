import SectionHeading from "./ui/SectionHeading";

// Section 5 — scope in prose, not bullets. Two paragraphs: what it
// does, and what it won't do and why. Ends on the boundary with P3.
export default function ScopeHonesty() {
  return (
    <section id="scope" className="mx-auto w-full max-w-3xl scroll-mt-20 px-5 sm:px-8">
      <SectionHeading kicker="Scope & honesty" title="What it does — and won’t." />

      <div className="flex max-w-2xl flex-col gap-5 text-[15px] leading-relaxed text-slate sm:text-base">
        <p>
          The catalog covers eleven metrics across service, revenue, and inventory — OTIF to
          days of cover — cut five ways, with entity resolution that lands &ldquo;abu dhabi
          dc&rdquo;, &ldquo;AUH&rdquo;, and &ldquo;Abu Dhabi DC&rdquo; on the same warehouse.
          Conversations carry context, so a follow-up like &ldquo;how are we doing now?&rdquo;
          inherits the thread. Change decompositions attribute a move to the members of a
          dimension under an exact-residual gate: if the contributions don&rsquo;t sum to the
          total change, the breakdown is withheld rather than shown wrong.
        </p>
        <p>
          It won&rsquo;t let the model write SQL — a compiler does, with every user-derived
          value bound as a parameter. It won&rsquo;t forecast; it describes what happened,
          never what will. It won&rsquo;t answer outside the catalog — it refuses with a
          reason instead of guessing — and it can&rsquo;t write to the data, because the
          database connection is read-only by construction, not by policy. And it stops at a
          deliberate line: this is a query tool, not a root-cause engine. It decomposes a
          change; it does not adjudicate blame. That is{" "}
          <a
            href="https://otif-root-cause-engine.vercel.app"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent underline decoration-machine-line underline-offset-2 hover:text-accent-deep hover:decoration-accent"
          >
            Project 3&rsquo;s job
          </a>
          .
        </p>
      </div>

      <p className="type-mono mt-8 rounded-xl border border-machine-line bg-machine px-5 py-4 text-slate">
        All data is synthetic. Mawarid Distribution is fictional. Built to demonstrate
        architecture and methodology.
      </p>
    </section>
  );
}
