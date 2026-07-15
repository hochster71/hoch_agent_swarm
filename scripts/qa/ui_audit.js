// HELM UI QA/AUDIT harness — headless Chromium
// Loads each UI, captures JS/console errors, verifies live data rendered,
// checks cross-nav links resolve, screenshots each. Writes JSON verdict.
const { chromium } = require('playwright');
const fs = require('fs');

const BASE = 'http://127.0.0.1:8770';
const OUT = '/Users/michaelhoch/hoch_agent_swarm/coordination/qa/ui_audit';
fs.mkdirSync(OUT, { recursive: true });

const UIS = [
  { id: 'roadmap',  path: '/roadmap', wait: 4000, expect: [/PHASE|SOAK|DOORSTEP|NORTH/i], forbid: [/undefined%|NaN|9600/] },
  { id: 'command',  path: '/command', wait: 3500, expect: [/HELM|COMMAND|CHAIN|SOAK/i], forbid: [/undefined|NaN/] },
  { id: 'jspace',   path: '/jspace',  wait: 4000, expect: [/J-SPACE|VERIFIED|HASH|INTEGRITY|AGENT/i], forbid: [/undefined%|NaN/] },
  { id: 'brain',    path: '/brain',   wait: 4500, expect: [/./], forbid: [] }, // WebGL canvas; check no JS error
  { id: 'founder',  path: '/founder', wait: 3500, expect: [/FOUNDER|APPROVE|QUEUE|NORTH|J-SPACE/i], forbid: [/undefined|NaN/] },
];

(async () => {
  const browser = await chromium.launch();
  const results = [];
  for (const ui of UIS) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const jsErrors = [], consoleErrors = [], badReqs = [];
    page.on('pageerror', e => jsErrors.push(String(e.message || e)));
    page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('requestfailed', r => badReqs.push(`${r.url()} :: ${r.failure()?.errorText}`));
    page.on('response', r => { if (r.status() >= 400) badReqs.push(`${r.status()} ${r.url()}`); });

    let httpStatus = null, bodyText = '', navLinks = [];
    try {
      const resp = await page.goto(BASE + ui.path, { waitUntil: 'domcontentloaded', timeout: 15000 });
      httpStatus = resp ? resp.status() : null;
      await page.waitForTimeout(ui.wait);
      bodyText = (await page.evaluate(() => document.body.innerText || '')).slice(0, 6000);
      navLinks = await page.evaluate(() =>
        Array.from(document.querySelectorAll('a[href]'))
          .map(a => a.getAttribute('href'))
          .filter(h => h && !h.startsWith('http') && h !== '#'));
      await page.screenshot({ path: `${OUT}/${ui.id}.png`, fullPage: false });
    } catch (e) {
      jsErrors.push('NAV_FAIL: ' + String(e.message || e));
    }

    const expectHits = ui.expect.map(rx => rx.test(bodyText));
    const forbidHits = ui.forbid.filter(rx => rx.test(bodyText)).map(rx => rx.source);
    const contentOK = expectHits.every(Boolean);

    // resolve unique nav links
    const uniq = [...new Set(navLinks)];
    const linkChecks = [];
    for (const h of uniq) {
      try {
        const u = h.startsWith('/') ? BASE + h : BASE + '/' + h;
        const r = await page.request.get(u, { timeout: 8000 });
        linkChecks.push({ href: h, status: r.status() });
      } catch (e) { linkChecks.push({ href: h, status: 'ERR' }); }
    }

    const verdict = (httpStatus === 200 && jsErrors.length === 0 && contentOK && forbidHits.length === 0
                     && linkChecks.every(l => l.status === 200)) ? 'PASS'
                    : (httpStatus === 200 && jsErrors.length === 0 && contentOK) ? 'PASS_WITH_NOTES' : 'FAIL';

    results.push({ id: ui.id, httpStatus, verdict, contentOK,
      jsErrors, consoleErrors: consoleErrors.slice(0, 8),
      badRequests: [...new Set(badReqs)].slice(0, 8),
      forbiddenText: forbidHits, navLinks: linkChecks,
      textSample: bodyText.replace(/\s+/g, ' ').slice(0, 320) });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(`${OUT}/audit.json`, JSON.stringify(results, null, 2));
  for (const r of results) {
    console.log(`\n[${r.verdict}] ${r.id}  http=${r.httpStatus}  content=${r.contentOK}`);
    if (r.jsErrors.length) console.log('   JS_ERR:', r.jsErrors.slice(0,3).join(' | '));
    if (r.badRequests.length) console.log('   BAD_REQ:', r.badRequests.slice(0,4).join(' | '));
    if (r.forbiddenText.length) console.log('   FORBIDDEN:', r.forbiddenText.join(', '));
    const badLinks = r.navLinks.filter(l => l.status !== 200);
    if (badLinks.length) console.log('   BAD_LINKS:', badLinks.map(l=>`${l.href}=${l.status}`).join(', '));
    else if (r.navLinks.length) console.log(`   links OK (${r.navLinks.length})`);
    console.log('   sample:', r.textSample.slice(0,140));
  }
  console.log('\nWROTE', `${OUT}/audit.json`);
})();
