import type { Turn as TurnData } from "@/lib/demo";
import EchoBar from "./EchoBar";
import SqlToggle from "./SqlToggle";
import TrendChart from "./charts/TrendChart";
import WaterfallChart from "./charts/WaterfallChart";
import StatCard from "./charts/StatCard";
import Panel from "./ui/Panel";
import Reveal from "./ui/Reveal";

function ChartFor({ turn }: { turn: TurnData }) {
  const chart = turn.response.chart;
  if (!chart) return null;
  if (chart.type === "line") return <TrendChart chart={chart} />;
  if (chart.type === "waterfall") return <WaterfallChart chart={chart} />;
  if (chart.type === "stat_card") return <StatCard chart={chart} />;
  return null;
}

/** One question, answered: the question in the reader's voice, the echo bar
 *  in the machine's, then the computed chart, the gated narration, the SQL. */
export default function Turn({
  turn,
  index,
  annotation,
}: {
  turn: TurnData;
  index: number;
  annotation?: string;
}) {
  const { response } = turn;
  return (
    <div>
      {annotation ? (
        <Reveal className="my-8 flex items-center gap-3 sm:my-10">
          <span aria-hidden="true" className="h-px flex-1 bg-line" />
          <p className="max-w-md text-center text-[13.5px] italic text-ink-3">{annotation}</p>
          <span aria-hidden="true" className="h-px flex-1 bg-line" />
        </Reveal>
      ) : null}

      <Reveal as="article" id={`turn-${index}`} className="scroll-mt-28">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-[11px] text-ink-3">
            {String(index).padStart(2, "0")}
          </span>
          <h3 className="font-display text-xl font-semibold tracking-[-0.01em] text-ink sm:text-[1.45rem]">
            &ldquo;{turn.question}&rdquo;
          </h3>
        </div>

        <div className="mt-4 space-y-4">
          <EchoBar spec={response.spec} echoText={response.echo_bar} />

          <Panel className="px-4 py-4 sm:px-6 sm:py-5">
            {response.chart?.title && response.chart.type !== "stat_card" ? (
              <div className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-3">
                {response.chart.title}
              </div>
            ) : null}
            <ChartFor turn={turn} />
            {response.narration ? (
              <p className="mt-4 max-w-prose border-t border-line pt-4 text-[14.5px] leading-relaxed text-ink-2">
                {response.narration}
              </p>
            ) : null}
            {response.sql ? (
              <div className="mt-4">
                <SqlToggle sql={response.sql} />
              </div>
            ) : null}
          </Panel>
        </div>
      </Reveal>
    </div>
  );
}
