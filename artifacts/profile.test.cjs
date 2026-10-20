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

    await page.getByText('Производство проката · Екатеринбург', { exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Категории', exact: true }).count(), 1);
    await page.getByText('Прямое влияние', { exact: true }).first().waitFor();
    assert.equal(await page.getByText('Экспортные пошлины и квоты', { exact: true }).count(), 1);

    await page.getByRole('button', { name: /Экспортные пошлины и квоты/ }).click();
    await page.getByRole('button', { name: 'Фоновое', exact: true }).click();
    await page.getByRole('button', { name: /Экспортные пошлины и квоты/ }).click();

    await page.getByRole('button', { name: 'Контрагенты', exact: true }).click();
    await page.getByText('Добыча железной руды', { exact: true }).waitFor();
    assert.equal(await page.getByText('10% закупок', { exact: true }).count(), 0);
    await page.getByRole('button', { name: /^Покупатели/ }).click();
    await page.getByText('Строительство', { exact: true }).first().waitFor();

    await page.getByRole('button', { name: 'Андрей Волков', exact: true }).click();
    const input = page.locator('input').last();
    await input.fill('Иван Петров');
    await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.getByRole('button', { name: 'Иван Петров', exact: true }).waitFor();

    await nav.getByRole('button', { name: 'Источники', exact: true }).click();
    await nav.getByRole('button', { name: 'Профиль', exact: true }).click();
    await page.getByRole('button', { name: 'Иван Петров', exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('Profile checks passed: categories, counterparties and editing');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
