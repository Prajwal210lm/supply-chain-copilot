import { chromium } from "playwright";

const base = process.argv[2] ?? "http://localhost:3111";
const failures = [];
const check = (ok, label) => {
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}`);
  if (!ok) failures.push(label);
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
page.on("pageerror", (e) => errors.push(String(e)));

await page.goto(base, { waitUntil: "networkidle" });

// the live card has its own visual identity and heading
await page.locator("[data-live-thread]").scrollIntoViewIfNeeded();
await page.waitForTimeout(400);
check(
  (await page.getByText("This one is live.").count()) === 1,
  "live section has its own heading, distinct from the demo",
);
check((await page.getByText("ask your own question").count()) === 1, "live section kicker present");

// counter starts full
check(
  (await page.locator("[data-remaining]").textContent()).trim().startsWith("5 of 5"),
  "counter starts at 5 of 5",
);

// Q1: real question through the UI, manual fill + submit
await page.locator("#live-question").fill("What was the fill rate in May 2026?");
await page.locator("form button[type='submit']").click();
await page.locator("[data-live-thread] article").first().waitFor({ timeout: 45000 });
const t1 = page.locator("[data-live-thread] article").first();
check((await t1.locator("[data-echo-bar]").count()) === 1, "live turn 1 renders an echo bar");
check(
  (await t1.locator("[data-chart='stat-card'], [data-chart='line'], [data-chart='waterfall']").count()) >= 1,
  "live turn 1 renders a chart",
);
// Narration is written by a real model call each run and can be legitimately
// withheld by the render gate (R1-R4) on any given response — that is the
// system working as designed, not a defect. Log it either way; don't fail
// the suite on withholding, since that would make this test flaky against
// its own honesty guarantee.
const narr1 = await t1
  .locator("p.max-w-prose")
  .first()
  .textContent()
  .catch(() => "");
if (narr1 && narr1.length > 30) {
  console.log(`INFO  live turn 1 narration rendered (${narr1.slice(0, 60)}…)`);
} else {
  console.log("INFO  live turn 1 narration withheld by the render gate on this run (chart still renders)");
}
check((await t1.locator("[data-sql-toggle]").count()) === 1, "live turn 1 has a SQL toggle");
check(
  (await page.locator("[data-remaining]").textContent()).trim().startsWith("4 of 5"),
  "counter decremented to 4",
);

// Q2: follow-up that only works with context, manual fill + submit
await page.locator("#live-question").fill("And in June?");
await page.locator("form button[type='submit']").click();
await page.waitForFunction(() => document.querySelectorAll("[data-live-thread] article").length >= 2, null, {
  timeout: 45000,
});
const t2 = page.locator("[data-live-thread] article").nth(1);
await page.waitForTimeout(300);
const echo2 = await t2.locator("[data-echo-bar] dd").first().textContent();
check(/fill rate/i.test(echo2 ?? ""), `follow-up carried context: metric field = "${echo2}"`);
const window2 = await t2.locator("[data-echo-bar] dd").nth(1).textContent();
check(/jun 2026/i.test(window2 ?? ""), `follow-up window resolved to "${window2}"`);
check(
  (await page.locator("[data-remaining]").textContent()).trim().startsWith("3 of 5"),
  "counter decremented to 3",
);

// Q3: a suggested chip fills the input and submits on its own
const chipText = "What's the average supplier lead time for Anadolu?";
await page.getByRole("button", { name: chipText }).click();
await page.waitForFunction(() => document.querySelectorAll("[data-live-thread] article").length >= 3, null, {
  timeout: 45000,
});
const t3 = page.locator("[data-live-thread] article").nth(2);
const q3Heading = await t3.locator("h3").textContent();
check(
  (q3Heading ?? "").includes("average supplier lead time for Anadolu"),
  `suggested chip submitted its own question (got "${q3Heading}")`,
);
check(
  (await page.locator("[data-remaining]").textContent()).trim().startsWith("2 of 5"),
  "counter decremented to 2 after chip submission",
);

// scroll each turn into view so the reveal-on-scroll animation settles
// before screenshotting (cosmetic only; DOM presence was already asserted)
for (const t of [t1, t2, t3]) {
  await t.scrollIntoViewIfNeeded();
  await page.waitForTimeout(150);
}

// localStorage persisted across all three submissions
const stored = await page.evaluate(() => localStorage.getItem("scc-live-used-v1"));
check(stored === "3", `localStorage tracks usage (got ${stored})`);

check(errors.length === 0, `no console errors (got ${errors.length}${errors.length ? ": " + errors.slice(0, 3).join(" | ") : ""})`);

await page.screenshot({ path: "D:/.cache/temp/shots-rebuild/live-e2e.png", fullPage: false });
await page.locator("[data-live-thread]").screenshot({ path: "D:/.cache/temp/shots-rebuild/live-thread.png" });

// exhausted state, forced via localStorage (no further real spend)
await page.evaluate(() => localStorage.setItem("scc-live-used-v1", "5"));
await page.reload({ waitUntil: "networkidle" });
await page.locator("[data-live-thread]").scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
check(await page.locator("#live-question").isDisabled(), "exhausted: input is disabled");
check(
  (await page.getByText("used all 5 questions. The demo above replays the full investigation.").count()) === 1,
  "exhausted: calm message present",
);
check((await page.locator("[data-remaining]").count()) === 0, "exhausted: counter badge hidden");
await page.locator("[data-live-thread]").screenshot({ path: "D:/.cache/temp/shots-rebuild/live-exhausted.png" });

await browser.close();

if (failures.length) {
  console.log(`\n${failures.length} FAILED`);
  process.exit(1);
}
console.log("\nLive E2E passed.");
