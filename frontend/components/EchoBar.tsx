"use client";

import { useEffect, useRef, useState } from "react";
import type { FieldOrigin, Spec } from "@/lib/demo";
import { echoFieldOrigins, echoFields, specTypeLabel } from "@/lib/demo";

const ORIGIN_STYLE: Record<FieldOrigin, string> = {
  inherited: "border-line-2 bg-panel text-ink-3",
  changed: "border-accent-line bg-accent-tint text-accent-ink",
};

/** The signature trust element: the system's reading of your question,
 *  rendered as structured machine fields before you look at any number.
 *  Fields stagger in on first scroll-in; "view spec" reveals the raw JSON.
 *
 *  When `prevSpec` is supplied (live follow-ups only), each field is marked
 *  inherited or changed so multi-turn context carry becomes visible. */
export default function EchoBar({
  spec,
  echoText,
  prevSpec,
  prevEchoText,
}: {
  spec: Spec;
  echoText?: string;
  prevSpec?: Spec | null;
  prevEchoText?: string;
}) {
  const [open, setOpen] = useState(false);
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const fields = echoFields(spec, echoText);
  const origins = echoFieldOrigins(
    fields,
    prevSpec ? echoFields(prevSpec, prevEchoText) : null,
  );
  const hasOrigins = Object.keys(origins).length > 0;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Under prefers-reduced-motion the CSS fallback shows the fields anyway.
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      data-echo-bar
      className={`echo-shell relative overflow-hidden rounded-lg border border-line bg-panel/80 backdrop-blur-sm transition-shadow duration-300 motion-reduce:transition-none hover:shadow-[var(--glow-accent)] ${
        inView ? "is-in" : ""
      }`}
    >
      <span
        aria-hidden="true"
        className="echo-rail absolute inset-y-0 left-0 w-[2px] bg-accent-line"
      />

      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2 pl-5">
        <span className="min-w-0 truncate font-mono text-[10px] uppercase tracking-[0.22em] text-accent-ink">
          interpreted as
          <span className="hidden sm:inline"> · {specTypeLabel(spec)}</span>
        </span>
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 whitespace-nowrap rounded font-mono text-[10.5px] uppercase tracking-[0.14em] text-ink-2 underline decoration-line-2 underline-offset-4 transition-colors hover:text-accent-ink hover:decoration-accent-line"
        >
          {open ? "hide spec" : "view spec"}
        </button>
      </div>

      <dl className="echo-sweep grid grid-cols-2 gap-x-6 gap-y-3 px-4 py-3.5 pl-5 sm:grid-cols-5 sm:gap-x-4">
        {fields.map((f, i) => (
          <div
            key={f.label}
            className="echo-field min-w-0"
            style={{ "--echo-delay": `${i * 90}ms` } as React.CSSProperties}
          >
            <div className="flex items-center gap-1.5">
              <dt className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-ink-3">
                {f.label}
              </dt>
              {origins[f.label] ? (
                <span
                  className={`shrink-0 rounded-full border px-1.5 font-mono text-[8px] uppercase tracking-[0.08em] ${
                    ORIGIN_STYLE[origins[f.label]]
                  }`}
                >
                  {origins[f.label]}
                </span>
              ) : null}
            </div>
            <dd
              className={`mt-1 font-mono text-[12.5px] ${
                f.label === "window" ? "break-words" : "truncate"
              } ${f.accent ? "font-medium text-accent-ink" : "text-ink"}`}
              title={f.value}
            >
              {f.value}
            </dd>
          </div>
        ))}
      </dl>

      {hasOrigins ? (
        <p className="border-t border-line px-4 py-1.5 pl-5 font-mono text-[9.5px] text-ink-3">
          carried forward from your previous question
        </p>
      ) : null}

      <div className="expando" data-open={open}>
        <div inert={!open}>
          <pre className="overflow-x-auto whitespace-pre border-t border-line bg-accent-tint/60 px-4 py-3 pl-5 font-mono text-[11.5px] leading-relaxed text-accent-ink">
            {JSON.stringify(spec, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
