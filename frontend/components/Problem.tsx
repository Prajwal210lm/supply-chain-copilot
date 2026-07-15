import BeforeAfter from "./BeforeAfter";
import SectionHeading from "./ui/SectionHeading";

export default function Problem() {
  return (
    <section id="problem" aria-label="The problem" className="scroll-mt-20">
      <SectionHeading
        kicker="the problem"
        title="The answer is in the ERP. Getting it out costs two days."
        intro={
          <>
            A demand planner at Mawarid wants to know why OTIF dropped in March. Today
            that question is a ticket, an analyst, an Excel pull, and a meeting sometime
            next week. The real cost is not the analyst&rsquo;s afternoon. It is the
            decisions taken on stale numbers while the answer sits in a queue, and the
            questions that never get asked because asking is expensive.
          </>
        }
      />
      <div className="mt-10">
        <BeforeAfter />
      </div>
    </section>
  );
}
