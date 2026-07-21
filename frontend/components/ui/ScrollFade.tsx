/** Right-edge fade gradient: the minimum viable signal that a container
 *  scrolls horizontally. `to` names a CSS custom property already defined
 *  in globals.css, so the gradient always fades into whatever surface it
 *  sits on (the paper-white chart panel, the dark SQL block, etc). */
export default function ScrollFade({ to = "--surface" }: { to?: string }) {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-y-0 right-0 w-10"
      style={{ background: `linear-gradient(to right, transparent, var(${to}))` }}
    />
  );
}
