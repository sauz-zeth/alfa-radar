const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  try {
    const page = await browser.newPage({ hasTouch: true });
    await page.goto(pathToFileURL(`${__dirname}/Лента новостей v9.dc.html`).href);
    const nav = page.locator('.top-tabs');
    await nav.waitFor();
    await page.evaluate(() => document.fonts.ready);
    const search = page.getByRole('button', { name: 'Поиск по всем новостям и компаниям' });
    const searchBox = await search.boundingBox();
    const fades = () => nav.evaluate(el => [el.style.getPropertyValue('--fade-left'), el.style.getPropertyValue('--fade-right')]);
    assert.deepEqual(await fades(), ['0px', '18px']);
    const settled = () => page.waitForTimeout(700);
    const left = () => nav.evaluate(el => el.scrollLeft);
    await nav.hover();
    await page.mouse.wheel(0, 200);
    await settled();
    assert.ok(await left() > 0, 'Vertical wheel scrolls tabs horizontally');
    assert.deepEqual(await search.boundingBox(), searchBox, 'Search stays fixed while tabs scroll');
    assert.deepEqual(await fades(), ['18px', '0px']);
    await page.mouse.wheel(0, -200);
    await settled();
    assert.equal(await left(), 0);
    assert.deepEqual(await fades(), ['0px', '18px']);

    const rect = await nav.boundingBox();
    await page.mouse.move(rect.x + 220, rect.y + 20);
    await page.mouse.down();
    await page.mouse.move(rect.x + 80, rect.y + 20, { steps: 10 });
    await page.mouse.up();
    await settled();
    assert.ok(await left() > 0, 'Mouse drag scrolls tabs');
    assert.equal(await page.getByText('Источники', { exact: true }).count(), 1, 'Drag does not open a tab');

    await nav.evaluate(el => el.scrollTo({ left: 0, behavior: 'instant' }));
    await settled();
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: rect.x + 280, y: rect.y + 20 }] });
    for (let i = 1; i <= 10; i++) {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: rect.x + 280 - i * 15, y: rect.y + 20 }] });
    }
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await settled();
    assert.ok(await left() > 0, 'Touch swipe scrolls tabs');
    await nav.getByRole('button', { name: 'Профиль', exact: true }).click();
    await settled();
    const profile = await nav.getByRole('button', { name: 'Профиль', exact: true }).boundingBox();
    assert.ok(profile.x >= rect.x && profile.x + profile.width <= rect.x + rect.width, 'Selected tab is fully visible');
    assert.equal(await nav.evaluate(el => Math.round(el.scrollLeft - (el.scrollWidth - el.clientWidth))), 0, 'Last tab snaps to the scroll boundary');
    await nav.getByRole('button', { name: /^Лента/ }).click();
    const tags = page.getByRole('group', { name: 'Темы новостей' });
    await tags.hover();
    await page.mouse.wheel(0, 240);
    await settled();
    assert.ok(await tags.evaluate(el => el.scrollLeft) > 0, 'Tags support vertical wheel');
    assert.ok(await tags.evaluate(el => [...el.children].some(button => Math.abs(button.getBoundingClientRect().left - el.getBoundingClientRect().left - 16) < 2)), 'Tags snap to a button');
    await tags.evaluate(el => el.scrollTo({ left: 0, behavior: 'instant' }));
    await settled();
    const tagRect = await tags.boundingBox();
    await page.mouse.move(tagRect.x + 280, tagRect.y + 15);
    await page.mouse.down();
    await page.mouse.move(tagRect.x + 80, tagRect.y + 15, { steps: 10 });
    await page.mouse.up();
    await settled();
    assert.ok(await tags.evaluate(el => el.scrollLeft) > 0, 'Tags support mouse drag');
    assert.equal(await page.locator('image-slot').count(), 18, 'Dragging tags does not activate a filter');
    await tags.evaluate(el => el.scrollTo({ left: 0, behavior: 'instant' }));
    await settled();
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: tagRect.x + 280, y: tagRect.y + 15 }] });
    for (let i = 1; i <= 10; i++) {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: tagRect.x + 280 - i * 15, y: tagRect.y + 15 }] });
    }
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await settled();
    assert.ok(await tags.evaluate(el => el.scrollLeft) > 0, 'Tags support touch swipe');
    await tags.getByRole('button', { name: 'Важное упоминание', exact: true }).click();
    assert.equal(await page.locator('image-slot').count(), 6, 'Click still filters news');
    await nav.hover();
    await page.mouse.wheel(0, 200);
    await settled();
    assert.ok(await left() > 0, 'Tabs still scroll after tags mount and filter');
    console.log('Navigation and tag checks passed: wheel, drag, touch, snap, fixed search, fades and filtering');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
