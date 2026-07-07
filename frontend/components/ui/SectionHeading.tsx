import Kicker from "./Kicker";

// Every section opens the same way: kicker -> display headline -> a
// one-line intro in the secondary tier. Rhythm is the design system.
export default function SectionHeading({
  kicker,
  title,
  intro,
}: {
  kicker: string;
  title: string;
  intro?: React.ReactNode;
}) {
  return (
    <div className="mb-10 flex flex-col gap-3 sm:mb-12">
      <Kicker>{kicker}</Kicker>
      <h2 className="type-section text-ink">{title}</h2>
      {intro ? <p className="type-body max-w-2xl text-slate">{intro}</p> : null}
    </div>
  );
}
