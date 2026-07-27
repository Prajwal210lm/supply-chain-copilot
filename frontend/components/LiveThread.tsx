"use client";

import { useRef, useState, useSyncExternalStore } from "react";
import {
  AskError,
  askQuestion,
  consumeQuestion,
  failureMessage,
  QUESTION_LIMIT,
  questionsUsed,
  questionsUsedServer,
  subscribeUsed,
  type ContextPair,
  type LiveTurnData,
} from "@/lib/live";
import LiveInput, { type AskStatus } from "./LiveInput";
import LiveTurn from "./LiveTurn";
import Reveal from "./ui/Reveal";

/** Starting points for a visitor who doesn't know what to ask. Chosen to
 *  mirror question shapes already proven against the live pipeline: an
 *  explicit single month (metric_query), a filtered metric (matches the
 *  demo's Anadolu turn), and a plain dimension breakdown. */
const SUGGESTED = [
  "What was OTIF in April 2026?",
  "What was fill rate in March 2026?",
  "What's the average supplier lead time for Anadolu?",
  "How does OTIF break down by DC?",
];

/** The live tail of the conversation, built as its own workspace: a
 *  distinct panel that stands apart from the static demo above it. Demo
 *  turns never travel as context — this is a separate thread the visitor
 *  starts themselves. */
export default function LiveThread({ demoTurnCount }: { demoTurnCount: number }) {
  const [turns, setTurns] = useState<LiveTurnData[]>([]);
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<AskStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const used = useSyncExternalStore(subscribeUsed, questionsUsed, questionsUsedServer);
  const remaining = QUESTION_LIMIT - used;

  function clearTimers() {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }

  async function submit(text: string) {
    const question = text.trim();
    if (!question || status !== "idle" || remaining <= 0) return;

    setError(null);
    setValue(question);
    setStatus("interpreting");
    // Time-based stages, since a single request/response carries no
    // intermediate events to key off. Tuned to the pipeline's own shape:
    // Stage 1 (interpret) is usually the longest single wait, the middle
    // deterministic stages are fast, Stage 4 (narrate) is the second model
    // call. A fast real response simply arrives before the later stages
    // render, which is fine — the label is advisory, not a promise.
    timers.current.push(setTimeout(() => setStatus("computing"), 1600));
    timers.current.push(setTimeout(() => setStatus("narrating"), 3400));

    const context: ContextPair[] = turns.map((t) => ({
      question: t.question,
      spec: t.response.spec,
    }));

    try {
      const response = await askQuestion(question, context);
      setTurns((prev) => [...prev, { question, response }]);
      consumeQuestion();
      setValue("");
    } catch (err) {
      // Transport and server errors do not consume a question.
      setError(
        err instanceof AskError
          ? failureMessage(err.failure)
          : "Something unexpected went wrong. The question wasn't counted.",
      );
    } finally {
      clearTimers();
      setStatus("idle");
    }
  }

  const chipsDisabled = status !== "idle" || remaining <= 0;

  return (
    <Reveal>
      <div
        id="live-question-card"
        data-live-thread
        className="scroll-mt-24 rounded-2xl border-2 border-accent-line bg-panel/70 p-5 shadow-[var(--elev-3),var(--glass-inner)] backdrop-blur-md sm:p-8"
      >
        <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-accent-ink">
          ask your own question
        </div>
        <h3 className="mt-2 font-display text-xl font-semibold tracking-[-0.01em] text-ink sm:text-2xl">
          The demo above is pre-built. This one is live.
        </h3>
        <p className="mt-2.5 max-w-2xl text-[14px] leading-relaxed text-ink-2">
          This input runs the real pipeline — interpret, validate, compile, execute,
          narrate — against your question, live. No mock-up, no cached answer.
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {SUGGESTED.map((q) => (
            <button
              key={q}
              type="button"
              disabled={chipsDisabled}
              onClick={() => submit(q)}
              className="tap rounded-full border border-line-2 bg-surface px-3.5 py-1.5 text-[12.5px] text-ink-2 hover:border-accent-line hover:bg-accent-tint hover:text-accent-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        <div className="mt-5">
          <LiveInput
            value={value}
            onChange={setValue}
            onSubmit={() => submit(value)}
            status={status}
            remaining={remaining}
            error={error}
          />
        </div>

        {turns.length > 0 ? (
          <ol className="mt-8 list-none space-y-8 border-t border-line pt-8">
            {turns.map((t, i) => (
              <li key={i}>
                <LiveTurn
                  turn={t}
                  index={demoTurnCount + i + 1}
                  onChip={(chip) => submit(chip)}
                  chipsDisabled={chipsDisabled}
                  prevTurn={i > 0 ? turns[i - 1] : null}
                />
              </li>
            ))}
          </ol>
        ) : null}
      </div>
    </Reveal>
  );
}
