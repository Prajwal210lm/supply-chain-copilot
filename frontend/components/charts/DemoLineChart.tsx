"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartData, ChartPoint } from "@/lib/demo";
import { chart as c } from "@/lib/tokens";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthTick(label: string): string {
  // "2025-01" -> "Jan"
  const m = Number(label.slice(5, 7));
  return MONTHS[m - 1] ?? label;
}

function EchoTooltip({
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

export default function DemoLineChart({ chart }: { chart: ChartData }) {
  return (
    <div className="h-64 w-full sm:h-72" role="img" aria-label={`Line chart: ${chart.title}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chart.data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={c.grid} />
          <XAxis
            dataKey="label"
            tickFormatter={monthTick}
            tick={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: c.tick }}
            tickLine={false}
            axisLine={{ stroke: c.axisLine }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[
              (dataMin: number) => Math.floor(dataMin - 0.5),
              (dataMax: number) => Math.ceil(dataMax + 0.5),
            ]}
            allowDecimals={false}
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: c.tick }}
            tickLine={false}
            axisLine={false}
            tickCount={5}
            width={44}
          />
          <Tooltip content={<EchoTooltip />} cursor={{ stroke: c.cursor }} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={c.accent}
            strokeWidth={2}
            dot={{ r: 2.5, fill: c.accent, strokeWidth: 0 }}
            activeDot={{ r: 4, fill: c.accent, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
