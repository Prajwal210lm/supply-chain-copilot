/** Shared card surface: raised on base, hairline border, quiet hover lift. */
export default function Panel({
  children,
  className = "",
  hover = false,
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-line bg-raised shadow-[0_1px_2px_rgba(33,29,23,0.04)] ${
        hover
          ? "transition-[transform,box-shadow] duration-300 motion-reduce:transition-none hover:-translate-y-0.5 hover:shadow-[0_6px_20px_rgba(33,29,23,0.07)] motion-reduce:hover:translate-y-0"
          : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}
