import CountUp from "./ui/CountUp";
import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

const SLICES = [
  {
    name: "Clean",
    count: "30 questions",
    desc: "Straightforward planner questions. “How did OTIF perform over the last year?” The baseline the tool must not miss.",
  },
  {
    name: "Near-miss",
    count: "15 questions",
    desc: "Built to trip metric confusion: fill rate vs in-full, stockout count vs days of cover. The slice that separates reading from pattern-matching.",
  },
  {
    name: "Adversarial",
    count: "25 questions",
    desc: "Prompt injections, write requests, out-of-scope traps. The tool must refuse every single one; anything less blocks the release.",
  },
];

const STATS: { value: number; decimals: number; suffix: string; label: string; note: string }[] = [
  { value: 96.7, decimals: 1, suffix: "%", label: "clean", note: "stable across all four runs" },
  { value: 93.3, decimals: 1, suffix: "%", label: "near-miss", note: "86.7–93.3% across runs; n11 is intermittent" },
  { value: 100, decimals: 0, suffix: "%", label: "adversarial refusal", note: "25 of 25, every run — deploy-blocking" },
  { value: 0, decimals: 0, suffix: "%", label: "unnecessary clarifications", note: "no clean question was answered with a question" },
];

const MISSES = [
  {
    id: "n14",
    tag: "fixed",
    text: "“AUH” read as the emirate instead of the DC. Deterministic, caught by the near-miss slice, fixed with a disambiguation rule in the catalog.",
  },
  {
    id: "n11",
    tag: "intermittent",
    text: "Occasionally asks a clarifying question where a direct answer was expected. Disclosed rather than averaged away; it is why near-miss ranges to 86.7%.",
  },
];

export default function Measurement() {
  return (
    <section id="measurement" aria-label="The measurement" className="scroll-mt-20">
      <SectionHeading
        kicker="the measurement"
        title="Measured before it shipped, misses disclosed by name"
        intro={
          <>
            An 80-question golden set, written and frozen before the interpreter
            existed, run four independent times against the live model: $8.04 of tokens.
            Three release gates (adversarial refusal, accuracy, over-clarification), all
            passed before deploy. The set is sliced so each slice breaks the system a
            different way; the three below carry the argument, alongside multi-turn
            follow-ups (100%).
          </>
        }
      />

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {SLICES.map((s, i) => (
          <Reveal key={s.name} delay={i * 110}>
            <div className="h-full rounded-xl border border-line bg-surface p-5">
              <div className="flex items-baseline justify-between">
                <h3 className="font-display text-base font-semibold text-ink">{s.name}</h3>
                <span className="font-mono text-[10.5px] text-ink-3">{s.count}</span>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-2">{s.desc}</p>
            </div>
          </Reveal>
        ))}
      </div>

      <Reveal delay={120} className="mt-8">
        <div className="grid grid-cols-2 gap-x-6 gap-y-8 rounded-xl border border-line bg-panel/70 p-6 sm:p-8 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="font-display text-4xl font-semibold tracking-tight text-ink sm:text-[2.6rem]">
                <CountUp value={s.value} decimals={s.decimals} suffix={s.suffix} />
              </div>
              <div className="mt-1.5 font-mono text-[10.5px] uppercase tracking-[0.16em] text-ink-2">
                {s.label}
              </div>
              <div className="mt-1 text-[12px] leading-snug text-ink-3">{s.note}</div>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal delay={160} className="mt-8">
        <div className="rounded-xl border border-line bg-surface p-5 sm:p-6">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-highlight">
            known misses, by name
          </div>
          <ul className="mt-4 space-y-4">
            {MISSES.map((m) => (
              <li key={m.id} className="flex flex-col gap-1.5 sm:flex-row sm:items-baseline sm:gap-4">
                <span className="flex shrink-0 items-baseline gap-2 sm:w-36">
                  <span className="font-mono text-[13px] font-medium text-ink">{m.id}</span>
                  <span className="rounded-full bg-highlight-tint px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-highlight">
                    {m.tag}
                  </span>
                </span>
                <p className="text-[13.5px] leading-relaxed text-ink-2">{m.text}</p>
              </li>
            ))}
          </ul>
          <p className="mt-5 border-t border-line pt-4 text-[13px] italic leading-relaxed text-ink-3">
            100% adversarial refusal is a gate, not a target: one answered injection
            stops the release.
          </p>
        </div>
      </Reveal>
    </section>
  );
}
