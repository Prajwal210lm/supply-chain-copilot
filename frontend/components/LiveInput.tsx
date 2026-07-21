"use client";

import { QUESTION_LIMIT } from "@/lib/live";

export type AskStatus = "idle" | "interpreting" | "computing" | "narrating";

const STAGE_LABEL: Record<Exclude<AskStatus, "idle">, string> = {
  interpreting: "Interpreting your question…",
  computing: "Compiling and executing…",
  narrating: "Writing the answer…",
};
const STAGE_ORDER: Exclude<AskStatus, "idle">[] = ["interpreting", "computing", "narrating"];

/** A three-segment progress track under the input while a question is in
 *  flight — makes a stageless wait (no streaming events to key off) read as
 *  purposeful rather than dead. Collapses to the plain label under reduced
 *  motion; the label itself is the real, accessible status either way. */
function StageTrack({ status }: { status: AskStatus }) {
  if (status === "idle") return null;
  const activeIdx = STAGE_ORDER.indexOf(status as Exclude<AskStatus, "idle">);
  return (
    <div className="mt-3 flex items-center gap-4">
      <div className="flex flex-1 gap-1.5" aria-hidden="true">
        {STAGE_ORDER.map((s, i) => (
          <span
            key={s}
            className={`h-1 flex-1 rounded-full transition-colors duration-500 motion-reduce:transition-none ${
              i <= activeIdx ? "bg-accent" : "bg-line-2"
            } ${i === activeIdx ? "animate-pulse motion-reduce:animate-none" : ""}`}
          />
        ))}
      </div>
      <span className="shrink-0 font-mono text-[11px] text-accent-ink">
        {STAGE_LABEL[status as Exclude<AskStatus, "idle">]}
      </span>
    </div>
  );
}

/** The live question form. Generous and inviting while questions remain,
 *  a purposeful staged status while one is in flight, plain words — not an
 *  apology — once the budget is spent. */
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
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <label htmlFor="live-question" className="sr-only">
          Ask a question about the data
        </label>
        <div className="flex flex-col gap-3 rounded-xl border border-line-2 bg-surface p-2.5 shadow-sm transition-colors focus-within:border-accent-line sm:flex-row sm:items-center sm:gap-3">
          <span aria-hidden="true" className="pl-2.5 font-mono text-base text-accent-ink sm:pl-3">
            ❯
          </span>
          <input
            id="live-question"
            type="text"
            inputMode="text"
            enterKeyHint="send"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            placeholder="Ask about OTIF, fill rate, lead times, stockouts…"
            className="w-full bg-transparent py-2 font-mono text-[16px] text-ink placeholder:text-ink-3 disabled:cursor-not-allowed sm:py-2.5"
          />
          {exhausted ? (
            <span className="shrink-0 rounded-lg border border-line-2 bg-panel px-4 py-2.5 text-center font-mono text-[10.5px] uppercase tracking-[0.12em] text-ink-3">
              {QUESTION_LIMIT} of {QUESTION_LIMIT} used
            </span>
          ) : (
            <button
              type="submit"
              disabled={pending || value.trim().length === 0}
              className="shrink-0 rounded-lg bg-accent-deep px-5 py-2.5 font-mono text-[12px] font-medium uppercase tracking-[0.1em] text-white shadow-sm transition-[opacity,transform] duration-150 disabled:opacity-40 disabled:shadow-none enabled:hover:-translate-y-px motion-reduce:enabled:hover:translate-y-0"
            >
              {pending ? "Asking…" : "Ask →"}
            </button>
          )}
        </div>
      </form>

      <StageTrack status={status} />

      <div aria-live="polite" className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-[11px] text-ink-3">
          Each question costs ~$0.03 of tokens. Limited to {QUESTION_LIMIT} per visitor.
        </p>
        {!exhausted && !pending ? (
          <p
            data-remaining
            className="rounded-full bg-accent-tint px-2.5 py-1 font-mono text-[11px] font-medium text-accent-ink"
          >
            {remaining} of {QUESTION_LIMIT} remaining
          </p>
        ) : null}
      </div>

      {exhausted ? (
        <p className="mt-3 font-mono text-[12px] leading-relaxed text-ink-2">
          You&rsquo;ve used all {QUESTION_LIMIT} questions. The demo above replays the
          full investigation.
        </p>
      ) : null}

      {error ? (
        <p role="status" className="mt-3 font-mono text-[11.5px] leading-relaxed text-highlight">
          {error}
        </p>
      ) : null}
    </div>
  );
}
