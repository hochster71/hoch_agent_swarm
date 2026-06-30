const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER EXCEPTION:', err.message));

  console.log("Navigating to https://has.localhost...");
  try {
    await page.goto('https://has.localhost/', { waitUntil: 'networkidle' });
    console.log("Navigation complete.");
    
    // Click PromptOps tab
    await page.click('#nav-promptops');
    
    // Check if the presets button exists in the DOM
    const html = await page.content();
    console.log("Has Weak Preset Button:", html.includes('Weak / Broad Prompt'));
    console.log("Has react-compliance-root:", html.includes('id="react-compliance-root"'));
    
    const rootContent = await page.evaluate(() => {
      const el = document.getElementById("react-compliance-root");
      return el ? el.innerHTML : "not found";
    });
    console.log("react-compliance-root content:", rootContent);
    
  } catch (e) {
    console.error("Navigation failed:", e);
  }
  
  await browser.close();
})();
