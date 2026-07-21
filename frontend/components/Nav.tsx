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

/** Sticky nav with scroll-spy: the section currently in view is highlighted.
 *  Desktop keeps the full link row. Below the sm breakpoint, seven links
 *  never fit next to the wordmark, so mobile gets a hamburger that opens a
 *  slide-down drawer instead of a silently-clipped, no-affordance row. */
export default function Nav() {
  const [active, setActive] = useState<string>("");
  const [menuOpen, setMenuOpen] = useState(false);

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

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    const onResize = () => {
      if (window.innerWidth >= 640) setMenuOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [menuOpen]);

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

        {/* desktop: full link row, unchanged */}
        <div className="hidden items-center gap-1 sm:flex">
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

        {/* mobile: hamburger toggle, 44x44 */}
        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls="mobile-nav-drawer"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          onClick={() => setMenuOpen((v) => !v)}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md sm:hidden"
        >
          <span aria-hidden="true" className="relative block h-4 w-5">
            <span
              className={`absolute left-0 top-0 h-[1.5px] w-5 bg-ink transition-transform duration-200 motion-reduce:transition-none ${
                menuOpen ? "translate-y-[7px] rotate-45" : ""
              }`}
            />
            <span
              className={`absolute left-0 top-[7px] h-[1.5px] w-5 bg-ink transition-opacity duration-200 motion-reduce:transition-none ${
                menuOpen ? "opacity-0" : ""
              }`}
            />
            <span
              className={`absolute left-0 top-[14px] h-[1.5px] w-5 bg-ink transition-transform duration-200 motion-reduce:transition-none ${
                menuOpen ? "-translate-y-[7px] -rotate-45" : ""
              }`}
            />
          </span>
        </button>
      </nav>

      {menuOpen ? (
        <>
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
            className="fixed inset-x-0 top-14 z-40 h-[calc(100vh-3.5rem)] cursor-default bg-ink/20 sm:hidden"
          />
          <div
            id="mobile-nav-drawer"
            className="fixed inset-x-0 top-14 z-50 border-b border-line bg-paper shadow-lg sm:hidden"
          >
            <div className="flex flex-col gap-0.5 px-3 py-3">
              {LINKS.map((l) => (
                <a
                  key={l.id}
                  href={`#${l.id}`}
                  aria-current={active === l.id ? "true" : undefined}
                  onClick={() => setMenuOpen(false)}
                  className={`flex min-h-11 items-center rounded-md px-3.5 font-mono text-[13.5px] tracking-[0.04em] transition-colors ${
                    active === l.id
                      ? "bg-accent-tint text-accent-ink"
                      : "text-ink-2"
                  }`}
                >
                  {l.label}
                </a>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </header>
  );
}
