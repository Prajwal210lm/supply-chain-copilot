// Typed access to lib/demo_conversation.json — a synced copy of
// data/demo_conversation.json (see scripts/sync-demo.mjs), which is the
// saved output of five real pipeline runs. The page renders this file
// directly; nothing on the demo path calls an API.

import demoJson from "./demo_conversation.json";

export type ChartPoint = {
  label: string;
  value: number | null;
  formatted: string;
  color: string | null; // waterfall: "green" | "red" | "total"
};

export type ChartData = {
  type: "line" | "bar_horizontal" | "waterfall" | "stat_card";
  title: string;
  data: ChartPoint[];
  axes: { x: string | null; y: string | null };
};

export type Filter = { dimension: string; values: string[] };

export type Period = { grain: string; start: string; end: string };

export type Spec = {
  spec_type: string;
  metric: string;
  period?: Period;
  period_a?: Period;
  period_b?: Period;
  dimension?: string;
  time_grain?: string | null;
  filters?: Filter[];
  top_n?: number;
  sort?: string;
};

export type Usage = {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
};

export type TurnResponse = {
  type: string;
  spec: Spec;
  echo_bar: string | null;
  result: Record<string, unknown> | null;
  narration: string | null;
  narration_withheld: string | null;
  chart: ChartData | null;
  sql: string | null;
  usage: Usage;
};

export type Turn = { question: string; response: TurnResponse };

export const demoTurns: Turn[] = (demoJson as { turns: Turn[] }).turns;

// Static catalog metadata (display names for the 11 metrics) — reference
// data, mirrored from copilot/registry.py's display_name column.
const METRIC_DISPLAY: Record<string, string> = {
  otif_pct: "OTIF %",
  on_time_pct: "On-Time %",
  in_full_pct: "In-Full %",
  fill_rate_pct: "Fill Rate %",
  revenue: "Revenue",
  order_count: "Order Count",
  avg_order_value: "Avg Order Value",
  inventory_value: "Inventory Value",
  days_of_cover: "Days of Cover",
  stockout_count: "Stockout Count",
  avg_supplier_lead_time: "Average Supplier Lead Time",
};

export type EchoField = { label: string; value: string };

const MONTH_ABBR = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function monthLabel(iso: string): string {
  // "2025-01" -> "Jan 2025"
  const month = MONTH_ABBR[Number(iso.slice(5, 7)) - 1];
  return month ? `${month} ${iso.slice(0, 4)}` : iso;
}

// Display formatting for a spec period — mirrors copilot/dateutil.py's
// period_label so the echo bar reads identically to the backend's own
// labels wherever the result object doesn't already carry one.
function periodLabel(period: Period): string {
  if (period.grain === "week") {
    return period.start === period.end ? period.start : `${period.start} to ${period.end}`;
  }
  if (period.start === period.end) return monthLabel(period.start);
  const startMonth = Number(period.start.slice(5, 7));
  const endMonth = Number(period.end.slice(5, 7));
  const sameYear = period.start.slice(0, 4) === period.end.slice(0, 4);
  if (sameYear && [1, 4, 7, 10].includes(startMonth) && endMonth === startMonth + 2) {
    return `Q${(startMonth - 1) / 3 + 1} ${period.start.slice(0, 4)}`;
  }
  return `${monthLabel(period.start)} to ${monthLabel(period.end)}`;
}

// The structured reading of the question — derived from the validated
// spec plus the result's period labels, never from model prose.
export function echoFields(turn: Turn): EchoField[] {
  const { spec, result, echo_bar } = turn.response;
  const fields: EchoField[] = [];

  fields.push({
    label: "metric",
    value: METRIC_DISPLAY[spec.metric] ?? spec.metric,
  });

  const r = (result ?? {}) as Record<string, string | undefined>;
  if (spec.spec_type === "change_decomposition") {
    fields.push({
      label: "window",
      value: `${r.period_b_label ?? spec.period_b?.start} vs ${r.period_a_label ?? spec.period_a?.start}`,
    });
  } else if (r.period_label) {
    fields.push({ label: "window", value: r.period_label });
  } else if (spec.period) {
    fields.push({ label: "window", value: periodLabel(spec.period) });
  }

  if (spec.time_grain) {
    fields.push({
      label: "series",
      value: spec.time_grain === "week" ? "weekly" : "monthly",
    });
  }

  if (spec.dimension) {
    fields.push({ label: "cut by", value: spec.dimension });
  }

  for (const f of spec.filters ?? []) {
    fields.push({ label: "filter", value: `${f.dimension} = ${f.values.join(", ")}` });
  }

  if (echo_bar?.includes("line grain")) {
    fields.push({ label: "grain", value: "line level" });
  }

  return fields;
}

export function formatTokens(usage: Usage): string {
  const total = usage.input_tokens + usage.output_tokens;
  return `${total.toLocaleString("en-US")} tokens · $${usage.cost_usd.toFixed(3)}`;
}
