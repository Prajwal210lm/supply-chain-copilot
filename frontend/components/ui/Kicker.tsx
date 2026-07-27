/** The eyebrow: a short accent rule, then uppercase mono with wide tracking.
 *  One voice for every section. */
export default function Kicker({
  children,
  tone = "accent",
}: {
  children: React.ReactNode;
  tone?: "accent" | "muted";
}) {
  const accent = tone === "accent";
  return (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className={`h-px w-6 shrink-0 ${accent ? "bg-accent" : "bg-line-2"}`}
      />
      <span
        className={`font-mono text-[11px] uppercase tracking-[0.22em] ${
          accent ? "text-accent-ink" : "text-ink-3"
        }`}
      >
        {children}
      </span>
    </span>
  );
}
