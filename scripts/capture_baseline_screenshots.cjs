const path = require('path');
const { chromium } = require(path.resolve(__dirname, '..', 'frontend', 'node_modules', 'playwright'));
const fs = require('fs');

(async () => {
  const outDir = path.resolve(__dirname, '..', 'docs', 'baseline');
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();
  console.log('Navigating to http://localhost:3000 ...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // 1. Landing View
  console.log('Capturing 00_landing.png ...');
  await page.screenshot({ path: path.join(outDir, '00_landing.png'), fullPage: true });

  // List of views to click
  const views = [
    { key: 'atlas', name: '01_taxa_atlas.png', buttonText: 'Taxa Atlas' },
    { key: 'workbench', name: '02_sequence_workbench.png', buttonText: 'Sequence Workbench' },
    { key: 'biodb', name: '03_biodb_explorer.png', buttonText: 'BioDB Multi-Explorer' },
    { key: 'studio', name: '04_literature_copilot.png', buttonText: 'Literature Copilot' },
    { key: 'corpus', name: '05_literature_corpus.png', buttonText: 'Literature Corpus' },
    { key: 'about', name: '06_platform_overview.png', buttonText: 'Platform Overview' },
    { key: 'evaluation', name: '07_benchmark_diagnostics.png', buttonText: 'Benchmark Diagnostics' },
    { key: 'diagnostics', name: '08_system_telemetry.png', buttonText: 'System Telemetry' },
  ];

  for (const v of views) {
    console.log(`Navigating to ${v.buttonText} ...`);
    try {
      // Find navigation button with text matching
      const btn = page.locator(`button:has-text("${v.buttonText}")`).first();
      if (await btn.count() > 0) {
        await btn.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: path.join(outDir, v.name), fullPage: true });
        console.log(`Captured ${v.name}`);
      } else {
        console.warn(`Could not find button for ${v.buttonText}`);
      }
    } catch (e) {
      console.error(`Error capturing ${v.name}:`, e.message);
    }
  }

  // Also capture Taxon Detail in Atlas
  console.log('Capturing Taxon Detail View (Woolly Mammoth) ...');
  try {
    const atlasBtn = page.locator('button:has-text("Taxa Atlas")').first();
    await atlasBtn.click();
    await page.waitForTimeout(1500);

    // Click on the first taxon card (Woolly Mammoth)
    const card = page.locator('div:has-text("Mammuthus primigenius")').first();
    if (await card.count() > 0) {
      await card.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: path.join(outDir, '01b_taxa_atlas_detail_overview.png'), fullPage: true });
      console.log('Captured 01b_taxa_atlas_detail_overview.png');

      // Click on "Extant Relative Synteny" tab
      const syntenyTab = page.locator('button:has-text("Extant Relative Synteny"), button:has-text("Extant Synteny")').first();
      if (await syntenyTab.count() > 0) {
        await syntenyTab.click();
        await page.waitForTimeout(1500);
        await page.screenshot({ path: path.join(outDir, '01c_taxa_atlas_detail_synteny.png'), fullPage: true });
        console.log('Captured 01c_taxa_atlas_detail_synteny.png');
      }

      // Click on "3D Structure" tab
      const structTab = page.locator('button:has-text("3D Structure"), button:has-text("Structure")').first();
      if (await structTab.count() > 0) {
        await structTab.click();
        await page.waitForTimeout(1500);
        await page.screenshot({ path: path.join(outDir, '01d_taxa_atlas_detail_structure.png'), fullPage: true });
        console.log('Captured 01d_taxa_atlas_detail_structure.png');
      }

      // Click on "Fossil Record" tab
      const fossilTab = page.locator('button:has-text("Fossil Record"), button:has-text("PBDB")').first();
      if (await fossilTab.count() > 0) {
        await fossilTab.click();
        await page.waitForTimeout(1500);
        await page.screenshot({ path: path.join(outDir, '01e_taxa_atlas_detail_fossils.png'), fullPage: true });
        console.log('Captured 01e_taxa_atlas_detail_fossils.png');
      }
    }
  } catch (e) {
    console.error('Error capturing taxon detail:', e.message);
  }

  await browser.close();
  console.log('All baseline screenshots captured successfully!');
})();
