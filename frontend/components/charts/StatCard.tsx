import type { Chart } from "@/lib/demo";

/** A single computed number, shown big. No chart chrome, no decoration. */
export default function StatCard({ chart, context }: { chart: Chart; context?: string }) {
  const point = chart.data[0];
  return (
    <div className="flex flex-col items-start gap-1 py-2" data-chart="stat-card">
      <div className="font-display text-5xl font-semibold tracking-tight text-ink sm:text-6xl">
        {point.formatted}
      </div>
      <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-2">
        {point.label}
      </div>
      {context ? <div className="text-[12.5px] text-ink-3">{context}</div> : null}
    </div>
  );
}
