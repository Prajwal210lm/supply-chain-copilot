/** Four dots, one per eval run, positioned vertically by that run's score.
 *  Identical scores sit on one flat line (visibly stable); a spread scatters
 *  and gets an explicit range bar with its endpoints labelled.
 *
 *  Each strip scales to its own values rather than a shared 0–100 axis: on an
 *  absolute axis a 6.6-point spread would be invisible, and the point here is
 *  to show variance honestly, not to flatter it. The endpoint labels keep the
 *  local scale from overstating the spread.
 *
 *  Laid out with CSS percentages rather than a stretched SVG viewBox so the
 *  dots stay perfectly round at every container width. */
export default function RunStrip({
  values,
  suffix = "%",
}: {
  values: number[];
  suffix?: string;
}) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const varies = max - min > 0.05;

  // Local domain, padded so dots never touch the band edges.
  const pad = varies ? (max - min) * 0.45 : 1;
  const lo = min - pad;
  const hi = max + pad;
  /** value -> % from the top of the band (0 = top, 100 = bottom) */
  const top = (v: number) => 100 - ((v - lo) / (hi - lo)) * 100;

  return (
    <div className="mt-3">
      <div
        className="relative h-7"
        role="img"
        aria-label={
          varies
            ? `Four eval runs, ranging ${min}${suffix} to ${max}${suffix}`
            : `Four eval runs, all ${max}${suffix}`
        }
      >
        {/* min / max guides */}
        {varies ? (
          <>
            <span
              className="absolute inset-x-4 border-t border-dashed border-line"
              style={{ top: `${top(max)}%` }}
            />
            <span
              className="absolute inset-x-4 border-t border-dashed border-line"
              style={{ top: `${top(min)}%` }}
            />
            {/* the range itself, drawn as a bar at the left edge */}
            <span
              className="absolute left-0 w-[2px] rounded-full bg-accent-line"
              style={{
                top: `${top(max)}%`,
                height: `${top(min) - top(max)}%`,
              }}
            />
          </>
        ) : (
          <span
            className="absolute inset-x-4 border-t border-accent-line"
            style={{ top: `${top(max)}%` }}
          />
        )}

        {values.map((v, i) => (
          <span
            key={i}
            className={`absolute h-[5px] w-[5px] -translate-x-1/2 -translate-y-1/2 rounded-full ${
              varies && v === min ? "bg-highlight" : "bg-accent"
            }`}
            style={{
              left: `${18 + i * 22}%`,
              top: `${top(v)}%`,
            }}
            title={`run ${i + 1}: ${v}${suffix}`}
          />
        ))}
      </div>
      <div className="flex items-baseline justify-between font-mono text-[9px] text-ink-3">
        <span>4 runs</span>
        <span>{varies ? `${min}${suffix} – ${max}${suffix}` : `all ${max}${suffix}`}</span>
      </div>
    </div>
  );
}
