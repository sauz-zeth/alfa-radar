const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  try {
    const page = await browser.newPage({ viewport: { width: 480, height: 940 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(`${__dirname}/Лента новостей v9.dc.html`).href);
    const nav = page.getByRole('navigation');
    await nav.getByRole('button', { name: 'Профиль', exact: true }).click();
    const settings = page.locator('.factor-settings');
    const canvas = settings.locator('canvas');
    await canvas.scrollIntoViewIfNeeded();
    const values = () => canvas.evaluate(el => window.Chart.getChart(el).data.datasets[0].data);
    assert.deepEqual(await values(), [6, 8, 7]);
    assert.equal(await settings.locator('input[type=range]').count(), 0);
    assert.equal(await settings.getByRole('button', { name: /Экспортные пошлины/ }).count(), 0, 'List is compact until a group is chosen');

    const point = await canvas.evaluate(el => {
      const arc = window.Chart.getChart(el).getDatasetMeta(0).data[0];
      const { x, y } = arc.getCenterPoint();
      return { x, y };
    });
    await canvas.click({ position: point });
    await settings.getByRole('button', { name: /Экспортные пошлины/ }).click();
    const range = settings.locator('input[type=range]');
    await range.fill('0.6');
    assert.deepEqual(await values(), [5, 9, 7], 'Editing weight updates chart groups');
    await range.fill('0');
    assert.deepEqual(await values(), [5, 8, 7]);
    await settings.getByRole('button', { name: 'Не влияют · 10', exact: true }).click();
    await settings.getByRole('button', { name: /Экспортные пошлины/ }).waitFor();
    await settings.getByRole('button', { name: /Фоновое/ }).click();
    await settings.getByRole('button', { name: /Налоги и НДПИ/ }).waitFor();

    await nav.getByRole('button', { name: 'Источники', exact: true }).click();
    assert.equal(await page.evaluate(() => Object.keys(window.Chart.instances).length), 0, 'Unmount destroys the chart');
    await nav.getByRole('button', { name: 'Профиль', exact: true }).click();
    assert.deepEqual(await values(), [5, 8, 7], 'Return keeps edited weights');
    assert.equal(await page.evaluate(() => Object.keys(window.Chart.instances).length), 1);
    assert.equal(await page.locator('.profile-page').evaluate(el => el.scrollWidth <= el.clientWidth), true);
    assert.deepEqual(errors, []);
    console.log('Profile chart checks passed: sector click, groups, editing, inactive factors, lifecycle and layout');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
