"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartData, ChartPoint } from "@/lib/demo";
import { chart as c } from "@/lib/tokens";

// Horizontal breakdown bars. No turn in the saved demo produces a
// breakdown_query, so this renders only when the demo data changes —
// it exists because the chart contract has four types, not three.

function BarTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded border border-line bg-raised px-2.5 py-1.5 font-mono text-xs text-ink shadow-sm">
      <span className="text-faint">{p.label}</span>{" "}
      <span className="font-medium">{p.formatted}</span>
    </div>
  );
}

export default function DemoBarChart({ chart }: { chart: ChartData }) {
  const height = Math.max(180, chart.data.length * 40 + 40);
  return (
    <div style={{ height }} className="w-full" role="img" aria-label={`Bar chart: ${chart.title}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chart.data}
          layout="vertical"
          margin={{ top: 4, right: 24, bottom: 0, left: 8 }}
        >
          <XAxis
            type="number"
            tick={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: c.tick }}
            tickLine={false}
            axisLine={{ stroke: c.axisLine }}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={120}
            tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: c.tickSoft }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<BarTooltip />} cursor={{ fill: c.cursorFill }} />
          <Bar dataKey="value" isAnimationActive={false} radius={[0, 2, 2, 0]} barSize={18}>
            {chart.data.map((p) => (
              <Cell key={p.label} fill={p.label === "All others" ? c.tick : c.accent} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
