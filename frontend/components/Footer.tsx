const SERIES = [
  {
    tag: "P1",
    name: "Liquidity Lens",
    href: "https://supply-chain-liquidity-lens.vercel.app",
  },
  {
    tag: "P2",
    name: "Supplier Resilience Radar",
    href: "https://supplier-resilience-radar.vercel.app",
  },
  {
    tag: "P3",
    name: "OTIF Root-Cause Engine",
    href: "https://otif-root-cause-engine.vercel.app",
  },
];

const CONTACT = [
  { label: "GitHub", href: "https://github.com/Prajwal210lm/supply-chain-copilot" },
  { label: "LinkedIn", href: "https://linkedin.com/in/prajwal-prakash-naregal" },
  { label: "Email", href: "mailto:prajwal210.techfest@gmail.com" },
];

// The most important elements on the site: nothing is more than one
// click from contacting the person who built it.
export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line sm:mt-32">
      <div className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-8 sm:py-14">
        <p className="type-kicker mb-4 text-faint">The rest of the series</p>
        <ul className="flex flex-col gap-1">
          {SERIES.map((project) => (
            <li key={project.tag}>
              <a
                href={project.href}
                target="_blank"
                rel="noopener noreferrer"
                className="group -mx-2 inline-flex min-h-11 items-baseline gap-3 rounded-md px-2 py-2 hover:bg-accent-glow"
              >
                <span className="font-mono text-xs text-faint">{project.tag}</span>
                <span className="text-sm font-medium text-ink group-hover:text-accent-deep">
                  {project.name}
                </span>
                <span className="hidden font-mono text-[11px] text-faint sm:inline">
                  {project.href.replace("https://", "")}
                </span>
              </a>
            </li>
          ))}
        </ul>

        <div className="mt-8 flex flex-wrap gap-x-2 gap-y-2 border-t border-line pt-6">
          {CONTACT.map((c) => (
            <a
              key={c.label}
              href={c.href}
              {...(c.href.startsWith("http")
                ? { target: "_blank", rel: "noopener noreferrer" }
                : {})}
              className="-my-1 rounded-md px-2 py-2 font-mono text-xs text-slate hover:bg-accent-wash hover:text-accent-deep"
            >
              {c.label}
            </a>
          ))}
        </div>

        <p className="type-mono mt-6 text-faint">
          Built with Python, FastAPI, DuckDB, Pydantic, Claude, Next.js, Recharts.
        </p>
        <p className="mt-3 font-mono text-[10px] leading-relaxed text-faint">
          All data is synthetic. Mawarid Distribution is fictional. Built to demonstrate
          architecture and methodology.
        </p>
      </div>
    </footer>
  );
}
