import Link from "next/link";
import Kicker from "@/components/ui/Kicker";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 px-5 text-center">
      <Kicker>404 · refusal</Kicker>
      <h1 className="type-section text-ink">This query returned no results.</h1>
      <p className="type-body max-w-md text-slate">
        Whatever was here doesn&rsquo;t resolve against the catalog. The conversation, the
        architecture, and the measurement are all on the main page.
      </p>
      <Link
        href="/"
        className="rounded-full border border-machine-line bg-machine px-5 py-2.5 type-small text-accent-deep hover:border-accent"
      >
        Back to the copilot
      </Link>
    </main>
  );
}
