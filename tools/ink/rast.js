// node rast.js jobs.json : each job {svg, png, w, h}; renders SVG files to transparent PNGs in Chromium
const { chromium } = require('playwright');
const fs = require('fs');
const FONTS = ['UnifrakturMaguntia','PirataOne','GrenzeGotisch','MrDafoe','PinyonScript','GreatVibes','Italianno','NewRocker','Rye','Sancreek','CinzelDecorative'];
const css = FONTS.map(f => `@font-face{font-family:'${f}';src:url('data:font/ttf;base64,${fs.readFileSync('/tmp/claude-0/ink/fonts/'+f+'.ttf').toString('base64')}')}`).join('\n');
(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2]));
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1024, height: 1024 }, deviceScaleFactor: 1 });
  for (const j of jobs) {
    await p.setViewportSize({ width: j.w, height: j.h });
    const svg = fs.readFileSync(j.svg, 'utf8');
    await p.setContent(`<html><head><style>${css} html,body{margin:0;background:transparent}</style></head><body>${svg}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: j.png, omitBackground: true, clip: { x: 0, y: 0, width: j.w, height: j.h } });
  }
  await b.close();
})();
