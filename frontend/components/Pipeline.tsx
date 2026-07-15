import FlowNode from "./flow/FlowNode";
import Reveal from "./ui/Reveal";

type Stage = { label: string; sub: string; kind: "model" | "code" };

const STAGES: Stage[] = [
  { label: "Interpret", sub: "picks from a typed catalog", kind: "model" },
  { label: "Validate", sub: "V1–V6 checks", kind: "code" },
  { label: "Compile", sub: "templated SQL", kind: "code" },
  { label: "Execute", sub: "read-only DuckDB", kind: "code" },
  { label: "Decompose", sub: "exact-residual gate", kind: "code" },
  { label: "Narrate", sub: "writes over placeholders", kind: "model" },
  { label: "Render gate", sub: "R1–R4", kind: "code" },
];

const STEP = 130; // ms between assembly beats

/** The signature animated element: the pipeline assembles on scroll-in.
 *  Nodes appear in sequence, connectors draw between them. Horizontal on
 *  desktop, a vertical timeline on small screens. Reduced motion: static. */
export default function Pipeline() {
  return (
    <Reveal>
      <div data-pipeline className="rounded-xl border border-line bg-panel/60 px-4 py-6 sm:px-6">
        {/* desktop: one continuous row */}
        <div className="hidden items-center gap-2 md:flex">
          <FlowNode label="question" kind="terminal" delay={0} />
          {STAGES.map((s, i) => (
            <div key={s.label} className="flex flex-1 items-center gap-2">
              <span
                aria-hidden="true"
                className="flow-link h-px min-w-3 flex-1 bg-line-2"
                style={{ "--flow-delay": `${(2 * i + 1) * STEP}ms` } as React.CSSProperties}
              />
              <FlowNode label={s.label} sub={s.sub} kind={s.kind} delay={(2 * i + 2) * STEP} />
            </div>
          ))}
          <span
            aria-hidden="true"
            className="flow-link h-px min-w-3 flex-1 bg-line-2"
            style={{ "--flow-delay": `${15 * STEP}ms` } as React.CSSProperties}
          />
          <FlowNode label="answer" kind="terminal" delay={16 * STEP} />
        </div>

        {/* mobile: vertical timeline */}
        <div className="flex flex-col items-center gap-1.5 md:hidden">
          <FlowNode label="question" kind="terminal" delay={0} />
          {STAGES.map((s, i) => (
            <div key={s.label} className="flex w-full flex-col items-center gap-1.5">
              <span
                aria-hidden="true"
                className="flow-link-v h-5 w-px bg-line-2"
                style={{ "--flow-delay": `${(2 * i + 1) * STEP}ms` } as React.CSSProperties}
              />
              <div className="w-full max-w-60">
                <FlowNode label={s.label} sub={s.sub} kind={s.kind} delay={(2 * i + 2) * STEP} />
              </div>
            </div>
          ))}
          <span
            aria-hidden="true"
            className="flow-link-v h-5 w-px bg-line-2"
            style={{ "--flow-delay": `${15 * STEP}ms` } as React.CSSProperties}
          />
          <FlowNode label="answer" kind="terminal" delay={16 * STEP} />
        </div>

        <p className="mt-5 border-t border-line pt-3 text-center font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">
          two model stages · five deterministic stages · every number computed by code
        </p>
      </div>
    </Reveal>
  );
}
