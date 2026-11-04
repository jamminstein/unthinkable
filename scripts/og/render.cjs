// Lay out and screenshot the equation field. Called by build.py with one JSON argument.
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const o = JSON.parse(process.argv[2]);
  const posts = JSON.parse(fs.readFileSync(o.posts, 'utf8')).posts;
  const G = JSON.parse(fs.readFileSync(o.obstacle, 'utf8'));
  G.bits = Array.from(G.bits, (c) => (c === '1' ? 1 : 0));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200 * o.K, height: 630 * o.K }, deviceScaleFactor: 1 });
  await page.goto('file://' + o.page);
  const res = await page.evaluate(([p, g, oo]) => window.compose(p, g, oo), [posts, G, o]);
  console.log(JSON.stringify(res));
  if (res.placed !== posts.length) throw new Error(`placed ${res.placed} of ${posts.length}`);
  await page.locator('#stage').screenshot({ path: o.out });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
