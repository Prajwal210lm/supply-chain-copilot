"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const SECTIONS = [
  { id: "problem", label: "The Problem" },
  { id: "conversation", label: "Investigation" },
  { id: "how", label: "Architecture" },
  { id: "measurement", label: "Measurement" },
  { id: "scope", label: "Scope" },
];

// Sticky nav: transparent over the hero, bordered once scrolled past it.
// Scroll-spy via one IntersectionObserver over the five section roots.
// On mobile the anchor row horizontally scrolls — every target stays a
// one-tap link, no hamburger to excavate.
export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const targets = SECTIONS.map((s) => document.getElementById(s.id)).filter(
      (el): el is HTMLElement => el !== null,
    );
    if (!targets.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: [0, 0.2, 0.5] },
    );
    targets.forEach((t) => observer.observe(t));
    return () => observer.disconnect();
  }, []);

  return (
    <nav
      aria-label="Sections"
      className={`sticky top-0 z-50 bg-base/95 backdrop-blur-sm ${
        scrolled ? "border-b border-line" : "border-b border-transparent"
      }`}
    >
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
        <Link href="#problem" className="type-small shrink-0 text-ink hover:text-accent-deep">
          Supply Chain Copilot
        </Link>
        <div className="-mx-1 flex min-w-0 items-center gap-1 overflow-x-auto px-1">
          {SECTIONS.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              aria-current={active === section.id ? "true" : undefined}
              className={`whitespace-nowrap rounded-md px-2.5 py-2 font-mono text-[11px] ${
                active === section.id
                  ? "text-accent"
                  : "text-slate hover:bg-accent-wash hover:text-accent-deep"
              }`}
            >
              {section.label}
            </a>
          ))}
        </div>
      </div>
    </nav>
  );
}
