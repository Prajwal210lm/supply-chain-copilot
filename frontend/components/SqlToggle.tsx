"use client";

import { useState } from "react";

/** The compiled SQL, collapsed by default. The one deep surface on the page:
 *  a code block with an accent top bar. The model never wrote a line of it. */
export default function SqlToggle({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div data-sql-toggle>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="rounded font-mono text-[10.5px] uppercase tracking-[0.14em] text-ink-3 underline decoration-line-2 underline-offset-4 transition-colors hover:text-accent-ink hover:decoration-accent-line"
      >
        {open ? "hide compiled sql" : "show compiled sql"}
      </button>
      {open ? (
        <div className="mt-2 overflow-hidden rounded-lg border border-line-2">
          <div className="h-[3px] bg-accent" aria-hidden="true" />
          <div className="flex items-center justify-between bg-code px-4 pt-2.5">
            <span className="font-mono text-[9.5px] uppercase tracking-[0.2em] text-ink-on-code-muted">
              compiled by code · executed read-only
            </span>
          </div>
          <pre className="overflow-x-auto bg-code px-4 pb-4 pt-2 font-mono text-[11.5px] leading-[1.7] text-ink-on-code">
            {sql.trim()}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
