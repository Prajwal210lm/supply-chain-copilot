"use client";

import { scrollToLiveCardWithPulse } from "@/lib/scrollToLiveCard";

/** A single in-context pointer from the demo's framing paragraph to the
 *  live question card below — the only "this part is live" cue in the
 *  page body, deliberately not repeated as section labels elsewhere. The
 *  nav carries its own small badge pointing at the same card. */
export default function LiveNudge() {
  function handleClick(e: React.MouseEvent<HTMLAnchorElement>) {
    e.preventDefault();
    scrollToLiveCardWithPulse();
  }

  return (
    <a
      href="#live-question-card"
      onClick={handleClick}
      className="mt-3 inline-flex items-center gap-1.5 font-mono text-[12px] text-ink-3 underline decoration-line-2 underline-offset-4 transition-colors hover:text-accent-ink hover:decoration-accent-line"
    >
      <span aria-hidden="true">↓</span> Ask your own question live
    </a>
  );
}
