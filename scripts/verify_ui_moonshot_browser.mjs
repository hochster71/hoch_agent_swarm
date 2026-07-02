import { chromium } from 'playwright';

const base = process.env.PERT_BASE_URL || 'http://127.0.0.1:8765';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1700, height: 1300 } });

try {
  await page.goto(`${base}/ui-moonshot`, { waitUntil: 'networkidle', timeout: 30000 });

  const body = await page.locator('body').innerText({ timeout: 10000 });
  const normalizedBody = body.toUpperCase();

  const required = [
    'HOCH PODS LIFTOFF CONTROL PLANE V4',
    'MISSION AUTHORITY',
    'LEADING AGENTS',
    'SWARM THEATER / AGENT LIFTOFF',
    'LIVE PERT ANALYSIS',
    'LIVE GAP ANALYSIS / CLOSURES',
    'LIVE RUNNERS / APPROVAL QUEUE',
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

  const glyphs = await page.locator('.agentGlyph').count();
  if (glyphs < 6) throw new Error(`MOONSHOT_AGENT_GLYPHS_LOW: ${glyphs}`);

  const pertRows = await page.locator('#pertTruthRows tr').count();
  if (pertRows < 1) throw new Error('MOONSHOT_PERT_ROWS_MISSING');

  const gapRows = await page.locator('#gapClosureRows tr').count();
  if (gapRows < 1) throw new Error('MOONSHOT_GAP_ROWS_MISSING');

  const runnerRows = await page.locator('#runnerRows tr').count();
  if (runnerRows < 1) throw new Error('MOONSHOT_RUNNER_ROWS_MISSING');

  await page.locator('.agentGlyph').first().hover();
  const modalVisible = await page.locator('#agentModal.active').count();
  if (modalVisible < 1) throw new Error('MOONSHOT_AGENT_MODAL_NOT_VISIBLE');

  console.log('UI_MOONSHOT_BROWSER: PASS');
} finally {
  await browser.close();
}
