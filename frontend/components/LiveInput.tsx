import Reveal from "./ui/Reveal";

/** Calm and honest: the live path exists behind an API secret; the public
 *  page ships the saved thread. No spinner, no apology. */
export default function LiveInput({ threadCostUsd }: { threadCostUsd: number }) {
  return (
    <Reveal>
      <div className="rounded-xl border border-line bg-surface p-4 sm:p-5">
        <label htmlFor="live-question" className="sr-only">
          Ask a question (disabled in this demo)
        </label>
        <div className="flex items-center gap-3 rounded-lg border border-line-2 bg-panel px-4 py-3">
          <span aria-hidden="true" className="font-mono text-sm text-accent-ink">
            ❯
          </span>
          <input
            id="live-question"
            type="text"
            disabled
            placeholder="Ask about OTIF, fill rate, lead times, stockouts…"
            className="w-full bg-transparent font-mono text-[13px] text-ink placeholder:text-ink-3 disabled:cursor-not-allowed"
          />
          <span className="shrink-0 rounded-full border border-line-2 px-2.5 py-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-ink-3">
            live in v2
          </span>
        </div>
        <p className="mt-3 font-mono text-[11px] text-ink-3">
          The five answers above cost ${threadCostUsd.toFixed(2)} of model tokens, end to
          end. The live endpoint runs behind an API secret with a daily cap.
        </p>
      </div>
    </Reveal>
  );
}
