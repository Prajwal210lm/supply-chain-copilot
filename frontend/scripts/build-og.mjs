// Renders public/og.png (1200x630) and public/favicon.png (64x64) from
// HTML drawn with the app's own tokens, via Playwright. Run manually when
// the brand or the headline number changes:
//   node scripts/build-og.mjs
import { chromium } from "playwright";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const pub = join(here, "..", "public");

const og = `<!doctype html><html><head><meta charset="utf-8">
<style>
  @font-face { font-family: X; src: local("Arial"); }
  * { margin: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 630px; overflow: hidden; position: relative;
    background: #fbfaf7;
    font-family: "Segoe UI", Arial, sans-serif; color: #211d17;
  }
  .wash { position: absolute; inset: 0;
    background: radial-gradient(56rem 26rem at 78% -10%, #eeedfb, transparent 70%); }
  .frame { position: absolute; inset: 36px; border: 1px solid #e8e3d9; border-radius: 24px; background: rgba(255,255,255,.55); }
  .inner { position: absolute; inset: 0; padding: 64px 84px 60px; display: flex; flex-direction: column; justify-content: space-between; }
  .kicker { font-family: Consolas, monospace; font-size: 18px; letter-spacing: .24em; text-transform: uppercase; color: #3a30b4; }
  h1 { font-size: 54px; line-height: 1.08; letter-spacing: -0.015em; font-weight: 650; max-width: 900px; margin-top: 14px; }
  h1 .q { color: #4032c8; }
  .echo { display: inline-flex; gap: 40px; padding: 18px 26px; border: 1px solid #e8e3d9; border-left: 4px solid #4f46e5;
    border-radius: 14px; background: #f4f1ea; }
  .f { display: flex; flex-direction: column; gap: 7px; }
  .fl { font-family: Consolas, monospace; font-size: 14px; letter-spacing: .18em; text-transform: uppercase; color: #6b6353; }
  .fv { font-family: Consolas, monospace; font-size: 21px; color: #211d17; }
  .fv.a { color: #3a30b4; font-weight: 600; }
  .bottom { display: flex; align-items: flex-end; justify-content: space-between; }
  .stat { display: flex; align-items: baseline; gap: 18px; }
  .stat .n { font-size: 72px; font-weight: 700; letter-spacing: -0.02em; color: #211d17; line-height: 1; }
  .stat .l { font-family: Consolas, monospace; font-size: 16px; letter-spacing: .18em; text-transform: uppercase; color: #57503f; }
  .url { font-family: Consolas, monospace; font-size: 18px; color: #6b6353; }
</style></head><body>
  <div class="wash"></div>
  <div class="frame"></div>
  <div class="inner">
    <div>
      <div class="kicker">supply chain copilot</div>
      <h1><span class="q">&ldquo;Why did OTIF drop in March?&rdquo;</span><br>
      Answered in seconds, by code the model never touches.</h1>
    </div>
    <div class="echo">
      <div class="f"><span class="fl">metric</span><span class="fv a">OTIF %</span></div>
      <div class="f"><span class="fl">window</span><span class="fv">Feb &rarr; Mar 2026</span></div>
      <div class="f"><span class="fl">cut by</span><span class="fv">supplier</span></div>
      <div class="f"><span class="fl">grain</span><span class="fv">line</span></div>
    </div>
    <div class="bottom">
      <div class="stat"><div class="n">96.7%</div><div class="l">measured spec accuracy</div></div>
      <div class="url">supply-chain-copilot-nine.vercel.app</div>
    </div>
  </div>
</body></html>`;

const fav = `<!doctype html><html><head><style>
  * { margin: 0; } body { width: 64px; height: 64px; }
  .b { width: 64px; height: 64px; border-radius: 14px; background: #4032c8; position: relative; }
  svg { position: absolute; inset: 0; }
</style></head><body><div class="b">
  <svg viewBox="0 0 64 64"><path d="M22 20 L36 32 L22 44" fill="none" stroke="#fbfaf7" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="44" cy="44" r="5" fill="#f5a623"/></svg>
</div></body></html>`;

const browser = await chromium.launch();

const ogPage = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await ogPage.setContent(og, { waitUntil: "networkidle" });
await ogPage.screenshot({ path: join(pub, "og.png") });
console.log("wrote public/og.png");

const favPage = await browser.newPage({
  viewport: { width: 64, height: 64 },
  deviceScaleFactor: 2,
});
await favPage.setContent(fav, { waitUntil: "networkidle" });
await favPage.screenshot({ path: join(pub, "favicon.png"), omitBackground: true });
console.log("wrote public/favicon.png");

await browser.close();
