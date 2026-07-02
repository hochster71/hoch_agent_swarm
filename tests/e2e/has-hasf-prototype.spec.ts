import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test('1. Capture Screenshot of Standalone Visual Prototype', async ({ page }) => {
    // Set viewport size exactly as required
    await page.setViewportSize({ width: 1536, height: 864 });

    // Navigate to the standalone visual prototype route
    await page.goto('http://127.0.0.1:8765/hoch-pods-theater-prototype');

    // Wait for the page to load completely (animations, SVGs)
    await page.waitForTimeout(2000);

    // Save screenshot
    const screenshotDir = path.join(__dirname, '..', '..', 'docs', 'evidence', 'ui', 'screenshots');
    fs.mkdirSync(screenshotDir, { recursive: true });
    const screenshotPath = path.join(screenshotDir, 'hoch-pods-theater-prototype-current.png');
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`Saved prototype screenshot to: ${screenshotPath}`);
});
