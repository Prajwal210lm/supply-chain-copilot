"use client";

import { useState } from "react";
import { SQL_TOKEN_CLASS, tokenizeSqlLines } from "@/lib/sqlHighlight";
import ScrollFade from "./ui/ScrollFade";

/** The compiled SQL, collapsed by default. The one deep surface on the page:
 *  a code block with an accent top bar, a line-number gutter, and syntax
 *  colouring. The model never wrote a line of it.
 *
 *  Layout note: the gutter sits OUTSIDE the <pre> so line numbers stay put
 *  while long lines scroll horizontally — the <pre> remains the single
 *  scroll container. */
export default function SqlToggle({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const code = sql.trim();
  const lines = tokenizeSqlLines(code);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable (insecure context or denied) — stay silent */
    }
  }

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

      {/* `inert` while collapsed: the content stays mounted so the row height
          can animate, but the copy button must not be tab-reachable or exposed
          to assistive tech while it is visually hidden. */}
      <div className="expando mt-2" data-open={open}>
        <div inert={!open}>
          <div className="overflow-hidden rounded-lg border border-line-2 shadow-[var(--elev-2)]">
            <div className="h-[3px] bg-gradient-to-r from-accent-deep via-accent to-accent-line" aria-hidden="true" />
            <div className="flex items-center justify-between gap-3 bg-code px-4 pt-2.5">
              <span className="font-mono text-[9.5px] uppercase tracking-[0.2em] text-ink-on-code-muted">
                compiled by code · executed read-only
              </span>
              <button
                type="button"
                onClick={copy}
                className="shrink-0 rounded border border-ink-on-code-muted/30 px-2 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.12em] text-ink-on-code-muted transition-colors hover:border-ink-on-code/50 hover:text-ink-on-code"
              >
                {copied ? "copied" : "copy"}
              </button>
            </div>
            <div className="relative flex bg-code">
              <div
                aria-hidden="true"
                className="shrink-0 select-none border-r border-ink-on-code-muted/15 px-3 py-2 text-right font-mono text-[11.5px] leading-[1.7] text-ink-on-code-muted/50"
              >
                {lines.map((_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
              </div>
              <pre className="flex-1 overflow-x-auto whitespace-pre px-4 py-2 font-mono text-[11.5px] leading-[1.7] text-ink-on-code">
                {lines.map((tokens, i) => (
                  <div key={i}>
                    {tokens.length === 0 ? " " : null}
                    {tokens.map((t, j) => (
                      <span key={j} className={SQL_TOKEN_CLASS[t.kind]}>
                        {t.text}
                      </span>
                    ))}
                  </div>
                ))}
              </pre>
              <ScrollFade to="--code" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
