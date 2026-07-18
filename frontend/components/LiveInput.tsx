"use client";

import { QUESTION_LIMIT } from "@/lib/live";

export type AskStatus = "idle" | "interpreting" | "computing";

/** The live question form. Calm in every state: a counter while questions
 *  remain, a quiet status while one is in flight, plain words when the
 *  budget is spent. */
export default function LiveInput({
  value,
  onChange,
  onSubmit,
  status,
  remaining,
  error,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  status: AskStatus;
  remaining: number;
  error: string | null;
}) {
  const pending = status !== "idle";
  const exhausted = remaining <= 0;
  const disabled = pending || exhausted;

  return (
    <div className="rounded-xl border border-line bg-surface p-4 sm:p-5">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <label htmlFor="live-question" className="sr-only">
          Ask a question about the data
        </label>
        <div className="flex items-center gap-3 rounded-lg border border-line-2 bg-panel px-4 py-3 focus-within:border-accent-line">
          <span aria-hidden="true" className="font-mono text-sm text-accent-ink">
            ❯
          </span>
          <input
            id="live-question"
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            placeholder="Ask about OTIF, fill rate, lead times, stockouts…"
            className="w-full bg-transparent font-mono text-[13px] text-ink placeholder:text-ink-3 disabled:cursor-not-allowed"
          />
          {pending ? (
            <span className="shrink-0 font-mono text-[10.5px] uppercase tracking-[0.14em] text-accent-ink">
              {status === "interpreting" ? "interpreting…" : "computing…"}
            </span>
          ) : exhausted ? (
            <span className="shrink-0 rounded-full border border-line-2 px-2.5 py-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-ink-3">
              {QUESTION_LIMIT} questions used
            </span>
          ) : (
            <button
              type="submit"
              disabled={value.trim().length === 0}
              className="shrink-0 rounded-md bg-accent-deep px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-[0.1em] text-white transition-opacity disabled:opacity-40"
            >
              ask
            </button>
          )}
        </div>
      </form>

      <div aria-live="polite" className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-[11px] text-ink-3">
          Each question costs ~$0.03 of tokens. Limited to {QUESTION_LIMIT} per visitor.
        </p>
        {!exhausted ? (
          <p data-remaining className="font-mono text-[11px] text-ink-2">
            {remaining} of {QUESTION_LIMIT} remaining
          </p>
        ) : null}
      </div>
      {error ? (
        <p role="status" className="mt-2 font-mono text-[11.5px] leading-relaxed text-highlight">
          {error}
        </p>
      ) : null}
    </div>
  );
}
