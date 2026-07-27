"use client";

import { QUESTION_LIMIT } from "@/lib/live";

export type AskStatus = "idle" | "interpreting" | "computing" | "narrating";

const STAGE_LABEL: Record<Exclude<AskStatus, "idle">, string> = {
  interpreting: "Interpreting your question…",
  computing: "Compiling and executing…",
  narrating: "Writing the answer…",
};
const STAGE_ORDER: Exclude<AskStatus, "idle">[] = ["interpreting", "computing", "narrating"];

/** The seven real pipeline stages, mapped onto the three status phases the
 *  client can actually observe from a single request/response. */
const PIPELINE_STAGES: {
  label: string;
  kind: "model" | "code";
  phase: Exclude<AskStatus, "idle">;
}[] = [
  { label: "Interpret", kind: "model", phase: "interpreting" },
  { label: "Validate", kind: "code", phase: "computing" },
  { label: "Compile", kind: "code", phase: "computing" },
  { label: "Execute", kind: "code", phase: "computing" },
  { label: "Decompose", kind: "code", phase: "computing" },
  { label: "Narrate", kind: "model", phase: "narrating" },
  { label: "Render gate", kind: "code", phase: "narrating" },
];

/** While a question is in flight, the wait is spent showing the architecture
 *  doing its job: the same seven stages the Design section explains, lighting
 *  up as the request progresses. Model stages keep their indigo treatment.
 *
 *  The phases are time-based (one request carries no intermediate events), so
 *  this is an honest illustration of stage ORDER, not a claim of live
 *  telemetry. The text label remains the real accessible status. */
function StageTrack({ status }: { status: AskStatus }) {
  if (status === "idle") return null;
  const activePhase = STAGE_ORDER.indexOf(status as Exclude<AskStatus, "idle">);

  const stageState = (phase: Exclude<AskStatus, "idle">) => {
    const idx = STAGE_ORDER.indexOf(phase);
    return { done: idx < activePhase, active: idx === activePhase };
  };

  return (
    <div className="mt-4">
      {/* Mobile: seven segments, no labels — at 390px each stage gets ~43px,
          which cannot hold "Render gate" without truncating to noise. The
          text status line below carries the meaning instead. */}
      <div className="flex items-center gap-1 sm:hidden" aria-hidden="true">
        {PIPELINE_STAGES.map((s) => {
          const { done, active } = stageState(s.phase);
          return (
            <span
              key={s.label}
              className={`h-1.5 flex-1 rounded-full transition-colors duration-300 motion-reduce:transition-none ${
                active
                  ? "bg-accent"
                  : done
                    ? "bg-accent-line"
                    : "bg-line-2"
              } ${active ? "animate-pulse motion-reduce:animate-none" : ""}`}
            />
          );
        })}
      </div>

      {/* sm+: the labelled stages, mirroring the Design section's diagram. */}
      <div className="hidden items-center gap-1 sm:flex" aria-hidden="true">
        {PIPELINE_STAGES.map((s, i) => {
          const { done, active } = stageState(s.phase);
          const model = s.kind === "model";
          return (
            <span key={s.label} className="flex min-w-0 flex-1 items-center gap-1">
              {i > 0 ? (
                <span
                  className={`h-px w-1.5 shrink-0 transition-colors duration-300 motion-reduce:transition-none ${
                    done || active ? "bg-accent-line" : "bg-line-2"
                  }`}
                />
              ) : null}
              <span
                className={`min-w-0 flex-1 truncate rounded border px-1 py-1 text-center font-mono text-[8.5px] uppercase tracking-[0.04em] transition-colors duration-300 motion-reduce:transition-none ${
                  active
                    ? `stage-active border-accent-line ${model ? "bg-accent-tint text-accent-ink" : "bg-surface text-ink"}`
                    : done
                      ? "border-accent-line/60 bg-accent-tint/50 text-accent-ink"
                      : "border-line bg-surface/70 text-ink-3"
                }`}
                title={s.label}
              >
                {s.label}
              </span>
            </span>
          );
        })}
      </div>

      <p className="mt-2 font-mono text-[11px] text-accent-ink">
        {STAGE_LABEL[status as Exclude<AskStatus, "idle">]}
      </p>
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
