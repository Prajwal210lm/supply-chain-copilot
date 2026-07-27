/** Shared card surface. A layered glass plate: translucent warm-white wash,
 *  luminous 1px rim, inner top highlight, and a soft cast shadow so it reads
 *  as floating above the page rather than filled onto it. */
export default function Panel({
  children,
  className = "",
  hover = false,
  strong = false,
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  strong?: boolean;
}) {
  return (
    <div
      className={`rounded-xl ${strong ? "glass-strong" : "glass"} ${
        hover ? "lift" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}
