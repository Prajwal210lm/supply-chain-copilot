"use client";

import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartData, ChartPoint } from "@/lib/demo";
import { chart as c } from "@/lib/tokens";

const COLOR: Record<string, string> = {
  green: c.positive,
  red: c.negative,
  total: c.neutral,
};

type WaterfallRow = ChartPoint & { base: number; bar: number };

// Contributions arrive ranked by |contribution| with a trailing Total.
// Each bar floats from the running cumulative sum; the Total bar spans
// from zero to the full delta.
function toFloatingRows(points: ChartPoint[]): WaterfallRow[] {
  let cumulative = 0;
  return points.map((p) => {
    const v = p.value ?? 0;
    if (p.color === "total") {
      return { ...p, base: Math.min(0, v), bar: Math.abs(v) };
    }
    const start = cumulative;
    cumulative += v;
    return { ...p, base: Math.min(start, cumulative), bar: Math.abs(v) };
  });
}

function WaterfallTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: WaterfallRow }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded border border-line bg-raised px-2.5 py-1.5 font-mono text-xs text-ink shadow-sm">
      <span className="text-faint">{p.label}</span>{" "}
      <span className="font-medium" style={{ color: COLOR[p.color ?? "total"] }}>
        {p.formatted}
      </span>
    </div>
  );
}

export default function DemoWaterfallChart({ chart }: { chart: ChartData }) {
  const rows = toFloatingRows(chart.data);
  const dense = rows.length > 6;
  return (
    <div className="h-72 w-full sm:h-80" role="img" aria-label={`Waterfall chart: ${chart.title}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          margin={{ top: 8, right: 8, bottom: dense ? 8 : 0, left: 0 }}
          barCategoryGap="24%"
        >
          <XAxis
            dataKey="label"
            tick={{ fontSize: dense ? 9 : 10, fontFamily: "var(--font-mono)", fill: c.tick }}
            tickLine={false}
            axisLine={{ stroke: c.axisLine }}
            interval={0}
            angle={dense ? -42 : 0}
            textAnchor={dense ? "end" : "middle"}
            height={dense ? 52 : 24}
          />
          <YAxis
            tickFormatter={(v: number) => `${v}pts`}
            tick={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: c.tick }}
            tickLine={false}
            axisLine={false}
            tickCount={5}
            width={48}
          />
          <Tooltip content={<WaterfallTooltip />} cursor={{ fill: c.cursorFill }} />
          <ReferenceLine y={0} stroke={c.axisLine} />
          <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="bar" stackId="w" isAnimationActive={false} radius={[2, 2, 2, 2]}>
            {rows.map((row) => (
              <Cell key={row.label} fill={COLOR[row.color ?? "total"]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
