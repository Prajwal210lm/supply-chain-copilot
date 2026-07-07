// Copies data/demo_conversation.json (repo root, produced by
// data/build_demo_conversation.py against the live pipeline) into
// frontend/lib/ so the app is self-contained when the deploy root is
// frontend/. Runs on predev/prebuild. If the repo-level source is absent
// (e.g. a shallow deploy) but a previously synced copy exists, the copy
// is kept; if neither exists, fail loudly — the page is this data.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "..", "..", "data", "demo_conversation.json");
const dest = join(here, "..", "lib", "demo_conversation.json");

if (existsSync(source)) {
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(source, dest);
  console.log("[sync-demo] copied data/demo_conversation.json -> lib/");
} else if (existsSync(dest)) {
  console.log("[sync-demo] source missing; keeping existing lib copy");
} else {
  console.error("[sync-demo] no demo_conversation.json found at " + source);
  process.exit(1);
}
