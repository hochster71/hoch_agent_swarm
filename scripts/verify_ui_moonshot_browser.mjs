import { chromium } from 'playwright';

const base = process.env.PERT_BASE_URL || 'http://127.0.0.1:8765';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });

try {
  await page.goto(`${base}/ui-moonshot`, { waitUntil: 'networkidle', timeout: 30000 });

  const body = await page.locator('body').innerText({ timeout: 10000 });
  const normalizedBody = body.toUpperCase();

  const required = [
    'HOCH PODS LIFTOFF CONTROL PLANE V2',
    'MISSION AUTHORITY',
    'LEADING AGENTS',
    'SWARM THEATER',
    'PERT CRITICAL PATH',
    'STALE / WATCHDOG',
    'EVIDENCE CONSOLE',
    'REVENUE / HASF'
  ];

  for (const text of required) {
    if (!normalizedBody.includes(text)) {
      throw new Error(`MOONSHOT_TEXT_MISSING: ${text}`);
    }
  }

  if (normalizedBody.includes('UNDEFINED')) {
    throw new Error('MOONSHOT_UNDEFINED_TEXT');
  }

  const cards = await page.locator('.card').count();
  if (cards < 6) {
    throw new Error(`MOONSHOT_CARD_COUNT_LOW: ${cards}`);
  }

  console.log('UI_MOONSHOT_BROWSER: PASS');
} finally {
  await browser.close();
}
