import CountUp from "./CountUp";
import Panel from "./ui/Panel";
import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

// Section 4 — the accuracy claim, with the same rigor the numbers were
// produced with: what was measured is explained before how it scored.

const SLICES = [
  { name: "Clean", definition: "straightforward questions a planner would actually ask" },
  {
    name: "Near-miss",
    definition:
      "questions built to trip metric confusion — fill rate vs in-full, stockout count vs days of cover",
  },
  { name: "Multi-turn", definition: "follow-ups that only make sense with the thread's context" },
  { name: "Adversarial", definition: "injection attempts, write requests, out-of-scope asks" },
];

const ROWS: Array<{
  slice: string;
  value: number;
  decimals: number;
  note: string;
}> = [
  { slice: "Clean questions", value: 96.7, decimals: 1, note: "stable across all four runs" },
  {
    slice: "Near-miss disambiguation",
    value: 93.3,
    decimals: 1,
    note: "range 86.7–93.3% across runs",
  },
  { slice: "Multi-turn follow-ups", value: 100, decimals: 0, note: "every run" },
  {
    slice: "Adversarial & injection",
    value: 100,
    decimals: 0,
    note: "correct refusals with correct reason codes",
  },
  {
    slice: "Unnecessary clarifications",
    value: 0,
    decimals: 0,
    note: "when a sensible default exists, it answers",
  },
];

export default function Measurement() {
  return (
    <section id="measurement" className="mx-auto w-full max-w-3xl scroll-mt-20 px-5 sm:px-8">
      <SectionHeading
        kicker="Measurement"
        title="Eighty questions, four independent runs."
        intro="The same golden set of 80 questions, run four times against the live model before deploy — $8.04 of tokens. Three release gates (adversarial, accuracy, over-clarification), all passed. The set is split into slices, each designed to break the system a different way:"
      />

      <dl className="flex max-w-2xl flex-col gap-1.5">
        {SLICES.map((s) => (
          <div key={s.name} className="flex gap-3 text-sm leading-relaxed">
            <dt className="w-24 shrink-0 font-mono text-[13px] text-accent-deep">{s.name}</dt>
            <dd className="text-slate">{s.definition}</dd>
          </div>
        ))}
      </dl>

      <Panel className="mt-8 overflow-hidden">
        {ROWS.map((row, i) => (
          <Reveal
            key={row.slice}
            delay={i * 80}
            className={`flex flex-wrap items-baseline gap-x-6 gap-y-1 px-5 py-4 ${
              i > 0 ? "border-t border-line" : ""
            }`}
          >
            <span className="w-56 shrink-0 text-sm font-medium text-ink">{row.slice}</span>
            <span className="font-display text-2xl font-semibold tracking-tight text-accent-deep">
              <CountUp value={row.value} decimals={row.decimals} suffix="%" />
            </span>
            <span className="text-sm text-slate">{row.note}</span>
          </Reveal>
        ))}
      </Panel>

      <Panel className="mt-4 px-5 py-4">
        <p className="type-kicker mb-3 text-negative">Known misses — disclosed, not buried</p>
        <ul className="flex flex-col gap-2.5 text-sm leading-relaxed text-slate">
          <li>
            <span className="font-mono text-xs text-faint">n14</span> — &ldquo;how much stock
            are we sitting on at AUH&rdquo; read AUH as the emirate, not the distribution
            center. Deterministic (failed every run); fixed after measurement by calibrating
            the entity resolver and listing DC members explicitly in the catalog.
          </li>
          <li>
            <span className="font-mono text-xs text-faint">n11</span> — &ldquo;how often were
            we out of beverages in Q2&rdquo; asked for a clarification instead of answering in
            one of the four runs. Intermittent; still open.
          </li>
        </ul>
      </Panel>
    </section>
  );
}
