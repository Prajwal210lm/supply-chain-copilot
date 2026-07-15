import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

const OBJECTIONS: { q: string; a: React.ReactNode }[] = [
  {
    q: "Why not just let the model write SQL?",
    a: (
      <>
        Because then the security and correctness story both collapse into &ldquo;we
        parse and filter strings and hope.&rdquo; A typed spec with enum fields can be
        validated completely in microseconds: unknown metric, incompatible dimension,
        malformed window are all rejected before anything touches the database. Free-form
        SQL can only be linted, never proven safe. The spec also decouples the model from
        the schema, so tables can be renamed or re-partitioned without retraining
        prompts, and it gives you the echo bar for free: a human-readable rendering of
        exactly what will be computed.
      </>
    ),
  },
  {
    q: "How do you know 96.7% is real and not cherry-picked?",
    a: (
      <>
        The golden set was written and frozen before the interpreter existed, so the bar
        predates the thing it measures. It ran four independent times ($8.04 of tokens),
        and the number held on every run. Accuracy is reported by slice rather than as
        one flattering average, the near-miss range (86.7&ndash;93.3%) is disclosed
        instead of smoothed, and the two misses are named: n14 and n11. The eval harness
        and all four result files are in the repo; anyone can rerun it.
      </>
    ),
  },
  {
    q: "What happens when the model gets the metric wrong?",
    a: (
      <>
        You see it before you trust it. The echo bar renders the interpretation, metric,
        window, cut, filters, before the number has any authority, so a wrong reading is
        visible rather than silent. This failure mode is measured on purpose: the
        near-miss slice exists to trip metric confusion, and it scores 93.3%. And because
        validation (V1&ndash;V6) rejects incompatible combinations outright, a
        misreading produces either a visible wrong spec or a refusal, never a
        quietly-wrong number.
      </>
    ),
  },
  {
    q: "Can a user exfiltrate data through prompt injection?",
    a: (
      <>
        The model&rsquo;s output is a typed spec checked against enums; free text never
        reaches SQL, so injection is a type error rather than a filtered attack. The
        database connection is read-only, so even a hypothetical malicious spec could
        only read what the catalog already exposes. The adversarial slice, 25 injection
        and write attempts, refused 25 of 25 on every one of the four runs, and that
        gate is deploy-blocking: one answered injection stops the release.
      </>
    ),
  },
  {
    q: "Why not use RAG instead of NL-to-SQL?",
    a: (
      <>
        Because the answer isn&rsquo;t written down anywhere. &ldquo;OTIF for March by
        supplier&rdquo; is an aggregation over ~50,000 order lines; there is no document
        to retrieve, and retrieval cannot sum. RAG is the right tool when the truth
        lives in prose, contracts, policies, incident reports. Here the truth lives in
        rows, and what you need is exact arithmetic with provenance. That is a compiler
        problem, not a search problem.
      </>
    ),
  },
];

export default function Objections() {
  return (
    <section id="objections" aria-label="Objections" className="scroll-mt-20">
      <SectionHeading
        kicker="before you ask"
        title="The five hardest questions, answered straight"
        intro="The questions a skeptical engineer or buyer should ask, with the answers the architecture actually supports."
      />

      <Reveal delay={100} className="mt-10">
        <div className="divide-y divide-line rounded-xl border border-line bg-surface">
          {OBJECTIONS.map((o) => (
            <details key={o.q} className="disclosure group px-5 sm:px-6">
              <summary className="flex items-center justify-between gap-4 py-4.5 sm:py-5">
                <h3 className="font-display text-[15.5px] font-semibold leading-snug text-ink sm:text-[17px]">
                  {o.q}
                </h3>
                <span
                  aria-hidden="true"
                  className="disclosure-mark grid h-6 w-6 shrink-0 place-items-center rounded-full border border-line-2 font-mono text-[13px] text-ink-2"
                >
                  +
                </span>
              </summary>
              <p className="max-w-3xl pb-5 text-[14px] leading-relaxed text-ink-2">{o.a}</p>
            </details>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
