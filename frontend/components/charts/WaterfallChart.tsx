"use client";

import { useEffect, useRef, useState } from "react";
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
import type { Chart, ChartPoint } from "@/lib/demo";
import ScrollFade from "../ui/ScrollFade";

const MOBILE_BREAKPOINT = 640;

/** SSR-safe: renders false until mounted, then tracks the sm breakpoint. */
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return isMobile;
}

/** Adds `is-in` once the plot scrolls into view, which lets CSS grow the bars
 *  up from the baseline. Fires once. */
function useGrowOnView<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return { ref, inView };
}

const css = (name: string) =>
  typeof window === "undefined"
    ? undefined
    : getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/** Classic waterfall: an invisible offset bar positions each contribution at
 *  its running cumulative; the Total bar runs from zero. Green positive, red
 *  negative, neutral total — the only place those colors are allowed.
 *
 *  `floating`: when the mobile view trims to the top contributors, a true
 *  cumulative stack would misrepresent the story (the shown bars no longer
 *  sum to the total, since the rest were omitted). Floating mode draws every
 *  bar — including the omitted-aware subset — from zero on its own value, so
 *  nothing implies a running sum that isn't actually there. */
function toWaterfall(data: ChartPoint[], floating: boolean) {
  let cum = 0;
  return data.map((d) => {
    if (d.color === "total" || floating) {
      return { ...d, base: Math.min(0, d.value), span: Math.abs(d.value) };
    }
    const start = cum;
    cum += d.value;
    return { ...d, base: Math.min(start, cum), span: Math.abs(d.value) };
  });
}

/** Dashed step connectors at each running-total level, the convention that
 *  makes a waterfall readable as a cascade rather than a row of bars. Only
 *  meaningful in cumulative mode — in the trimmed mobile view the bars float
 *  from zero, so there is no continuous running total to trace. */
function connectorLevels(contributors: ChartPoint[], total: ChartPoint | null) {
  const out: { from: string; to: string; y: number }[] = [];
  let cum = 0;
  for (let i = 0; i < contributors.length; i++) {
    cum += contributors[i].value;
    const next = i + 1 < contributors.length ? contributors[i + 1] : total;
    if (!next) break;
    out.push({ from: contributors[i].label, to: next.label, y: cum });
  }
  return out;
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
    <div className="rounded-md border border-[var(--glass-rim)] bg-white/80 px-2.5 py-1.5 font-mono text-xs text-ink shadow-[var(--elev-2)] backdrop-blur-md">
      <span className="text-ink-3">{p.label}</span>{" "}
      <span className="font-semibold">{p.formatted}</span>
    </div>
  );
}

export default function WaterfallChart({ chart }: { chart: Chart }) {
  const isMobile = useIsMobile();
  const { ref, inView } = useGrowOnView<HTMLDivElement>();

  const contributors = chart.data.filter((d) => d.color !== "total");
  const total = chart.data.find((d) => d.color === "total") ?? null;

  // On mobile, more than 5 contributors would otherwise force a min-width
  // scroll container that clips the Total bar — the single most important
  // one — off the initial view. Trim to the top 5 by magnitude instead; the
  // Total bar (computed from ALL contributors, not just the shown subset)
  // always renders, and a caption discloses the trim.
  const trimmedForMobile = isMobile && contributors.length > 5;
  const shownContributors = trimmedForMobile
    ? [...contributors].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 5)
    : contributors;
  const chartData = total ? [...shownContributors, total] : shownContributors;

  const data = toWaterfall(chartData, trimmedForMobile);
  const wide = !trimmedForMobile && data.length > 6;
  const connectors = trimmedForMobile ? [] : connectorLevels(shownContributors, total);

  return (
    <div data-chart="waterfall">
      <div className={`relative ${wide ? "overflow-x-auto" : ""}`}>
        <div
          ref={ref}
          className={`chart-grow h-60 rounded-lg bg-sunken/70 sm:h-64 ${
            inView ? "is-in" : ""
          } ${wide ? "min-w-[600px]" : "w-full"}`}
        >
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
              {connectors.map((c) => (
                <ReferenceLine
                  key={`${c.from}-${c.to}`}
                  segment={[
                    { x: c.from, y: c.y },
                    { x: c.to, y: c.y },
                  ]}
                  stroke={css("--line-2")}
                  strokeDasharray="3 3"
                  strokeWidth={1}
                />
              ))}
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
        {wide ? <ScrollFade to="--surface" /> : null}
      </div>
      {trimmedForMobile ? (
        <p className="mt-2 font-mono text-[10.5px] text-ink-3">
          Showing top 5 of {contributors.length} contributors.
        </p>
      ) : null}
    </div>
  );
}
