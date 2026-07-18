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
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", e => errors.push(String(e)));

await page.goto(base, { waitUntil: "networkidle" });

// counter starts full
await page.locator("#live-question").scrollIntoViewIfNeeded();
await page.waitForTimeout(400);
check((await page.locator("[data-remaining]").textContent()).trim().startsWith("10 of 10"), "counter starts at 10 of 10");

// Q1: real question through the UI
await page.locator("#live-question").fill("What was the fill rate in May 2026?");
await page.locator("form button[type='submit']").click();
await page.locator("[data-live-thread] article").first().waitFor({ timeout: 45000 });
const t6 = page.locator("[data-live-thread] article").first();
check((await t6.locator("[data-echo-bar]").count()) === 1, "live turn 1 renders an echo bar");
check((await t6.locator("[data-chart='stat-card'], [data-chart='line'], [data-chart='waterfall']").count()) >= 1, "live turn 1 renders a chart");
const narr1 = await t6.locator("p.max-w-prose").first().textContent().catch(() => "");
check(Boolean(narr1 && narr1.length > 30), `live turn 1 has narration (${(narr1||"").slice(0,60)}…)`);
check((await t6.locator("[data-sql-toggle]").count()) === 1, "live turn 1 has a SQL toggle");
check((await page.locator("[data-remaining]").textContent()).trim().startsWith("9 of 10"), "counter decremented to 9");

// Q2: follow-up that only works with context
await page.locator("#live-question").fill("And in June?");
await page.locator("form button[type='submit']").click();
await page.waitForFunction(() => document.querySelectorAll("[data-live-thread] article").length >= 2, null, { timeout: 45000 });
const t7 = page.locator("[data-live-thread] article").nth(1);
await page.waitForTimeout(300);
const echo7 = await t7.locator("[data-echo-bar] dd").first().textContent();
check(/fill rate/i.test(echo7 ?? ""), `follow-up carried context: metric field = "${echo7}"`);
const window7 = await t7.locator("[data-echo-bar] dd").nth(1).textContent();
check(/jun 2026/i.test(window7 ?? ""), `follow-up window resolved to "${window7}"`);
check((await page.locator("[data-remaining]").textContent()).trim().startsWith("8 of 10"), "counter decremented to 8");

// divider present
check((await page.getByText("your questions").count()) >= 1, "live divider present");

// localStorage persisted
const stored = await page.evaluate(() => localStorage.getItem("scc-live-used-v1"));
check(stored === "2", `localStorage tracks usage (got ${stored})`);

check(errors.length === 0, `no console errors (got ${errors.length}${errors.length ? ": " + errors.slice(0,3).join(" | ") : ""})`);

await page.screenshot({ path: "D:/.cache/temp/shots-rebuild/live-e2e.png", fullPage: false });
await page.locator("[data-live-thread]").screenshot({ path: "D:/.cache/temp/shots-rebuild/live-thread.png" });
await browser.close();

if (failures.length) { console.log(`\n${failures.length} FAILED`); process.exit(1); }
console.log("\nLive E2E passed.");
