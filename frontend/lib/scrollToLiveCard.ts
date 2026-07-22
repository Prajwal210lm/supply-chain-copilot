/** Smooth-scrolls to the live question card and pulses it once it actually
 *  settles into view. Shared by every "this points at the live section"
 *  affordance on the site (the in-context nudge, the nav badge) so the
 *  arrival feel is identical no matter where the click came from. */
export function scrollToLiveCardWithPulse() {
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
