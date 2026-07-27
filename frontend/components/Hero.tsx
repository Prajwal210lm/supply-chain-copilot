import Kicker from "./ui/Kicker";
import Reveal from "./ui/Reveal";
import StatTile from "./ui/StatTile";
import { threadCostUsd, turns } from "@/lib/demo";

/** Real questions from the thread, jumping to the turns that answer them. */
const CHIPS = [
  { q: turns[0].question, target: "turn-1" },
  { q: turns[1].question, target: "turn-2" },
  { q: turns[3].question, target: "turn-4" },
];

export default function Hero() {
  return (
    <section aria-label="Introduction" className="relative overflow-hidden">
      {/* Animated mesh: four offset radial washes drifting on a 30s cycle.
          Pure CSS — no canvas, no JS, static under reduced motion. */}
      <div
        aria-hidden="true"
        className="mesh pointer-events-none absolute inset-x-0 top-0 h-140 origin-top"
      />
      <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-16 sm:px-8 sm:pb-20 sm:pt-24">
        <Reveal>
          <Kicker>supply chain copilot · mawarid distribution (fictional)</Kicker>
          <h1 className="mt-5 max-w-4xl font-display text-4xl font-semibold leading-[1.06] tracking-[-0.02em] text-ink sm:text-6xl">
            Ask your supply chain a question. Get a grounded answer in seconds, not days.
          </h1>
          <p className="mt-6 max-w-2xl text-[15.5px] leading-relaxed text-ink-2 sm:text-[17px]">
            At a GCC distributor like Mawarid, &ldquo;why did OTIF drop?&rdquo; becomes a
            ticket, an analyst&rsquo;s Excel pull, and a meeting next week. This copilot
            answers in one turn, shows you exactly how it read your question, and
            computes every number with tested code. The model never writes SQL and never
            does arithmetic.
          </p>
        </Reveal>

        <Reveal delay={120} className="mt-9 flex flex-wrap gap-3">
          <a
            href="#conversation"
            className="tap rounded-lg bg-accent-deep px-5 py-2.5 text-[13.5px] font-medium text-white shadow-sm"
          >
            Read the thread
          </a>
          <a
            href="#how"
            className="tap rounded-lg border border-line-2 bg-surface px-5 py-2.5 text-[13.5px] font-medium text-ink hover:border-accent-line hover:text-accent-ink"
          >
            How it&rsquo;s built
          </a>
        </Reveal>

        <Reveal delay={200} className="mt-12 grid max-w-3xl grid-cols-1 gap-6 sm:grid-cols-3">
          <StatTile
            value="96.7%"
            count={{ to: 96.7, decimals: 1, suffix: "%" }}
            label="spec accuracy, clean"
            sub="stable across four eval runs"
          />
          <StatTile
            value={`$${threadCostUsd.toFixed(2)}`}
            count={{ to: threadCostUsd, decimals: 2, prefix: "$" }}
            label="per 5-question thread"
            sub="measured pipeline cost"
          />
          <StatTile
            value="492"
            count={{ to: 492 }}
            label="automated tests"
            sub="hand-verified fixtures"
          />
        </Reveal>

        <Reveal delay={280} className="mt-12">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-3">
            asked in the demo below
          </div>
          <div className="mt-3 flex flex-wrap gap-2.5">
            {CHIPS.map((c) => (
              <a
                key={c.target}
                href={`#${c.target}`}
                className="tap group rounded-full border border-line-2 bg-surface px-4 py-2 text-[13px] text-ink-2 hover:border-accent-line hover:bg-accent-tint hover:text-accent-ink"
              >
                <span aria-hidden="true" className="mr-1.5 font-mono text-accent">
                  ❯
                </span>
                &ldquo;{c.q}&rdquo;
              </a>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
