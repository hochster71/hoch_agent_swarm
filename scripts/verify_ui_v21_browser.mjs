import { chromium } from 'playwright';

const base = process.env.PERT_BASE_URL || 'http://127.0.0.1:8765';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

try {
  await page.goto(`${base}/ui-v2`, { waitUntil: 'networkidle', timeout: 30000 });

  const title = await page.locator('h1').innerText({ timeout: 10000 });
  const normalizedTitle = title.toUpperCase();
  if (!normalizedTitle.includes('OPERATOR CONSOLE V2.1')) {
    throw new Error(`UI_V21_TITLE: FAIL got=${title}`);
  }

  const tabs = ['Command', 'Pods', 'Revenue', 'Evidence', 'PERT', 'Watchdog'];

  for (const tab of tabs) {
    const btn = page.getByRole('button', { name: tab });
    await btn.waitFor({ state: 'visible', timeout: 10000 });
    await btn.click();

    const appText = await page.locator('#app').innerText({ timeout: 10000 });

    if (!appText || appText.trim().length < 20) {
      throw new Error(`UI_V21_TAB_BLANK: FAIL tab=${tab}`);
    }

    if (appText.includes('undefined')) {
      throw new Error(`UI_V21_UNDEFINED: FAIL tab=${tab}`);
    }

    if (appText.includes('API Error')) {
      throw new Error(`UI_V21_API_ERROR: FAIL tab=${tab}`);
    }
  }

  await page.getByRole('button', { name: 'Watchdog' }).click();
  await page.locator('text=Source Freshness Detail').waitFor({ state: 'visible', timeout: 10000 });

  console.log('UI_V21_BROWSER: PASS');
} finally {
  await browser.close();
}
