// The human voice: the question rendered as quoted speech, in the serif
// italic. This is the page's recurring typographic beat — five of these
// pace the whole scroll.
export default function UserMessage({ question }: { question: string }) {
  return (
    <blockquote className="font-display text-2xl italic leading-snug tracking-tight text-ink sm:text-[1.75rem]">
      &ldquo;{question}&rdquo;
    </blockquote>
  );
}
