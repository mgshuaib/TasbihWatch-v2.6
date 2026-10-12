import puppeteer from './node_modules/puppeteer/lib/esm/puppeteer/puppeteer.js';
const b = await puppeteer.launch({ args:['--no-sandbox','--disable-dev-shm-usage'] });
const p = await b.newPage();
await p.setViewport({ width: 420, height: 920, deviceScaleFactor: 2 });
await p.goto('file:///home/user/TasbihWatch/simulator.html', { waitUntil: 'load' });
await new Promise(r=>setTimeout(r,400));
const m = await p.evaluate(() => {
  S.home = true; S.si=1; S.ii=3; S.c=12; S.recent=[1,0,3]; S.cMode=1; renderHome(); render(); applyLayout();
  const sc = document.getElementById('screen').getBoundingClientRect();
  const view = document.getElementById('homeView');
  const bad = [];
  view.querySelectorAll('*').forEach(e => {
    const st = getComputedStyle(e); if (st.display==='none' || parseFloat(st.opacity)===0) return;
    const r = e.getBoundingClientRect(); if (!r.width && !r.height) return;
    const over = Math.max(0, sc.top-r.top, r.bottom-sc.bottom, sc.left-r.left, r.right-sc.right);
    if (over > 1) bad.push((e.id?'#'+e.id:'.'+String(e.className).split(' ')[0])+' '+over.toFixed(0)+'px');
  });
  const g = document.getElementById('hGrid');
  const tr = [...view.querySelectorAll('[data-open]')].map(t=>t.getBoundingClientRect());
  const mc = [...view.querySelectorAll('.mchip')].map(c=>c.getBoundingClientRect());
  return { bad, scroll: g.scrollHeight-g.clientHeight, gridH: Math.round(g.getBoundingClientRect().height),
           tile: [Math.round(tr[0].width), Math.round(tr[0].height)],
           chip: [Math.round(mc[0].width), Math.round(mc[0].height)],
           selected: view.querySelectorAll('.mchip.on').length };
});
console.log(JSON.stringify(m));
const el = await p.$('#screen'); await el.screenshot({ path: '/tmp/home4.png' });
await b.close();
