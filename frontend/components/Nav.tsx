"use client";

import { useEffect, useState } from "react";

const LINKS = [
  { id: "problem", label: "Problem" },
  { id: "approach", label: "Approach" },
  { id: "conversation", label: "Demo" },
  { id: "how", label: "Design" },
  { id: "measurement", label: "Measurement" },
  { id: "scope", label: "Scope" },
  { id: "objections", label: "Objections" },
];

/** Sticky nav with scroll-spy: the section currently in view is highlighted. */
export default function Nav() {
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    const sections = LINKS.map((l) => document.getElementById(l.id)).filter(
      (el): el is HTMLElement => el !== null,
    );
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-25% 0px -60% 0px", threshold: [0, 0.1, 0.3] },
    );
    sections.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
      <nav
        aria-label="Sections"
        className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-5 sm:px-8"
      >
        <a
          href="#top"
          className="shrink-0 font-display text-[15px] font-semibold tracking-tight text-ink"
        >
          Supply Chain Copilot
        </a>
        <div className="flex items-center gap-1 overflow-x-auto">
          {LINKS.map((l) => (
            <a
              key={l.id}
              href={`#${l.id}`}
              aria-current={active === l.id ? "true" : undefined}
              className={`whitespace-nowrap rounded-md px-2.5 py-1.5 font-mono text-[11px] tracking-[0.06em] transition-colors ${
                active === l.id
                  ? "bg-accent-tint text-accent-ink"
                  : "text-ink-2 hover:text-ink"
              }`}
            >
              {l.label}
            </a>
          ))}
        </div>
      </nav>
    </header>
  );
}
