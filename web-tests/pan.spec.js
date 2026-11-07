import { test, expect } from '@playwright/test';
import fs from 'node:fs';

const center = async (page) =>
  (await page.locator('#after').getAttribute('data-center'))
    .split(',')
    .map(Number);
const scale = async (page) =>
  Number(await page.locator('#after').getAttribute('data-zoom'));
async function open(page) {
  await page.goto('/');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready');
  await expect(page.locator('#after')).toHaveAttribute('data-zoom', /\d/);
}
async function drag(page, dx, dy) {
  const b = await page.locator('#after').boundingBox();
  const x = b.x + b.width * 0.45,
    y = b.y + b.height * 0.45;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + dx, y + dy, { steps: 8 });
  await page.mouse.up();
}

for (const view of [
  { width: 1440, height: 1000, mode: 'boundary' },
  { width: 1280, height: 800, mode: 'boundary' },
  { width: 390, height: 844, mode: 'boundary' },
  { width: 1440, height: 1000, mode: 'single' },
])
  test(`pan after one zoom step follows both drag axes ${view.width} ${view.mode}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: view.width, height: view.height });
    await open(page);
    if (view.mode === 'single') await page.locator('#modeSingle').click();
    await page.locator('#zoomin').click();
    const before = await center(page),
      zoom = await scale(page);
    const pixelsBefore = await page
      .locator('#after')
      .evaluate((c) => c.toDataURL());
    await drag(page, 24, 32);
    const after = await center(page);
    await testInfo.attach('pan-diagnostic', {
      body: JSON.stringify({
        view,
        before,
        after,
        zoom,
        expected: { x: before[0] - 24 / zoom, y: before[1] - 32 / zoom },
      }),
      contentType: 'application/json',
    });
    expect(
      after[0],
      'horizontal drag must not be locked when the image fits this axis',
    ).toBeCloseTo(before[0] - 24 / zoom, 1);
    expect(
      after[1],
      'vertical drag must not be locked when the image fits this axis',
    ).toBeCloseTo(before[1] - 32 / zoom, 1);
    expect(
      await page.locator('#after').evaluate((c) => c.toDataURL()),
    ).not.toBe(pixelsBefore);
    if (view.width > 760 && view.mode === 'boundary')
      await expect(page.locator('#before')).toHaveAttribute(
        'data-center',
        await page.locator('#after').getAttribute('data-center'),
      );
    fs.mkdirSync('captures', { recursive: true });
    await page.screenshot({
      path: `captures/pan-${view.width}-${view.mode}.png`,
    });
    await page.locator('#fit').click();
    expect(await center(page)).toEqual([256, 256]);
  });

test('two-finger style horizontal and vertical wheel events pan without changing zoom', async ({
  page,
}, testInfo) => {
  await open(page);
  await page.locator('#zoomin').click();
  const before = await center(page),
    zoom = await scale(page);
  await page.locator('#after').hover({ position: { x: 150, y: 150 } });
  await page.mouse.wheel(24, 32);
  await expect.poll(async () => await center(page)).not.toEqual(before);
  const after = await center(page);
  await testInfo.attach('wheel-diagnostic', {
    body: JSON.stringify({ before, after, zoom, afterZoom: await scale(page) }),
    contentType: 'application/json',
  });
  expect(await scale(page)).toBe(zoom);
  expect(after[0]).toBeCloseTo(before[0] + 24 / zoom, 1);
  expect(after[1]).toBeCloseTo(before[1] + 32 / zoom, 1);
});

test('modifier wheel zoom remains available after wheel panning', async ({
  page,
}) => {
  await open(page);
  for (const modifier of ['Control', 'Meta']) {
    await page.locator('#fit').click();
    const initial = await scale(page);
    await page.locator('#after').hover({ position: { x: 200, y: 200 } });
    await page.keyboard.down(modifier);
    await page.mouse.wheel(0, -120);
    await page.keyboard.up(modifier);
    await expect.poll(() => scale(page)).toBeGreaterThan(initial);
    const zoom = await scale(page),
      before = await center(page);
    await page.mouse.wheel(12, 18);
    await expect.poll(() => center(page)).not.toEqual(before);
    expect(await scale(page)).toBe(zoom);
  }
});
