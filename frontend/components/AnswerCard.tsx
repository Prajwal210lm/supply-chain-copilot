import DemoBarChart from "./charts/DemoBarChart";
import DemoLineChart from "./charts/DemoLineChart";
import DemoWaterfallChart from "./charts/DemoWaterfallChart";
import StatCard from "./charts/StatCard";
import SQLToggle from "./SQLToggle";
import { formatTokens, type TurnResponse } from "@/lib/demo";

function ChartFor({ response }: { response: TurnResponse }) {
  const chart = response.chart;
  if (!chart) return null;
  const result = (response.result ?? {}) as Record<string, string | undefined>;
  switch (chart.type) {
    case "line":
      return <DemoLineChart chart={chart} />;
    case "waterfall":
      return <DemoWaterfallChart chart={chart} />;
    case "bar_horizontal":
      return <DemoBarChart chart={chart} />;
    case "stat_card":
      return <StatCard chart={chart} periodLabel={result.period_label} />;
  }
}

// The answer: chart on sunken ground, narration in the body voice, and a
// footer that keeps the receipts (compiled SQL, token cost) one click
// away without shouting. No card border of its own — the turn owns the
// framing, the panel owns the surface.
export default function AnswerCard({ response }: { response: TurnResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg bg-sunken px-3 pb-2 pt-3 sm:px-4 sm:pt-4">
        <ChartFor response={response} />
      </div>

      {response.narration ? (
        <p className="type-body max-w-prose text-ink">{response.narration}</p>
      ) : (
        <p className="max-w-prose text-sm italic leading-relaxed text-slate">
          Narration withheld by the render gate
          {response.narration_withheld ? ` (${response.narration_withheld})` : ""} — the chart
          and its numbers are still exact; only the unverifiable prose was dropped.
        </p>
      )}

      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2 border-t border-line pt-3">
        {response.sql ? <SQLToggle sql={response.sql} /> : <span />}
        <span className="type-mono shrink-0 text-faint">{formatTokens(response.usage)}</span>
      </div>
    </div>
  );
}
