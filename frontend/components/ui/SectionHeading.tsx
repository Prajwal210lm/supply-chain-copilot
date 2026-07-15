import Kicker from "./Kicker";
import Reveal from "./Reveal";

/** Every section opens with the same rhythm: kicker, headline, one-line intro. */
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
    <Reveal className="max-w-3xl">
      <Kicker>{kicker}</Kicker>
      <h2 className="mt-3 font-display text-[1.75rem] leading-[1.15] font-semibold tracking-[-0.015em] text-ink sm:text-4xl">
        {title}
      </h2>
      {intro ? (
        <p className="mt-4 text-[15px] leading-relaxed text-ink-2 sm:text-base">
          {intro}
        </p>
      ) : null}
    </Reveal>
  );
}
