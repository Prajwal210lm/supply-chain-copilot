/** The eyebrow: uppercase mono, wide tracking. One voice for every section. */
export default function Kicker({
  children,
  tone = "accent",
}: {
  children: React.ReactNode;
  tone?: "accent" | "muted";
}) {
  return (
    <span
      className={`font-mono text-[11px] uppercase tracking-[0.22em] ${
        tone === "accent" ? "text-accent-ink" : "text-ink-3"
      }`}
    >
      {children}
    </span>
  );
}
