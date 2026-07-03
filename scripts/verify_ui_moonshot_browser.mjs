import { chromium } from 'playwright';

const base = process.env.PERT_BASE_URL || 'http://127.0.0.1:8765';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1700, height: 1300 } });

try {
  await page.goto(`${base}/ui-moonshot`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('.podNode', { timeout: 15000 });

  const body = await page.locator('body').innerText({ timeout: 10000 });
  const normalizedBody = body.toUpperCase();

  const required = [
    'HOCH PODS THEATER V6',
    'STORYBOARD-DRIVEN AGENT SPIN-UP',
    'HOCH PODS STORYBOARD THEATER',
    'AGENT QUEUE',
    'STALE / WATCHDOG',
    'EVIDENCE CONSOLE'
  ];

  for (const text of required) {
    if (!normalizedBody.includes(text)) {
      throw new Error(`MOONSHOT_TEXT_MISSING: ${text}`);
    }
  }

  if (normalizedBody.includes('UNDEFINED')) {
    throw new Error('MOONSHOT_UNDEFINED_TEXT');
  }

  // Heading check / Live PERT Analysis
  const hasPertHeading = /Live\s+PERT\s+Analysis/i.test(body);
  const pertRows = await page.locator('#pertTruthRows tr').count();
  if (!hasPertHeading && pertRows < 1) {
    throw new Error('MOONSHOT_PERT_CONTRACT_MISSING: No Live PERT Analysis heading and no #pertTruthRows tr found.');
  }

  const theaters = await page.locator('#theater').count();
  if (theaters !== 1) throw new Error(`MOONSHOT_THEATER_COUNT_INVALID: ${theaters}`);

  const pods = await page.locator('.podNode').count();
  if (pods < 7) throw new Error(`MOONSHOT_POD_COUNT_LOW: ${pods}`);

  const scenes = await page.locator('.storyFrame').count();
  if (scenes < 17) throw new Error(`MOONSHOT_STORYBOARD_COUNT_LOW: ${scenes}`);

  const spirit = await page.locator('#agentSpirit').count();
  if (spirit !== 1) throw new Error('MOONSHOT_AGENT_SPIRIT_MISSING');

  const beam = await page.locator('#launchBeam').count();
  if (beam !== 1) throw new Error('MOONSHOT_LAUNCH_BEAM_MISSING');

  const skill = await page.locator('#skillCard').count();
  if (skill !== 1) throw new Error('MOONSHOT_SKILL_CARD_MISSING');

  const gapRows = await page.locator('#gapClosureRows tr').count();
  if (gapRows < 1) throw new Error('MOONSHOT_GAP_ROWS_MISSING');

  const runnerRows = await page.locator('#runnerRows tr').count();
  if (runnerRows < 1) throw new Error('MOONSHOT_RUNNER_ROWS_MISSING');

  console.log('UI_MOONSHOT_BROWSER: PASS');
} finally {
  await browser.close();
}
