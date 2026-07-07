// Drives the built page in headless Chromium and checks the verification
// list: all 5 turns render with real chart SVGs, echo bars show
// structured interpretation, spec/SQL toggles work, nav scroll-spy
// highlights, objections expand, og assets serve, 404 is branded,
// reduced-motion shows everything, layout holds at 390px, console clean.
// Usage: node scripts/verify-page.mjs <baseURL>   (default http://localhost:3100)
import { chromium } from "playwright";

const base = process.argv[2] ?? "http://localhost:3100";
const failures = [];
const check = (ok, label) => {
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}`);
  if (!ok) failures.push(label);
};

const browser = await chromium.launch();

for (const viewport of [
  { name: "desktop 1440px", width: 1440, height: 900 },
  { name: "mobile 390px", width: 390, height: 844 },
]) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));

  await page.goto(base, { waitUntil: "networkidle" });
  console.log(`\n--- ${viewport.name} ---`);

  // All 5 turns present with their questions
  const turnCount = await page.locator("ol > li[id^='turn-']").count();
  check(turnCount === 5, `5 demo turns render (got ${turnCount})`);

  // Echo bars: one per turn, with structured fields
  const echoCount = await page.getByText("Interpreted as").count();
  check(echoCount === 5, `5 echo bars render (got ${echoCount})`);
  const metricFields = await page.locator("dt", { hasText: /^metric$/ }).count();
  check(metricFields === 5, `every echo bar has a METRIC field (got ${metricFields})`);
  const filterField = await page.getByText("supplier = Anadolu").count();
  check(filterField === 1, "turn 3 echo bar shows its filter (supplier = Anadolu)");

  // Charts: turn 1 line + two waterfalls render real SVG paths/bars
  const t1Svg = await page.locator("#turn-1 .recharts-line").count();
  check(t1Svg === 1, "turn 1 renders a real line chart");
  const waterfalls = await page.locator(".recharts-bar-rectangle").count();
  check(waterfalls > 10, `waterfall bars render (got ${waterfalls} rects)`);
  const stat3 = await page.locator("#turn-3 .font-display", { hasText: "41.4 days" }).count();
  const stat5 = await page.locator("#turn-5 .font-display", { hasText: "93.9%" }).count();
  check(stat3 === 1 && stat5 === 1, `both stat cards show their formatted values (t3=${stat3}, t5=${stat5})`);

  // Spec toggle reveals JSON
  await page.locator("#turn-2 button", { hasText: "view spec" }).click();
  const specVisible = await page.locator("#turn-2 pre", { hasText: '"spec_type": "change_decomposition"' }).isVisible();
  check(specVisible, "spec toggle reveals the validated spec JSON");

  // SQL toggle reveals compiled SQL
  await page.locator("#turn-1 button", { hasText: "show compiled SQL" }).click();
  const sqlVisible = await page.locator("#turn-1 pre", { hasText: "SELECT" }).isVisible();
  check(sqlVisible, "SQL toggle reveals compiled SQL");

  // New sections
  check((await page.locator("section#objections details").count()) === 5, "5 objection collapsibles present");
  await page.locator("section#objections summary").first().click();
  const objOpen = await page.locator("section#objections details[open] p").first().isVisible();
  check(objOpen, "objection expands on click");
  const beforeAfter = await page.getByText("With the copilot").count();
  check(beforeAfter >= 1, "before/after comparison present");

  // Nav + scroll-spy
  check((await page.locator("nav a[href^='#']").count()) >= 5, "nav renders section anchors");
  await page.locator("#measurement").scrollIntoViewIfNeeded();
  await page.waitForTimeout(700);
  const activeAnchor = await page.locator("nav a[aria-current='true']").getAttribute("href");
  check(activeAnchor === "#measurement", `scroll-spy highlights measurement (got ${activeAnchor})`);

  // No horizontal overflow at this viewport
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  check(overflow <= 0, `no horizontal overflow (delta ${overflow}px)`);

  // Sections + footer links
  for (const id of ["conversation", "how", "measurement", "objections", "scope"]) {
    check((await page.locator(`#${id}`).count()) === 1, `section #${id} present`);
  }
  const portfolioLinks = await page.locator("footer a[href*='vercel.app']").count();
  check(portfolioLinks === 3, `3 portfolio links in footer (got ${portfolioLinks})`);

  await page.screenshot({
    path: `${process.env.SHOT_DIR ?? "."}/p4-${viewport.width}.png`,
    fullPage: true,
  });

  check(consoleErrors.length === 0, `no console errors (got ${consoleErrors.length}${consoleErrors.length ? ": " + consoleErrors.slice(0, 3).join(" | ") : ""})`);
  await page.close();
}

// OG + favicon assets served
const assetPage = await browser.newPage();
for (const asset of ["/og.png", "/favicon.png", "/icon.svg"]) {
  const res = await assetPage.request.get(base + asset);
  check(res.status() === 200, `${asset} serves 200 (got ${res.status()})`);
}

// OG meta present in the HTML head
await assetPage.goto(base, { waitUntil: "domcontentloaded" });
const ogMeta = await assetPage.locator("meta[property='og:image']").getAttribute("content");
check(Boolean(ogMeta && ogMeta.includes("og.png")), `og:image meta present (got ${ogMeta})`);

// 404 page is branded
const notFound = await assetPage.request.get(base + "/this-does-not-exist");
check(notFound.status() === 404, "unknown route returns 404");
await assetPage.goto(base + "/this-does-not-exist", { waitUntil: "domcontentloaded" });
const notFoundText = await assetPage.getByText("This query returned no results").count();
check(notFoundText === 1, "404 page carries the branded refusal");
await assetPage.close();

// Reduced motion: everything visible without any animation running
const rmPage = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  reducedMotion: "reduce",
});
await rmPage.goto(base, { waitUntil: "networkidle" });
const heroVisible = await rmPage.locator("h1").isVisible();
const revealHidden = await rmPage.evaluate(() => {
  const els = Array.from(document.querySelectorAll("[data-reveal]"));
  return els.filter((el) => getComputedStyle(el).opacity !== "1").length;
});
check(heroVisible && revealHidden === 0, `reduced-motion: all reveal sections visible (hidden=${revealHidden})`);

// Keyboard: skip link is the first focusable element and becomes visible
await rmPage.keyboard.press("Tab");
const skipFocused = await rmPage.evaluate(
  () => document.activeElement?.classList.contains("skip-link") ?? false,
);
check(skipFocused, "skip-to-content link is the first focusable element");
await rmPage.close();

await browser.close();

if (failures.length) {
  console.log(`\n${failures.length} check(s) FAILED`);
  process.exit(1);
}
console.log("\nAll checks passed.");
