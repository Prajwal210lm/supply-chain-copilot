import raw from "./demo_conversation.json";

/* ---------------------------------------------------------------------------
   Typed access to data/demo_conversation.json (synced by scripts/sync-demo.mjs).
   Every number the page shows comes from this file or is derived from it.
--------------------------------------------------------------------------- */

export type ChartPoint = {
  label: string;
  value: number;
  formatted: string;
  color: "green" | "red" | "total" | null;
};

export type Chart = {
  type: "line" | "waterfall" | "stat_card" | "bar";
  title: string;
  data: ChartPoint[];
  axes: { x: string; y: string } | null;
};

export type Period = { grain: string; start: string; end: string };

export type Spec = {
  spec_type: string;
  metric: string;
  period?: Period;
  period_a?: Period;
  period_b?: Period;
  dimension?: string;
  time_grain?: string;
  grain?: string;
  filters?: { dimension: string; values: string[] }[];
};

export type Usage = {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
};

export type TurnResponse = {
  type: string;
  spec: Spec;
  echo_bar: string;
  narration: string | null;
  narration_withheld: boolean | null;
  chart: Chart | null;
  sql: string | null;
  options: string[] | null;
  suggestions: string[] | null;
  message: string | null;
  usage: Usage;
};

export type Turn = { question: string; response: TurnResponse };

const data = raw as unknown as { placeholder: boolean; turns: Turn[] };

export const turns: Turn[] = data.turns;

export const threadCostUsd: number = turns.reduce(
  (sum, t) => sum + t.response.usage.cost_usd,
  0,
);

/* ---- display helpers ------------------------------------------------------ */

const METRIC_NAMES: Record<string, string> = {
  otif_pct: "OTIF %",
  on_time_pct: "On-Time %",
  in_full_pct: "In-Full %",
  fill_rate_pct: "Fill Rate %",
  revenue: "Revenue",
  order_count: "Order Count",
  avg_order_value: "Average Order Value",
  inventory_value: "Inventory Value",
  days_of_cover: "Days of Cover",
  stockout_count: "Stockout Count",
  avg_supplier_lead_time: "Avg Supplier Lead Time",
};

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export function formatMonth(iso: string): string {
  const [y, m] = iso.split("-");
  const idx = Number(m) - 1;
  return MONTHS[idx] ? `${MONTHS[idx]} ${y}` : iso;
}

export function shortMonth(iso: string): string {
  const idx = Number(iso.split("-")[1]) - 1;
  return MONTHS[idx] ?? iso;
}

function formatPeriod(p: Period): string {
  if (p.start === p.end) return formatMonth(p.start);
  return `${formatMonth(p.start)} – ${formatMonth(p.end)}`;
}

export type EchoField = { label: string; value: string; accent?: boolean };

/** The echo bar's structured fields, derived deterministically from the spec
 *  the model actually emitted plus the backend's own echo string (which knows
 *  registry facts the spec doesn't carry, e.g. line-grain OTIF variants). */
export function echoFields(spec: Spec, echoText?: string): EchoField[] {
  const fields: EchoField[] = [
    { label: "metric", value: METRIC_NAMES[spec.metric] ?? spec.metric, accent: true },
  ];

  if (spec.spec_type === "change_decomposition" && spec.period_a && spec.period_b) {
    fields.push({
      label: "window",
      value: `${formatPeriod(spec.period_a)} → ${formatPeriod(spec.period_b)}`,
    });
  } else if (spec.period) {
    fields.push({ label: "window", value: formatPeriod(spec.period) });
  }

  fields.push({ label: "cut by", value: spec.dimension ?? "—" });

  const filters = spec.filters ?? [];
  fields.push({
    label: "filter",
    value:
      filters.length > 0
        ? filters.map((f) => `${f.dimension} = ${f.values.join(", ")}`).join("; ")
        : "—",
  });

  const grain = echoText?.includes("line grain")
    ? "line"
    : (spec.time_grain ?? spec.grain ?? (spec.period?.grain || "month"));
  fields.push({ label: "grain", value: grain });

  return fields;
}

export function specTypeLabel(spec: Spec): string {
  return spec.spec_type === "change_decomposition" ? "decomposition" : "metric query";
}

/* ---------------------------------------------------------------------------
   Context-carry diff. Purely presentational: given the fields of a turn and
   the fields of the turn before it in the SAME thread, mark which values the
   interpreter carried forward and which it changed. This makes multi-turn
   context — otherwise an invisible achievement — legible on screen.

   Fields that are "—" in both turns get no marker: technically inherited, but
   labelling an absent filter as carried-forward is noise, not signal.
--------------------------------------------------------------------------- */
export type FieldOrigin = "inherited" | "changed";

export function echoFieldOrigins(
  fields: EchoField[],
  prevFields: EchoField[] | null,
): Record<string, FieldOrigin> {
  if (!prevFields) return {};
  const prev = new Map(prevFields.map((f) => [f.label, f.value]));
  const out: Record<string, FieldOrigin> = {};
  for (const f of fields) {
    if (!prev.has(f.label)) continue;
    const before = prev.get(f.label);
    if (f.value === "—" && before === "—") continue;
    out[f.label] = f.value === before ? "inherited" : "changed";
  }
  return out;
}
