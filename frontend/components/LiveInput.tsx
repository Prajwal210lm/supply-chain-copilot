// Present but honest: the ask endpoint exists (key-gated, rate-limited),
// and the public input ships in v2. Until then this control says exactly
// what it is instead of pretending.
export default function LiveInput() {
  return (
    <div className="no-print mt-14 sm:mt-16">
      <div className="flex items-center gap-3 rounded-xl border border-line bg-raised px-4 py-3.5">
        <input
          type="text"
          disabled
          placeholder="Ask your own question…"
          aria-label="Ask your own question (live input ships in v2)"
          className="min-w-0 flex-1 bg-transparent text-[15px] text-ink placeholder:text-faint focus:outline-none disabled:cursor-not-allowed"
        />
        <span className="shrink-0 rounded-full border border-machine-line bg-machine px-3 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-accent-deep">
          v2
        </span>
      </div>
      <p className="mt-2.5 font-mono text-[11px] leading-relaxed text-faint">
        Live questions ship in v2. This page replays saved output from the real pipeline —
        the five turns above cost $0.14 of tokens to produce.
      </p>
    </div>
  );
}
