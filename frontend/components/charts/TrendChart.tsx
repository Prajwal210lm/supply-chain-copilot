"use client";

import {
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Chart } from "@/lib/demo";
import { shortMonth } from "@/lib/demo";

const css = (name: string) =>
  typeof window === "undefined"
    ? undefined
    : getComputedStyle(document.documentElement).getPropertyValue(name).trim();

type TooltipPayload = { payload?: { label: string; formatted: string } };

function TrendTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length || !payload[0].payload) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-line bg-surface px-2.5 py-1.5 font-mono text-xs text-ink shadow-sm">
      <span className="text-ink-3">{shortMonth(p.label)}</span>{" "}
      <span className="font-semibold">{p.formatted}</span>
    </div>
  );
}

export default function TrendChart({ chart }: { chart: Chart }) {
  const data = chart.data.map((d) => ({ ...d }));
  const min = data.reduce((a, b) => (b.value < a.value ? b : a));

  return (
    <div className="h-56 w-full sm:h-64" data-chart="line">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 14, bottom: 4, left: -14 }}>
          <XAxis
            dataKey="label"
            tickFormatter={shortMonth}
            tick={{ fontSize: 10.5, fill: css("--ink-3"), fontFamily: "var(--font-spline-mono)" }}
            axisLine={{ stroke: css("--line-2") }}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={18}
          />
          <YAxis
            domain={["dataMin - 1", "dataMax + 0.5"]}
            tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            tick={{ fontSize: 10.5, fill: css("--ink-3"), fontFamily: "var(--font-spline-mono)" }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip content={<TrendTooltip />} cursor={{ stroke: css("--line-2"), strokeDasharray: "3 3" }} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={css("--accent")}
            strokeWidth={2}
            dot={{ r: 2.5, fill: css("--accent"), strokeWidth: 0 }}
            activeDot={{ r: 4, fill: css("--accent-deep"), strokeWidth: 0 }}
            isAnimationActive={false}
          />
          {/* the year's trough, computed from the data itself */}
          <ReferenceDot
            x={min.label}
            y={min.value}
            r={4.5}
            fill={css("--highlight")}
            stroke="var(--surface)"
            strokeWidth={1.5}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
