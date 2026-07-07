import AnswerCard from "./AnswerCard";
import EchoBar from "./EchoBar";
import LiveInput from "./LiveInput";
import Panel from "./ui/Panel";
import SectionHeading from "./ui/SectionHeading";
import UserMessage from "./UserMessage";
import { demoTurns, echoFields } from "@/lib/demo";

// One-line guides before turns 2–5: what the user is doing and why.
// Visually quieter than the questions and answers — they narrate the
// investigation for a reader skimming it, they aren't the content.
const ANNOTATIONS: Record<number, string> = {
  1: "The headline shows a dip. The natural next question: why?",
  2: "The decomposition points at one supplier — Anadolu. What actually went wrong there?",
  3: "A six-week lead time on one supplier. Was the damage spread across both warehouses, or concentrated?",
  4: "Concentrated in Abu Dhabi. Three months on: has it recovered?",
};

export default function ConversationThread() {
  return (
    <section id="conversation" className="mx-auto w-full max-w-3xl scroll-mt-20 px-5 sm:px-8">
      <SectionHeading
        kicker="The investigation"
        title="One incident, five questions."
        intro={
          <>
            In March 2026, Mawarid&rsquo;s OTIF fell from 91.0% to 84.2% — the sharpest drop in
            two years of data. The thread below traces that drop from the headline number to
            the supplier behind it, to the warehouse that took the damage, to the recovery.
            Every answer was produced by the live pipeline and saved; between each question and
            its answer sits the exact interpretation that produced it.
          </>
        }
      />

      <Panel className="-mx-5 rounded-none border-x-0 sm:mx-0 sm:rounded-xl sm:border-x">
        <ol>
          {demoTurns.map((turn, i) => (
            <li
              key={turn.question}
              id={`turn-${i + 1}`}
              className={`scroll-mt-24 p-5 sm:p-8 ${i > 0 ? "border-t border-line" : ""}`}
            >
              <div className="mb-4 flex items-baseline gap-3">
                <span className="type-mono text-faint">{String(i + 1).padStart(2, "0")}</span>
                {ANNOTATIONS[i] ? (
                  <p className="text-sm italic leading-relaxed text-faint">{ANNOTATIONS[i]}</p>
                ) : null}
              </div>
              <div className="flex flex-col gap-4">
                <UserMessage question={turn.question} />
                <EchoBar fields={echoFields(turn)} spec={turn.response.spec} />
                <AnswerCard response={turn.response} />
              </div>
            </li>
          ))}
        </ol>
      </Panel>

      <LiveInput />
    </section>
  );
}
