"use client";

/** A single in-context pointer from the demo's framing paragraph to the
 *  live question card below — the only "this part is live" cue on the
 *  page, deliberately not repeated as nav or section labels elsewhere.
 *  Smooth-scrolls to the card and gives it a one-shot arrival pulse. */
export default function LiveNudge() {
  function handleClick(e: React.MouseEvent<HTMLAnchorElement>) {
    e.preventDefault();
    const el = document.getElementById("live-question-card");
    if (!el) return;

    const pulse = () => {
      el.classList.remove("live-nudge-pulse");
      void el.offsetWidth; // restart the animation on a rapid re-click
      el.classList.add("live-nudge-pulse");
      setTimeout(() => el.classList.remove("live-nudge-pulse"), 650);
    };

    // If the card is already basically in view, pulse immediately — no
    // scroll is coming, so there's nothing to wait for. Otherwise wait for
    // the scroll to actually finish before pulsing: firing on click alone
    // means the 600ms pulse plays out while the card is still off-screen,
    // and the user arrives to see nothing happen.
    const top = el.getBoundingClientRect().top;
    if (top >= 0 && top <= window.innerHeight * 0.5) {
      pulse();
      return;
    }

    let fired = false;
    const onScrollEnd = () => {
      if (fired) return;
      fired = true;
      window.removeEventListener("scrollend", onScrollEnd);
      clearTimeout(fallback);
      pulse();
    };
    // Safety net for browsers without `scrollend` (Safari < 17.4) or the
    // rare case it never fires.
    const fallback = setTimeout(() => {
      if (fired) return;
      fired = true;
      window.removeEventListener("scrollend", onScrollEnd);
      pulse();
    }, 1500);
    window.addEventListener("scrollend", onScrollEnd);

    el.scrollIntoView({ behavior: "smooth", block: "start" });
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
