import { chromium } from 'playwright';

const base = process.env.PERT_BASE_URL || 'http://127.0.0.1:8765';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1700, height: 1300 } });

try {
  await page.goto(`${base}/ui-moonshot`, { waitUntil: 'networkidle', timeout: 30000 });

  const body = await page.locator('body').innerText({ timeout: 10000 });
  const normalizedBody = body.toUpperCase();

  const required = [
    'HOCH PODS LIFTOFF CONTROL PLANE V3',
    'MISSION AUTHORITY',
    'LEADING AGENTS',
    'SWARM THEATER',
    'LIVE PERT ANALYSIS',
    'LIVE GAP ANALYSIS / CLOSURES',
    'LIVE RUNNERS / APPROVAL QUEUE',
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

  const pertRows = await page.locator('#pertTruthRows tr').count();
  if (pertRows < 1) throw new Error('MOONSHOT_PERT_ROWS_MISSING');

  const gapRows = await page.locator('#gapClosureRows tr').count();
  if (gapRows < 1) throw new Error('MOONSHOT_GAP_ROWS_MISSING');

  const runnerRows = await page.locator('#runnerRows tr').count();
  if (runnerRows < 1) throw new Error('MOONSHOT_RUNNER_ROWS_MISSING');

  console.log('UI_MOONSHOT_BROWSER: PASS');
} finally {
  await browser.close();
}
