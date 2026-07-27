import Pipeline from "./Pipeline";
import Reveal from "./ui/Reveal";
import SectionHeading from "./ui/SectionHeading";

const CONSTRAINTS = [
  {
    title: "The model never writes SQL.",
    body: (
      <>
        It emits a typed QuerySpec: metric, window, dimension, filters, every field an
        enum from a fixed catalog. Free text never reaches the database, so a prompt
        injection that tries to smuggle SQL in has nowhere to land.{" "}
        <span className="text-ink font-medium">
          Injection is a type error, not a filtered attack.
        </span>{" "}
        There is no blocklist to slip past, because there is no string to slip it into.
      </>
    ),
  },
  {
    title: "The model never computes a number.",
    body: (
      <>
        Deterministic code compiles the spec to SQL and executes it read-only. When a
        change is decomposed into per-supplier or per-DC contributions, the parts must
        sum to the total delta exactly, to integer fils for additive metrics and within
        1e-9 relative tolerance for ratios. If the residual gate fails, the breakdown is
        withheld rather than fudged.
      </>
    ),
  },
  {
    title: "The model never shows an unverifiable number.",
    body: (
      <>
        The narration stage writes prose over placeholders bound to computed values. A
        render gate (R1–R4) rejects bare digits the code didn&rsquo;t produce,
        hallucinated placeholder paths, and spelled-out quantities. When the gate trips,
        the narration is withheld and the chart, which never depended on the model,
        stays.
      </>
    ),
  },
];

export default function Architecture() {
  return (
    <section id="how" aria-label="How it's designed" className="scroll-mt-20">
      <SectionHeading
        kicker="how I designed it"
        title="Seven stages. The model touches two."
        intro={
          <>
            The question flows left to right. The two model stages interpret and
            narrate; the five deterministic stages validate, compute, and gate. Each
            hand-off is a typed contract, so every failure is loud and attributable.
          </>
        }
      />

      <div className="mt-10">
        <Pipeline />
      </div>

      <div className="mt-10 grid gap-6 md:grid-cols-3">
        {CONSTRAINTS.map((c, i) => (
          <Reveal key={c.title} delay={i * 110} className="h-full">
            <div className="glass lift h-full rounded-xl p-5">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-ink">
                constraint {i + 1}
              </div>
              <h3 className="mt-2 font-display text-[1.05rem] font-semibold leading-snug text-ink">
                {c.title}
              </h3>
              <p className="mt-2.5 text-[13.5px] leading-relaxed text-ink-2">{c.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
