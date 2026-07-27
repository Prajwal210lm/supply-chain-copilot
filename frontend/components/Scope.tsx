import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

const CARDS = [
  {
    title: "What's synthetic",
    body: "Everything. Mawarid Distribution is fictional; two years of orders, shipments, and inventory are generated with a fixed seed, with incidents planted so the answers are checkable. 400 SKUs rather than 9,000 — but the model never sees a row, only the catalog, so the architecture is indifferent to scale.",
  },
  {
    title: "What was deliberately left out",
    body: "Forecasting, RAG over documents, and causal attribution. The last one matters: deciding which team is to blame for a failure is a different machine (that is Project 3's job). Leaving them out kept every remaining claim checkable.",
  },
  {
    title: "What transfers to a real engagement",
    body: "The QuerySpec pattern — model selects from a catalog, deterministic code does the rest — fits any domain with a fixed schema: procurement, logistics, warehouse ops, finance. So does the measurement frame: a frozen golden set, sliced accuracy, deploy-blocking gates, misses disclosed by name.",
  },
];

export default function Scope() {
  return (
    <section id="scope" aria-label="Scope and honesty" className="scroll-mt-20">
      <SectionHeading
        kicker="scope & honesty"
        title="What this is, and what it deliberately is not"
      />

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {CARDS.map((c, i) => (
          <Reveal key={c.title} delay={i * 110}>
            <div className="glass lift h-full rounded-xl p-5">
              <h3 className="font-display text-base font-semibold text-ink">{c.title}</h3>
              <p className="mt-2.5 text-[13.5px] leading-relaxed text-ink-2">{c.body}</p>
            </div>
          </Reveal>
        ))}
      </div>

      <Reveal delay={140} className="mt-8">
        <figure className="rounded-xl border-l-2 border-accent bg-accent-tint/50 px-6 py-5">
          <blockquote className="max-w-2xl font-display text-lg font-medium leading-snug text-ink sm:text-xl">
            &ldquo;This is a query tool, not a root-cause engine. It decomposes a change;
            it does not adjudicate blame.&rdquo;
          </blockquote>
          <figcaption className="mt-2 font-mono text-[10.5px] uppercase tracking-[0.16em] text-ink-3">
            the boundary with project 3
          </figcaption>
        </figure>
      </Reveal>
    </section>
  );
}
