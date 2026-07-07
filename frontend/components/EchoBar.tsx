"use client";

import { useEffect, useRef, useState } from "react";
import type { EchoField, Spec } from "@/lib/demo";

// The trust surface. Between every question and answer sits the system's
// reading of the question — derived from the validated spec, never from
// model prose. The fields assemble once when the turn first scrolls into
// view, and the exact JSON the validators consumed is one toggle away.
// No dead controls: editing ships with live input in v2, so the
// affordance here is inspection, which is real today.
export default function EchoBar({
  fields,
  spec,
}: {
  fields: EchoField[];
  spec: Spec;
}) {
  const [live, setLive] = useState(false);
  const [specOpen, setSpecOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setLive(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`rounded-lg border border-machine-line bg-machine ${live ? "echo-live" : ""}`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-machine-line/70 px-4 py-2">
        <span className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-accent-deep">
          Interpreted as
        </span>
        <button
          type="button"
          onClick={() => setSpecOpen((v) => !v)}
          aria-expanded={specOpen}
          className="-my-1 rounded-md px-2 py-1.5 font-mono text-[11px] text-slate hover:bg-accent-glow hover:text-accent-deep"
        >
          {specOpen ? "hide spec" : "view spec"} {"{}"}
        </button>
      </div>

      <dl className="flex flex-wrap gap-x-6 gap-y-2.5 px-4 py-3">
        {fields.map((field, i) => (
          <div
            key={field.label + field.value}
            className="echo-field flex items-baseline gap-2"
            style={{ transitionDelay: live ? `${i * 70}ms` : undefined }}
          >
            <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
              {field.label}
            </dt>
            <dd className="font-mono text-[13px] font-medium text-ink">
              {field.value}
            </dd>
          </div>
        ))}
      </dl>

      {specOpen ? (
        <pre className="overflow-x-auto border-t border-machine-line/70 px-4 py-3 font-mono text-xs leading-relaxed text-slate">
          {JSON.stringify(spec, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
