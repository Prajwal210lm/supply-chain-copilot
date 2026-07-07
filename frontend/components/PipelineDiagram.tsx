"use client";

import { useEffect, useRef, useState } from "react";

// The architecture, drawn: seven stages, two of them the model (accent,
// white text), five deterministic code (sunken, ink). Assembles once on
// scroll-in — nodes appear in pipeline order, then the connectors draw —
// data flowing left to right (top to bottom on mobile). Reduced-motion
// renders everything instantly via the CSS opt-out in globals.css.

const STAGES: Array<{ name: string; sub: string; model: boolean }> = [
  { name: "question", sub: "plain English", model: false },
  { name: "interpret", sub: "model · emits a typed spec", model: true },
  { name: "validate", sub: "six checks, V1–V6", model: false },
  { name: "compile", sub: "parameterized SQL", model: false },
  { name: "execute", sub: "read-only database", model: false },
  { name: "narrate", sub: "model · prose from the result", model: true },
  { name: "render gate", sub: "every number traced", model: false },
];

const NODE_STEP_MS = 140;

export default function PipelineDiagram() {
  const ref = useRef<HTMLDivElement>(null);
  const [assembled, setAssembled] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setAssembled(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={assembled ? "pipe-assembled" : ""}>
      <div className="flex flex-col items-stretch sm:flex-row sm:flex-wrap sm:items-center sm:gap-y-4">
        {STAGES.map((stage, i) => (
          <div key={stage.name} className="flex flex-col items-center sm:flex-row">
            <div
              className={`pipe-node flex w-full flex-col rounded-lg border px-4 py-3 sm:w-auto ${
                stage.model
                  ? "border-accent bg-accent"
                  : "border-line bg-sunken"
              }`}
              style={{ "--pipe-delay": `${i * NODE_STEP_MS}ms` } as React.CSSProperties}
            >
              <span
                className={`font-mono text-sm font-medium ${
                  stage.model ? "text-white" : "text-ink"
                }`}
              >
                {stage.name}
              </span>
              <span
                className={`mt-0.5 font-mono text-[10px] leading-tight ${
                  stage.model ? "text-white/75" : "text-faint"
                }`}
              >
                {stage.sub}
              </span>
            </div>
            {i < STAGES.length - 1 ? (
              <>
                <span
                  aria-hidden
                  className="pipe-link hidden h-[2px] w-7 shrink-0 bg-line-strong sm:block"
                  style={{ "--pipe-delay": `${i * NODE_STEP_MS + 110}ms` } as React.CSSProperties}
                />
                <span
                  aria-hidden
                  className="pipe-link-vertical h-5 w-[2px] shrink-0 bg-line-strong sm:hidden"
                  style={{ "--pipe-delay": `${i * NODE_STEP_MS + 110}ms` } as React.CSSProperties}
                />
              </>
            ) : null}
          </div>
        ))}
      </div>
      <p className="type-mono mt-5 text-faint">
        <span className="text-accent-deep">indigo nodes</span>
        {" are the model · everything else is deterministic code"}
      </p>
    </div>
  );
}
