import type { ChartData } from "@/lib/demo";

// A single grounded number. Not a Recharts chart — a number this load-
// bearing deserves typography, not an SVG.
export default function StatCard({
  chart,
  periodLabel,
}: {
  chart: ChartData;
  periodLabel?: string;
}) {
  const point = chart.data[0];
  return (
    <div className="flex flex-col gap-2 py-4">
      <div className="font-mono text-[11px] uppercase tracking-[0.14em] text-slate">
        {chart.title}
        {periodLabel ? <span className="text-faint"> · {periodLabel}</span> : null}
      </div>
      <div className="font-display text-5xl font-medium tracking-tight text-ink sm:text-6xl">
        {point.formatted}
      </div>
    </div>
  );
}
