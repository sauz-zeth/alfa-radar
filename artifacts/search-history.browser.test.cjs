const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(`${__dirname}/Лента новостей v9.dc.html`).href);
    const open = () => page.getByRole('button', { name: 'Поиск по всем новостям и компаниям' }).click();
    const input = page.getByRole('searchbox');
    const clear = () => page.getByRole('button', { name: 'Очистить поиск', exact: true }).click();
    await open();
    assert.equal(await page.locator('.search-card').count(), 0);
    await input.fill('незавершённый запрос');
    await clear();
    assert.equal(await page.getByText('Недавние запросы', { exact: true }).count(), 0);
    await input.fill('РЖД');
    await input.press('Enter');
    await clear();
    await page.getByRole('button', { name: 'РЖД', exact: true }).waitFor();
    await page.reload();
    await open();
    await page.getByRole('button', { name: 'РЖД', exact: true }).click();
    assert.equal(await input.inputValue(), 'РЖД');
    assert.equal(await page.locator('.search-card').count(), 2);
    await input.fill('форум');
    await page.locator('.search-card').click();
    await page.getByRole('button', { name: 'Назад к результатам' }).click();
    await clear();
    await page.getByRole('button', { name: 'форум', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Удалить запрос «РЖД»', exact: true }).click();
    await page.reload();
    await open();
    assert.equal(await page.getByRole('button', { name: 'РЖД', exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Очистить историю', exact: true }).click();
    await page.reload();
    await open();
    assert.equal(await page.getByText('Недавние запросы', { exact: true }).count(), 0);

    await page.evaluate(() => {
      Storage.prototype.setItem = () => { throw new DOMException('Storage unavailable', 'QuotaExceededError'); };
    });
    await input.fill('сталь');
    await input.press('Enter');
    await clear();
    await page.getByRole('button', { name: 'сталь', exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('Browser history checks passed: submit, reload, repeat, results, removal, clear and storage failure');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
