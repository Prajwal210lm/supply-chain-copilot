import Kicker from "./ui/Kicker";
import Reveal from "./ui/Reveal";

const PROJECTS = [
  {
    name: "Liquidity Lens",
    tag: "P1",
    desc: "Working-capital diagnostics for a distributor's cash cycle.",
    href: "https://supply-chain-liquidity-lens.vercel.app",
  },
  {
    name: "Supplier Resilience Radar",
    tag: "P2",
    desc: "Agentic supplier risk assessment with contract-grounded claims.",
    href: "https://supplier-resilience-radar.vercel.app",
  },
  {
    name: "OTIF Root-Cause Engine",
    tag: "P3",
    desc: "Four specialist agents attributing delivery failures to a cause.",
    href: "https://otif-root-cause-engine.vercel.app",
  },
];

const CONTACT = [
  {
    label: "GitHub",
    value: "github.com/Prajwal210lm/supply-chain-copilot",
    href: "https://github.com/Prajwal210lm/supply-chain-copilot",
  },
  {
    label: "LinkedIn",
    value: "linkedin.com/in/prajwal-b-006050228",
    href: "https://linkedin.com/in/prajwal-b-006050228",
  },
  { label: "Email", value: "prajwal210lm@gmail.com", href: "mailto:prajwal210lm@gmail.com" },
];

export default function Footer() {
  return (
    <footer aria-label="Contact and portfolio" className="border-t border-line bg-panel/50">
      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 sm:py-20">
        <Reveal className="max-w-2xl">
          <Kicker>the portfolio</Kicker>
          <h2 className="mt-3 font-display text-2xl font-semibold tracking-[-0.015em] text-ink sm:text-3xl">
            Project 4 of a four-project AI supply-chain portfolio.
          </h2>
          <p className="mt-4 text-[14.5px] leading-relaxed text-ink-2">
            Same method each time: pick an expensive operational question, build the
            system that answers it honestly, measure it before shipping, and publish the
            misses next to the wins.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            {CONTACT.map((c) => (
              <a
                key={c.label}
                href={c.href}
                {...(c.href.startsWith("http")
                  ? { target: "_blank", rel: "noopener noreferrer" }
                  : {})}
                className="rounded-lg border border-line-2 bg-surface px-4 py-2 font-mono text-[12px] text-ink-2 transition-colors hover:border-accent-line hover:text-accent-ink"
              >
                <span className="mr-2 text-ink-3">{c.label}</span>
                {c.value.replace("github.com/Prajwal210lm/", "…/")}
              </a>
            ))}
          </div>
        </Reveal>

        <Reveal delay={120} className="mt-14">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-3">
            the rest of the portfolio
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {PROJECTS.map((p) => (
              <a
                key={p.tag}
                href={p.href}
                target="_blank"
                rel="noopener noreferrer"
                className="glass lift group rounded-xl p-4"
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-display text-[15px] font-semibold text-ink group-hover:text-accent-ink">
                    {p.name}
                  </span>
                  <span className="font-mono text-[10px] text-ink-3">{p.tag}</span>
                </div>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-2">{p.desc}</p>
                <p className="mt-2 font-mono text-[10.5px] text-ink-3">
                  {p.href.replace("https://", "")}
                </p>
              </a>
            ))}
          </div>
        </Reveal>

        <div className="mt-14 flex flex-col gap-3 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-[10.5px] text-ink-3">
            Built with Python · FastAPI · DuckDB · Pydantic · Claude · Next.js ·
            Recharts · Tailwind
          </p>
          <p className="font-mono text-[10.5px] text-ink-3">Built by Prajwal B</p>
        </div>
        <p className="mt-3 font-mono text-[10.5px] text-ink-3">
          All data is synthetic. Mawarid Distribution is fictional.
        </p>
      </div>
    </footer>
  );
}
