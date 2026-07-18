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

/** The live tail of the conversation. Demo turns stay static above; the
 *  visitor's own questions append here, answered by the deployed pipeline.
 *  Only live turns travel as context — the demo is a different thread. */
export default function LiveThread({ demoTurnCount }: { demoTurnCount: number }) {
  const [turns, setTurns] = useState<LiveTurnData[]>([]);
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<AskStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const computeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const used = useSyncExternalStore(subscribeUsed, questionsUsed, questionsUsedServer);
  const remaining = QUESTION_LIMIT - used;

  async function submit(text: string) {
    const question = text.trim();
    if (!question || status !== "idle" || remaining <= 0) return;

    setError(null);
    setStatus("interpreting");
    computeTimer.current = setTimeout(() => setStatus("computing"), 2800);

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
      if (computeTimer.current) clearTimeout(computeTimer.current);
      setStatus("idle");
    }
  }

  return (
    <div data-live-thread>
      {turns.length > 0 ? (
        <div className="mb-8 mt-14 flex items-center gap-3">
          <span aria-hidden="true" className="h-px flex-1 bg-line-2" />
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-3">
            your questions · answered live
          </span>
          <span aria-hidden="true" className="h-px flex-1 bg-line-2" />
        </div>
      ) : null}

      <ol className="list-none space-y-10">
        {turns.map((t, i) => (
          <li key={i}>
            <LiveTurn
              turn={t}
              index={demoTurnCount + i + 1}
              onChip={(chip) => submit(chip)}
              chipsDisabled={status !== "idle" || remaining <= 0}
            />
          </li>
        ))}
      </ol>

      <div className={turns.length > 0 ? "mt-10" : "mt-12"}>
        <LiveInput
          value={value}
          onChange={setValue}
          onSubmit={() => submit(value)}
          status={status}
          remaining={remaining}
          error={error}
        />
      </div>
    </div>
  );
}
