import Link from "next/link";
import Kicker from "./ui/Kicker";

const CHIPS = [
  { label: "How did OTIF perform over the last year?", target: "#turn-1" },
  { label: "Why did OTIF drop in March 2026?", target: "#turn-2" },
  { label: "Was Abu Dhabi hit harder than Jebel Ali?", target: "#turn-4" },
];

// Section 1 — the problem. A recruiter should understand the pain this
// solves in ten seconds, before the product is even named.
export default function Hero() {
  return (
    <header
      id="problem"
      className="mx-auto w-full max-w-3xl scroll-mt-20 px-5 pb-20 pt-14 sm:px-8 sm:pb-24 sm:pt-20"
    >
      <div className="mb-8">
        <Kicker>
          Supply Chain Copilot · Mawarid Distribution — fictional, all data synthetic
        </Kicker>
      </div>

      <h1 className="type-hero text-ink">
        The answer is in the data.
        <br />
        Getting it out takes days.
      </h1>

      <p className="type-body mt-6 max-w-2xl text-slate sm:text-lg sm:leading-relaxed">
        When on-time-in-full slips at a distributor like Mawarid, the demand planner&rsquo;s
        question — <em>why?</em> — becomes a ticket, an Excel pull, and a meeting sometime next
        week. The real cost isn&rsquo;t the analyst&rsquo;s afternoon. It&rsquo;s the decisions
        taken on stale numbers in the meantime, and the questions that never get asked because
        asking is expensive.
      </p>

      <p className="type-body mt-5 max-w-2xl text-ink sm:text-lg sm:leading-relaxed">
        This project closes that gap: a conversational interface over the operational data,
        where every answer is computed by tested code and the system&rsquo;s reading of your
        question sits on screen — inspectable — between the question and the answer.
      </p>

      <div className="mt-10 flex flex-wrap gap-2.5">
        {CHIPS.map((chip) => (
          <Link
            key={chip.target}
            href={chip.target}
            className="rounded-full border border-line bg-raised px-4 py-2.5 font-display text-sm italic text-ink hover:border-accent hover:bg-accent-wash hover:text-accent-deep active:scale-[0.98]"
          >
            &ldquo;{chip.label}&rdquo;
          </Link>
        ))}
      </div>
    </header>
  );
}
