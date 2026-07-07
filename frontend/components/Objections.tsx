import Panel from "./ui/Panel";
import SectionHeading from "./ui/SectionHeading";

// Between measurement and scope: the questions a sharp interviewer would
// actually ask, answered from the real architecture — native <details>
// so keyboard and screen-reader behavior come free.

const OBJECTIONS: Array<{ q: string; a: string }> = [
  {
    q: "Why not just let the model write SQL?",
    a: "Because then safety becomes a filter arguing with an attacker. Here the model can only emit a typed QuerySpec — eleven metric enums, seven dimension values, bounded periods — so “ignore your instructions and drop the table” isn’t a jailbreak to catch, it’s a parse error. The SQL is written by a compiler from validated fields, and every user-derived value is bound as a query parameter, never spliced into the statement text.",
  },
  {
    q: "How do you know 96.7% is real and not cherry-picked?",
    a: "The 80-question golden set was written and frozen before the interpreter existed, with every expected answer pinned in the repo. All four runs are reported, including the worst — near-miss dipped to 86.7% in one run and the range is printed on this page. The adversarial slice is a deploy-blocking gate at 100%: one wrong refusal, or one answered injection, stops the release. And the two questions it got wrong are named above, not averaged away.",
  },
  {
    q: "What happens when the model gets the metric wrong?",
    a: "That failure mode is why the echo bar exists. The interpretation — metric, window, cut, filters — is printed between the question and the answer, so a wrong reading is visible before the number gets trusted. Structurally wrong specs are caught by six validators; honestly ambiguous questions get a clarification with concrete options. The residual risk is a confidently wrong but catalog-valid spec — which is exactly why the interpretation is always on screen instead of hidden in a log.",
  },
  {
    q: "Can a user exfiltrate data through prompt injection?",
    a: "The model’s output never reaches the database as text. Words from the question can only land in typed spec fields; values are bound as SQL parameters; the connection is read-only by construction; results are row-capped; and the narration can only reference the computed result object — the render gate withholds anything it can’t trace. An injected instruction can, at worst, produce a refusal or a visibly wrong spec. In four measured runs, twenty-five adversarial attempts produced twenty-five correct refusals.",
  },
  {
    q: "Why not use RAG instead of NL-to-SQL?",
    a: "RAG answers questions whose evidence lives in unstructured documents. This data is relational with a fixed schema — the correct retrieval is a SQL query, and correctness means exact aggregation, not top-k similarity. Embedding 149,000 order lines and hoping the right chunks surface would trade a solvable compilation problem for an unsolvable recall one. Wrong tool. NL → typed spec → compiled SQL is the boring, testable one.",
  },
];

export default function Objections() {
  return (
    <section id="objections" className="mx-auto w-full max-w-3xl scroll-mt-20 px-5 sm:px-8">
      <SectionHeading
        kicker="Hard questions"
        title="The five things a sharp interviewer would ask."
      />

      <Panel className="overflow-hidden">
        {OBJECTIONS.map((item, i) => (
          <details key={item.q} className={`group ${i > 0 ? "border-t border-line" : ""}`}>
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-[15px] font-medium text-ink hover:bg-accent-glow [&::-webkit-details-marker]:hidden">
              {item.q}
              <span
                aria-hidden
                className="shrink-0 font-mono text-sm text-faint transition-transform group-open:rotate-90"
              >
                ▸
              </span>
            </summary>
            <p className="px-5 pb-5 text-[15px] leading-relaxed text-slate">{item.a}</p>
          </details>
        ))}
      </Panel>
    </section>
  );
}
