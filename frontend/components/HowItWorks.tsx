import PipelineDiagram from "./PipelineDiagram";
import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

// Section 3 — architecture, framed for a COO and defensible to an
// engineer. The pipeline diagram is the section's visual signature;
// three prose claims below carry the argument.

const CLAIMS: Array<{ claim: string; body: string }> = [
  {
    claim: "The model never writes SQL.",
    body: "It emits a typed QuerySpec — metric, window, dimension, filters — that six validators check against the catalog before anything runs. That makes injection a type error rather than a filtered attack: an instruction smuggled into a question has nowhere to go, because free text never reaches the database.",
  },
  {
    claim: "The model never computes a number.",
    body: "A deterministic compiler turns the validated spec into parameterized SQL over a read-only database. Change decompositions carry a residual gate — member contributions must sum exactly to the total change, or the member breakdown is withheld and only the totals are shown.",
  },
  {
    claim: "The model never shows an unverifiable number.",
    body: "The narration passes a render gate: every figure in the paragraph must be a placeholder that traces to the computed result object. If the model writes a digit of its own, the paragraph is withheld — the chart and its numbers still render, because they never depended on the model in the first place.",
  },
];

export default function HowItWorks() {
  return (
    <div className="w-full border-y border-line bg-raised py-20 sm:py-24">
      <section id="how" className="mx-auto w-full max-w-5xl scroll-mt-20 px-5 sm:px-8">
        <SectionHeading kicker="How it works" title="Two model calls. Everything else is code." />

        <PipelineDiagram />

        <div className="mt-12 flex max-w-2xl flex-col gap-5">
          {CLAIMS.map((item, i) => (
            <Reveal key={item.claim} delay={i * 80}>
              <p className="type-body text-slate">
                <strong className="font-semibold text-ink">{item.claim}</strong> {item.body}
              </p>
            </Reveal>
          ))}
        </div>
      </section>
    </div>
  );
}
