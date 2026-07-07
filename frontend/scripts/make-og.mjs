// Generates public/og.png (1200x630) and public/favicon.png (32x32) by
// screenshotting token-styled HTML in headless Chromium — same fonts,
// same palette as the page, no design drift between site and card.
import { chromium } from "playwright";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const pub = join(here, "..", "public");

const og = `<!doctype html><html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Spline+Sans+Mono:wght@400;600&display=swap');
  * { margin: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 630px; background: #fafaf9; color: #1e1e24;
    font-family: 'Fraunces', Georgia, serif; padding: 80px;
    display: flex; flex-direction: column; justify-content: space-between;
    border-bottom: 10px solid #4338ca;
  }
  .kicker { font-family: 'Spline Sans Mono', monospace; font-size: 20px;
    letter-spacing: 0.12em; text-transform: uppercase; color: #8e8e99; font-weight: 600; }
  h1 { font-size: 76px; line-height: 1.12; font-weight: 600; letter-spacing: -0.02em; }
  .stat { display: flex; align-items: baseline; gap: 18px; }
  .stat b { font-size: 54px; color: #3730a3; font-weight: 600; }
  .stat span { font-family: 'Spline Sans Mono', monospace; font-size: 22px; color: #52525b; }
</style></head><body>
  <p class="kicker">Supply Chain Copilot &middot; Mawarid Distribution</p>
  <h1>The answer is in the data.<br>Getting it out takes days.</h1>
  <div class="stat"><b>96.7%</b><span>spec accuracy &middot; measured over four independent runs</span></div>
</body></html>`;

const fav = `<!doctype html><html><head><meta charset="utf-8"><style>
  * { margin: 0; } body { width: 64px; height: 64px; }
  div { width: 64px; height: 64px; background: #4338ca; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font: 600 40px Georgia, serif; }
</style></head><body><div>?</div></body></html>`;

const browser = await chromium.launch();

const ogPage = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await ogPage.setContent(og, { waitUntil: "networkidle" });
await ogPage.screenshot({ path: join(pub, "og.png") });

const favPage = await browser.newPage({ viewport: { width: 64, height: 64 } });
await favPage.setContent(fav);
await favPage.screenshot({ path: join(pub, "favicon.png") });

await browser.close();
console.log("wrote public/og.png and public/favicon.png");
