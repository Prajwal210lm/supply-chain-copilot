import type { LiveTurnData } from "@/lib/live";
import Panel from "./ui/Panel";
import Turn from "./Turn";

/** One live turn. Answers reuse the demo Turn wholesale (echo bar, chart,
 *  narration, SQL). Clarifications and refusals render as the machine
 *  speaking, with clickable chips that become the next question. */
export default function LiveTurn({
  turn,
  index,
  onChip,
  chipsDisabled,
  prevTurn,
}: {
  turn: LiveTurnData;
  index: number;
  onChip: (text: string) => void;
  chipsDisabled: boolean;
  prevTurn?: LiveTurnData | null;
}) {
  const { response } = turn;

  if (response.type === "answer") {
    return <Turn turn={turn} index={index} prevTurn={prevTurn} />;
  }

  const isClarification = response.type === "clarification";
  const spec = response.spec as unknown as { question?: string };
  const text = isClarification
    ? (spec.question ?? "Which reading did you mean?")
    : (response.message ?? "This question is outside the catalog.");
  const chips = (isClarification ? response.options : response.suggestions) ?? [];

  return (
    <article id={`turn-live-${index}`} className="scroll-mt-28">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[11px] text-ink-3">
          {String(index).padStart(2, "0")}
        </span>
        <h3 className="font-display text-xl font-semibold tracking-[-0.01em] text-ink sm:text-[1.45rem]">
          &ldquo;{turn.question}&rdquo;
        </h3>
      </div>

      <div className="mt-4">
        <Panel className="px-4 py-4 sm:px-6 sm:py-5">
          <div
            className={`font-mono text-[10px] uppercase tracking-[0.22em] ${
              isClarification ? "text-accent-ink" : "text-highlight"
            }`}
          >
            {isClarification ? "the copilot asks" : "refused, by design"}
          </div>
          <p className="mt-2 max-w-prose text-[15px] leading-relaxed text-ink">{text}</p>
          {chips.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2.5">
              {chips.map((c) => (
                <button
                  key={c}
                  type="button"
                  disabled={chipsDisabled}
                  onClick={() => onChip(c)}
                  className="tap rounded-full border border-line-2 bg-surface px-4 py-2 text-[13px] text-ink-2 hover:border-accent-line hover:bg-accent-tint hover:text-accent-ink disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span aria-hidden="true" className="mr-1.5 font-mono text-accent">
                    ❯
                  </span>
                  {c}
                </button>
              ))}
            </div>
          ) : null}
        </Panel>
      </div>
    </article>
  );
}
