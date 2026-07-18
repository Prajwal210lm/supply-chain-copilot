import type { Spec, TurnResponse } from "./demo";

/* ---------------------------------------------------------------------------
   Client-side layer for POST /api/ask. The response shape is identical to a
   demo turn's `response`, so live answers render through the same components.

   NEXT_PUBLIC_API_SECRET ships in the browser bundle by design (it stops
   casual scraping, not determined attackers); the real protection is
   server-side: per-IP throttling, a daily cap, and a Semaphore(1).
--------------------------------------------------------------------------- */

export type LiveTurnData = { question: string; response: TurnResponse };

export type ContextPair = { question: string; spec: Spec };

export type AskFailure =
  | { kind: "timeout" }
  | { kind: "network" }
  | { kind: "http"; status: number; detail: string };

export class AskError extends Error {
  failure: AskFailure;
  constructor(failure: AskFailure) {
    super(failure.kind === "http" ? failure.detail : failure.kind);
    this.failure = failure;
  }
}

const TIMEOUT_MS = 30_000;

export async function askQuestion(
  question: string,
  context: ContextPair[],
): Promise<TurnResponse> {
  const base = process.env.NEXT_PUBLIC_API_URL;
  const secret = process.env.NEXT_PUBLIC_API_SECRET;
  if (!base || !secret) {
    throw new AskError({
      kind: "http",
      status: 0,
      detail: "Live questions aren't configured on this deployment.",
    });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${base}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Api-Secret": secret },
      body: JSON.stringify({ question, context }),
      signal: controller.signal,
    });
  } catch (err) {
    throw new AskError(
      err instanceof DOMException && err.name === "AbortError"
        ? { kind: "timeout" }
        : { kind: "network" },
    );
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail ?? "";
    } catch {
      /* non-JSON error body */
    }
    throw new AskError({ kind: "http", status: res.status, detail });
  }
  return (await res.json()) as TurnResponse;
}

export function failureMessage(f: AskFailure): string {
  if (f.kind === "timeout")
    return "That took longer than 30 seconds. The question wasn't counted; try again.";
  if (f.kind === "network")
    return "Couldn't reach the API. The question wasn't counted; check your connection and try again.";
  if (f.status === 429 && f.detail) return `${f.detail} The question wasn't counted.`;
  if (f.status === 403)
    return "The API rejected this deployment's secret. The question wasn't counted.";
  if (f.status === 503)
    return "Live questions are temporarily unavailable on the server. The question wasn't counted.";
  return f.detail
    ? `${f.detail} The question wasn't counted.`
    : "Something went wrong on the way to the API. The question wasn't counted.";
}

/* ---------------------------------------------------------------------------
   Per-browser question budget, exposed as an external store so components
   read it with useSyncExternalStore (hydration-safe: the server snapshot is
   0 used; the client snapshot takes over after hydration).
--------------------------------------------------------------------------- */

export const QUESTION_LIMIT = 10;
const STORAGE_KEY = "scc-live-used-v1";

let listeners: (() => void)[] = [];

export function subscribeUsed(cb: () => void): () => void {
  listeners.push(cb);
  return () => {
    listeners = listeners.filter((l) => l !== cb);
  };
}

export function questionsUsed(): number {
  if (typeof window === "undefined") return 0;
  const n = Number(window.localStorage.getItem(STORAGE_KEY) ?? "0");
  return Number.isFinite(n) && n >= 0 ? Math.min(n, QUESTION_LIMIT) : 0;
}

export function questionsUsedServer(): number {
  return 0;
}

export function consumeQuestion(): void {
  const used = Math.min(questionsUsed() + 1, QUESTION_LIMIT);
  window.localStorage.setItem(STORAGE_KEY, String(used));
  listeners.forEach((l) => l());
}
