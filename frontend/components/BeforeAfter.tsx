import FlowNode from "./flow/FlowNode";
import Reveal from "./ui/Reveal";

const TODAY = ["question", "ticket", "analyst", "Excel", "meeting", "answer"];
const AFTER: { label: string; kind: "code" | "model" }[] = [
  { label: "question", kind: "code" },
  { label: "interpret", kind: "model" },
  { label: "answer", kind: "code" },
];

function Arrow({ delay }: { delay: number }) {
  return (
    <span
      aria-hidden="true"
      className="flow-link h-px w-2.5 shrink-0 bg-line-2 sm:w-3"
      style={{ "--flow-delay": `${delay}ms` } as React.CSSProperties}
    />
  );
}

/** The problem's punchline, in the pipeline's own visual language. */
export default function BeforeAfter() {
  return (
    <Reveal>
      <div data-before-after className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-line bg-panel/70 p-5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-3">
              today
            </span>
            <span className="font-mono text-[11px] text-ink-2">~2 days</span>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {TODAY.map((step, i) => (
              <span key={step} className="flex items-center gap-1.5">
                {i > 0 ? <Arrow delay={i * 130} /> : null}
                <FlowNode label={step} kind="code" compact delay={i * 130 + 60} />
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-accent-line bg-surface p-5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-ink">
              with the copilot
            </span>
            <span className="font-mono text-[11px] font-medium text-accent-ink">
              ~10 seconds
            </span>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {AFTER.map((step, i) => (
              <span key={step.label} className="flex items-center gap-2">
                {i > 0 ? <Arrow delay={i * 130 + 400} /> : null}
                <FlowNode
                  label={step.label}
                  kind={step.kind}
                  compact
                  delay={i * 130 + 460}
                />
              </span>
            ))}
          </div>
        </div>
      </div>
    </Reveal>
  );
}
