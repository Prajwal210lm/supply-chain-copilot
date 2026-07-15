/** A single real number with its label and provenance line. */
export default function StatTile({
  value,
  label,
  sub,
}: {
  value: string;
  label: string;
  sub: string;
}) {
  return (
    <div className="border-l-2 border-accent-line pl-4">
      <div className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-[2.1rem]">
        {value}
      </div>
      <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-2">
        {label}
      </div>
      <div className="mt-0.5 text-[12.5px] text-ink-3">{sub}</div>
    </div>
  );
}
