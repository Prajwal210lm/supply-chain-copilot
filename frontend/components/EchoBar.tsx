"use client";

import { useEffect, useRef, useState } from "react";
import type { Spec } from "@/lib/demo";
import { echoFields, specTypeLabel } from "@/lib/demo";

/** The signature trust element: the system's reading of your question,
 *  rendered as structured machine fields before you look at any number.
 *  Fields stagger in on first scroll-in; "view spec" reveals the raw JSON. */
export default function EchoBar({ spec, echoText }: { spec: Spec; echoText?: string }) {
  const [open, setOpen] = useState(false);
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const fields = echoFields(spec, echoText);

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
      className={`rounded-lg border border-line border-l-2 border-l-accent bg-panel transition-shadow duration-300 motion-reduce:transition-none hover:shadow-[0_0_0_3px_var(--accent-tint)] ${
        inView ? "is-in" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
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

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 px-4 py-3.5 sm:grid-cols-5 sm:gap-x-4">
        {fields.map((f, i) => (
          <div
            key={f.label}
            className="echo-field min-w-0"
            style={{ "--echo-delay": `${i * 90}ms` } as React.CSSProperties}
          >
            <dt className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-ink-3">
              {f.label}
            </dt>
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

      {open ? (
        <pre className="overflow-x-auto border-t border-line bg-accent-tint/60 px-4 py-3 font-mono text-[11.5px] leading-relaxed text-accent-ink">
          {JSON.stringify(spec, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
