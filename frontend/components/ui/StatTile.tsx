import CountUp from "./CountUp";

/** A single real number with its label and provenance line. Pass `count` to
 *  animate the value up when it scrolls into view; omit it for values that
 *  aren't numeric. The accent rail thickens toward the number so the tile
 *  reads as measured off a scale. */
export default function StatTile({
  value,
  label,
  sub,
  count,
}: {
  value: string;
  label: string;
  sub: string;
  count?: { to: number; decimals?: number; prefix?: string; suffix?: string };
}) {
  return (
    <div className="group relative pl-4">
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-[2px] rounded-full bg-gradient-to-b from-accent via-accent-line to-transparent transition-opacity duration-200 group-hover:opacity-80"
      />
      <div className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-[2.1rem]">
        {count ? (
          <CountUp
            value={count.to}
            decimals={count.decimals ?? 0}
            prefix={count.prefix}
            suffix={count.suffix}
          />
        ) : (
          value
        )}
      </div>
      <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-2">
        {label}
      </div>
      <div className="mt-0.5 text-[12.5px] text-ink-3">{sub}</div>
    </div>
  );
}
