import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

const NEVERS = [
  { label: "never writes SQL", sub: "typed spec, enum fields" },
  { label: "never computes a number", sub: "tested code does the math" },
  { label: "never shows an unverifiable figure", sub: "render gate on every digit" },
];

export default function Approach() {
  return (
    <section id="approach" aria-label="How I approached it" className="scroll-mt-20">
      <SectionHeading
        kicker="how I approached it"
        title="Let the model read. Never let it count."
        intro={
          <>
            You ask in plain English. The system shows you exactly how it interpreted
            your question, as a structured spec you can read at a glance, before you
            trust any number. Then deterministic, tested code computes the answer
            against the data. The language model&rsquo;s only jobs are reading your
            question and phrasing the result.
          </>
        }
      />
      <Reveal delay={120} className="mt-8 flex flex-wrap gap-3">
        {NEVERS.map((n) => (
          <a
            key={n.label}
            href="#how"
            className="glass lift group rounded-lg px-4 py-3"
          >
            <div className="font-mono text-[12px] font-medium text-ink group-hover:text-accent-ink">
              {n.label}
            </div>
            <div className="mt-0.5 text-[11.5px] text-ink-3">{n.sub}</div>
          </a>
        ))}
      </Reveal>
    </section>
  );
}
