import { turns } from "@/lib/demo";
import LiveNudge from "./LiveNudge";
import SectionHeading from "./ui/SectionHeading";
import Turn from "./Turn";
import LiveThread from "./LiveThread";

/** Reader-voice glue between turns; the investigation's connective tissue. */
const ANNOTATIONS: Record<number, string> = {
  2: "The headline shows a dip. The natural next question: why?",
  3: "The decomposition points to SUP-07, Anadolu. What went wrong there?",
  4: "Was this spread across both DCs, or concentrated?",
  5: "And has it recovered?",
};

export default function Conversation() {
  return (
    <section id="conversation" aria-label="The demo conversation" className="scroll-mt-20">
      <SectionHeading
        kicker="the conversation"
        title="One incident, five questions"
        intro={
          <>
            In March 2026, Mawarid&rsquo;s OTIF dropped from 91.0% to 84.2%, the sharpest
            fall in two years of data. The thread below traces that drop from the headline
            to the supplier behind it, to the DC that took the damage, to the recovery.
            Every answer was produced by the live pipeline and saved; nothing here is a
            mock-up. Between each question and its answer sits the exact interpretation
            that produced it.
          </>
        }
      />
      <LiveNudge />

      {/* The thread is the centerpiece of the page: it sits on its own
          recessed rail so the five turns read as one continuous artifact
          rather than five loose cards. */}
      <div className="relative mt-10 sm:mt-12">
        <span
          aria-hidden="true"
          className="absolute inset-y-0 -left-3 hidden w-px bg-gradient-to-b from-transparent via-line-2 to-transparent sm:block"
        />
        <ol className="list-none space-y-10">
          {turns.map((t, i) => (
            <li key={i}>
              <Turn turn={t} index={i + 1} annotation={ANNOTATIONS[i + 1]} />
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-14 sm:mt-16">
        <LiveThread demoTurnCount={turns.length} />
      </div>
    </section>
  );
}
