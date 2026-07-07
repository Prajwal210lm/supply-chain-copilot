"use client";

import { useState } from "react";

// The compiled SQL, collapsed by default. It exists to prove a claim the
// page makes everywhere: the model never wrote this — a deterministic
// compiler did, with every user-derived value bound as a parameter (?).
export default function SQLToggle({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-w-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="-mx-2 -my-2 rounded-md px-2 py-2 font-mono text-[11px] text-faint hover:bg-accent-wash hover:text-accent-deep"
      >
        {open ? "▾ hide compiled SQL" : "▸ show compiled SQL"}
      </button>
      {open ? (
        <div className="mt-2 overflow-hidden rounded-md border border-line">
          <div aria-hidden className="h-0.5 bg-accent-deep" />
          <pre className="max-h-80 overflow-auto bg-sunken p-3 font-mono text-[11px] leading-relaxed text-ink">
            {sql}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
