/**
 * ════════════════════════════════════════════════════════════════════════
 *  سبحة — لقطات المرجع بدقّة ×٣ (لوضوح الرموز والخطوط عند العرض والتكبير)
 * ════════════════════════════════════════════════════════════════════════
 *  تُنتج خمس لقطات بأسماء «ساعة-*.png» في screenshots/:
 *    الرئيسية · العداد · القراءة · الإتمام · التقييم والملاحظات
 *
 *  لماذا ×٣؟ عند تكبير الصورة (أو عرضها على شاشة كبيرة) تبقى الأيقونات
 *  المتجهة والخطوط حادّة بلا تدرّج ضبابي — وهذا هو الغرض من هذه اللقطات.
 *
 *  التشغيل:
 *     cd tests && npm install puppeteer     # مرّة واحدة
 *     node tools/shots-3x.mjs
 * ════════════════════════════════════════════════════════════════════════
 */
import puppeteer from '../tests/node_modules/puppeteer/lib/esm/puppeteer/puppeteer.js';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SIM = 'file://' + path.join(HERE, '..', 'simulator.html');
const SHOTS = path.join(HERE, '..', 'screenshots');

const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] });
const page = await browser.newPage();
await page.setViewport({ width: 420, height: 920, deviceScaleFactor: 3 });   // ×٣
await page.goto(SIM, { waitUntil: 'load' });
await new Promise(r => setTimeout(r, 600));

const run = src => page.evaluate(async code => {
  await new Function('return (async()=>{' + code + '})()')();
  await new Promise(r => requestAnimationFrame(r));
  await new Promise(r => setTimeout(r, 120));
}, src);

// كل لقطة: حالة نظيفة (لا تلقين · لا رسالة عابرة · قائمة من أعلاها)
const shots = [
  ['ساعة-الرئيسية@3x.png', "hideDone(); closeMenu(); stopPrompt(); S.home=true; S.recent=[1,0,3]; S.c=12; renderHome(); render(); applyLayout();"],
  ['ساعة-العداد@3x.png',   "hideDone(); closeMenu(); stopPrompt(); S.home=false; S.si=0; S.ii=1; S.c=7; S.read=false; render(); applyLayout();"],
  ['ساعة-القراءة@3x.png',  "hideDone(); closeMenu(); S.home=false; S.si=1; S.ii=0; S.read=true; render(); applyLayout(); startPrompt();"],
  ['ساعة-الإتمام@3x.png',  "closeMenu(); stopPrompt(); hideDone(); S.home=false; S.si=0; S.ii=SETS[0].items.length-1; S.c=SETS[0].items[S.ii].n; S.done=false; S.start=Date.now()-214000; render(); advanceOrFinish('tap');"],
  ['ساعة-التقييم@3x.png',  "hideDone(); stopPrompt(); S.home=false; S.read=false; S.cMode=0; render(); applyLayout(); openMenu('support');"],
];

for (const [name, setup] of shots) {
  await run("if (typeof stopPrompt==='function') stopPrompt(); el.toast.classList.remove('on');");
  await run(setup);
  await new Promise(r => setTimeout(r, 650));      // استقرار أي انتقال
  const el = await page.$('#screen');
  await el.screenshot({ path: path.join(SHOTS, name) });
  const { width, height } = await page.evaluate(() => {
    const s = document.getElementById('wrap') || document.getElementById('screen');
    return { width: s.clientWidth, height: s.clientHeight };
  });
  console.log(`  ✔ ${name}  (${width}×${height} منطقي ⇒ ${width * 3}×${height * 3} بكسل)`);
}

await browser.close();
const refs = fs.readdirSync(SHOTS).filter(f => f.startsWith('ساعة-') && f.endsWith('.png')).length;
const all = fs.readdirSync(SHOTS).filter(f => f.endsWith('.png')).length;
console.log(`\n  المجموع: ${refs} لقطة مرجع ×٣ · ${all} صورة في screenshots/`);
