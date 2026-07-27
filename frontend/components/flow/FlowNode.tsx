/** Shared visual language for pipeline stages and the before/after strip.
 *  Model stages are accent-tinted; deterministic stages sit on plain surface;
 *  terminals are quiet dots. Animation delays cascade via --flow-delay. */
export default function FlowNode({
  label,
  sub,
  kind,
  delay = 0,
  compact = false,
}: {
  label: string;
  sub?: string;
  kind: "model" | "code" | "terminal";
  delay?: number;
  compact?: boolean;
}) {
  const style = { "--flow-delay": `${delay}ms` } as React.CSSProperties;

  if (kind === "terminal") {
    return (
      <div className="flow-node flex flex-col items-center gap-1.5" style={style}>
        <span aria-hidden="true" className="block h-2.5 w-2.5 rounded-full bg-ink-3" />
        <span className="font-mono text-[9.5px] uppercase tracking-[0.16em] text-ink-3">
          {label}
        </span>
      </div>
    );
  }

  const model = kind === "model";
  return (
    <div
      className={`flow-node rounded-lg border text-center ${
        model
          ? "flow-model border-accent-line bg-accent-tint"
          : "border-line bg-surface/90 shadow-[var(--elev-1)] backdrop-blur-sm"
      } ${compact ? "px-3 py-1.5" : "px-2 py-2.5 sm:px-2.5"}`}
      style={style}
    >
      <div
        className={`font-mono ${compact ? "text-[11px]" : "text-[11.5px]"} font-medium ${
          model ? "text-accent-ink" : "text-ink"
        }`}
      >
        {label}
      </div>
      {sub ? (
        <div className="mt-1 text-[9.5px] leading-snug text-ink-3">{sub}</div>
      ) : null}
      {!compact ? (
        <div
          className={`mt-1.5 font-mono text-[8px] uppercase tracking-[0.2em] ${
            model ? "text-accent" : "text-ink-3"
          }`}
        >
          {model ? "model" : "code"}
        </div>
      ) : null}
    </div>
  );
}
