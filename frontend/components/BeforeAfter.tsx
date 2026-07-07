import Panel from "./ui/Panel";

// The show-don't-tell moment between the problem and the proof: the same
// question, two processes. Rendered in the pipeline diagram's node
// language so it reads as part of one system. Static — the animated
// version of this idea belongs to the architecture section.

function FlowNode({ children, tone = "code" }: { children: string; tone?: "code" | "model" }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2.5 py-1.5 font-mono text-[11px] ${
        tone === "model"
          ? "border-accent bg-accent text-white"
          : "border-line bg-sunken text-ink"
      }`}
    >
      {children}
    </span>
  );
}

function Arrow() {
  return (
    <span aria-hidden className="font-mono text-[11px] text-faint">
      →
    </span>
  );
}

export default function BeforeAfter() {
  return (
    <section className="mx-auto w-full max-w-4xl px-5 sm:px-8">
      <div className="grid gap-4 sm:grid-cols-2">
        <Panel className="p-5">
          <p className="type-kicker mb-4 text-faint">Today</p>
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-2">
            <FlowNode>question</FlowNode>
            <Arrow />
            <FlowNode>ticket</FlowNode>
            <Arrow />
            <FlowNode>analyst</FlowNode>
            <Arrow />
            <FlowNode>Excel</FlowNode>
            <Arrow />
            <FlowNode>meeting</FlowNode>
            <Arrow />
            <FlowNode>answer</FlowNode>
          </div>
          <p className="type-mono mt-4 text-negative">~2 days</p>
        </Panel>

        <Panel className="p-5">
          <p className="type-kicker mb-4 text-accent-deep">With the copilot</p>
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-2">
            <FlowNode>question</FlowNode>
            <Arrow />
            <FlowNode tone="model">copilot</FlowNode>
            <Arrow />
            <FlowNode>answer</FlowNode>
          </div>
          <p className="type-mono mt-4 text-positive">~10 seconds, interpretation shown</p>
        </Panel>
      </div>
    </section>
  );
}
