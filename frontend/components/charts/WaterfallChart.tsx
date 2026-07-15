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
import type { Chart } from "@/lib/demo";

const css = (name: string) =>
  typeof window === "undefined"
    ? undefined
    : getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/** Classic waterfall: an invisible offset bar positions each contribution at
 *  its running cumulative; the Total bar runs from zero. Green positive, red
 *  negative, neutral total — the only place those colors are allowed. */
function toWaterfall(chart: Chart) {
  let cum = 0;
  return chart.data.map((d) => {
    if (d.color === "total") {
      return { ...d, base: Math.min(0, d.value), span: Math.abs(d.value) };
    }
    const start = cum;
    cum += d.value;
    return { ...d, base: Math.min(start, cum), span: Math.abs(d.value) };
  });
}

function barColor(color: string | null): string {
  if (color === "green") return css("--pos") ?? "#15803d";
  if (color === "red") return css("--neg") ?? "#b91c1c";
  return css("--bar-neutral") ?? "#78716c";
}

type TooltipPayload = { payload?: { label: string; formatted: string } };

function WfTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length || !payload[0].payload) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-line bg-surface px-2.5 py-1.5 font-mono text-xs text-ink shadow-sm">
      <span className="text-ink-3">{p.label}</span>{" "}
      <span className="font-semibold">{p.formatted}</span>
    </div>
  );
}

export default function WaterfallChart({ chart }: { chart: Chart }) {
  const data = toWaterfall(chart);
  const wide = data.length > 6;

  return (
    <div className={wide ? "overflow-x-auto" : ""} data-chart="waterfall">
      <div className={`h-60 sm:h-64 ${wide ? "min-w-[600px]" : "w-full"}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 18, right: 8, bottom: 2, left: -18 }} barCategoryGap="24%">
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: css("--ink-3"), fontFamily: "var(--font-spline-mono)" }}
              axisLine={{ stroke: css("--line-2") }}
              tickLine={false}
              interval={0}
              angle={wide ? -34 : 0}
              textAnchor={wide ? "end" : "middle"}
              height={wide ? 44 : 24}
            />
            <YAxis
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}`}
              tick={{ fontSize: 10.5, fill: css("--ink-3"), fontFamily: "var(--font-spline-mono)" }}
              axisLine={false}
              tickLine={false}
              width={46}
            />
            <Tooltip content={<WfTooltip />} cursor={{ fill: css("--panel") }} />
            <ReferenceLine y={0} stroke={css("--line-2")} />
            {/* invisible positioning bar */}
            <Bar dataKey="base" stackId="wf" fill="transparent" isAnimationActive={false} />
            <Bar dataKey="span" stackId="wf" isAnimationActive={false} radius={[2, 2, 2, 2]}>
              {data.map((d) => (
                <Cell key={d.label} fill={barColor(d.color)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
