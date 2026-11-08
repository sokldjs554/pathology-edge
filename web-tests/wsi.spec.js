import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const data = JSON.parse(
  fs.readFileSync(new URL('../dist/wsi.json', import.meta.url)),
);
fs.mkdirSync('captures', { recursive: true });
const shot = async (page, name) => {
  if ((await page.locator('body').getAttribute('data-phase')) === 'ready')
    await page.waitForFunction(() =>
      Object.entries(WSI.viewers).every(
        ([id, v]) =>
          (id === 'A' && WSI.mode === 'explore') || v.getFullyLoaded(),
      ),
    );
  return page.screenshot({ path: `captures/wsi-${name}.png`, fullPage: true });
};
const open = async (page) => {
  await page.goto('/wsi.html');
  await expect
    .poll(() => page.locator('body').getAttribute('data-phase'), {
      timeout: 25000,
    })
    .not.toBe('loading');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {
    timeout: 5000,
  });
};
const roi = async (page, id = 'R1') => {
  await page.locator(`.roi-item[data-roi="${id}"]`).click();
  await expect(page.locator('#activeRegion')).toContainText(id);
  const r = data.rois.find((r) => r.id === id);
  await expect
    .poll(async () => {
      const c = (await center(page)).split(',').map(Number);
      return Math.hypot(c[0] - r.origin[0] - 512, c[1] - r.origin[1] - 512);
    })
    .toBeLessThan(1);
};
const center = (page, id = 'B') =>
  page.locator('#viewer' + id).getAttribute('data-center');
const synced = async (page) => {
  await expect
    .poll(async () => {
      const a = (await center(page, 'A')).split(',').map(Number),
        b = (await center(page, 'B')).split(',').map(Number);
      return Math.hypot(a[0] - b[0], a[1] - b[1]);
    })
    .toBeLessThan(0.05);
  await expect
    .poll(async () =>
      Math.abs(
        Number(await page.locator('#viewerA').getAttribute('data-zoom')) -
          Number(await page.locator('#viewerB').getAttribute('data-zoom')),
      ),
    )
    .toBeLessThan(0.0001);
};
test('real multilevel tiles load; ROI masks, metrics and native coordinates use the same slide', async ({
  page,
}) => {
  const errors = [],
    requests = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('response', (r) => {
    if (r.url().includes('/slide_files/'))
      requests.push({ url: r.url(), status: r.status() });
  });
  await open(page);
  await shot(page, 'overview');
  await expect(page.locator('.guide')).toContainText('① 슬라이드 탐색');
  await expect(page.locator('#coverageSummary')).toContainText('0.2079%');
  for (const r of data.rois) {
    await roi(page, r.id);
    await synced(page);
    const c = (await center(page)).split(',').map(Number);
    expect(c[0]).toBeCloseTo(r.origin[0] + 512, 1);
    expect(c[1]).toBeCloseTo(r.origin[1] + 512, 1);
    await expect(page.locator('#roiMetrics tr').nth(0)).toContainText(
      r.methods.no_overlap.median_seconds.toFixed(3),
    );
    await expect(page.locator('#roiMetrics tr').nth(0)).toContainText(
      r.methods.overlap.median_seconds.toFixed(3),
    );
    await expect(page.locator('#roiMetrics tr').nth(4)).toContainText(
      String(r.methods.overlap.merged_count),
    );
    const mask = page.locator(`#overlayB image[data-mask="${r.id}-overlap"]`);
    await expect(mask).toHaveAttribute('x', String(r.origin[0]));
    await expect(mask).toHaveAttribute('href', r.methods.overlap.overlay);
  }
  await page.locator('#native').click();
  await expect(page.locator('#zoomReadout')).toHaveText('100%');
  await expect
    .poll(() =>
      requests.some((r) => r.status === 200 && r.url.includes('/16/')),
    )
    .toBe(true);
  expect(
    new Set(
      requests
        .filter((r) => r.status === 200)
        .map((r) => r.url.match(/slide_files\/(\d+)\//)?.[1]),
    ).size,
  ).toBeGreaterThan(1);
  expect(errors).toEqual([]);
  await shot(page, 'roi-native');
  fs.writeFileSync(
    'captures/wsi-real-tile-requests.json',
    JSON.stringify({ requests, source: data.slide.source_sha256 }, null, 2),
  );
});
test('real XOR case, shared viewport, ordinary scroll, dragging and calibrated zoom', async ({
  page,
}) => {
  await open(page);
  await roi(page);
  await page.locator('#jumpDifference').click();
  const c = data.rois[0].difference.cases[0];
  await synced(page);
  await expect(page.locator('#differenceCounts')).toContainText(
    `추가 ${c.added_pixels}px`,
  );
  await expect(page.locator('#differenceCounts')).toContainText(
    `제거 ${c.removed_pixels}px`,
  );
  for (const id of ['A', 'B']) {
    const b = page.locator(`#overlay${id} [data-boundary]`);
    await expect(b).toHaveAttribute('x', String(c.bbox_level0[0]));
    await expect(b).toHaveAttribute('y', String(c.bbox_level0[1]));
    const centerXY = (await center(page, id)).split(',').map(Number);
    expect(centerXY[0]).toBeCloseTo(c.center_level0[0], 1);
    expect(centerXY[1]).toBeCloseTo(c.center_level0[1], 1);
    const bounds = await b.boundingBox(),
      v = await page.locator('#viewer' + id).boundingBox();
    expect(
      Math.abs(bounds.x + bounds.width / 2 - (v.x + v.width / 2)),
    ).toBeLessThan(1);
    expect(
      Math.abs(bounds.y + bounds.height / 2 - (v.y + v.height / 2)),
    ).toBeLessThan(1);
  }
  await shot(page, 'boundary');
  const box = await page.locator('#viewerB').boundingBox();
  await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.35);
  const old = await center(page);
  await page.mouse.wheel(43, 76);
  await expect.poll(() => center(page)).not.toBe(old);
  await synced(page);
  const old2 = await center(page);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width * 0.65 - 60,
    box.y + box.height * 0.35 + 40,
    { steps: 8 },
  );
  await page.mouse.up();
  await expect.poll(() => center(page)).not.toBe(old2);
  await synced(page);
  const z = Number(await page.locator('#viewerB').getAttribute('data-zoom'));
  await page.keyboard.down('Control');
  await page.mouse.wheel(0, -120);
  await page.keyboard.up('Control');
  await expect
    .poll(async () =>
      Number(await page.locator('#viewerB').getAttribute('data-zoom')),
    )
    .toBeGreaterThan(z);
  await synced(page);
  await page.locator('#showMask').uncheck();
  await expect(page.locator('#overlayB [data-mask]')).toHaveCount(0);
  await page.locator('#showDifference').uncheck();
  await expect(page.locator('#overlayB [data-difference]')).toHaveCount(0);
  await page.locator('#showMask').check();
  await page.locator('#showDifference').check();
  await page.locator('#viewerB').focus();
  const old3 = await center(page);
  await page.keyboard.press('ArrowLeft');
  await expect.poll(() => center(page)).not.toBe(old3);
  await synced(page);
});
test('NMS pair links actual raw candidates to the two original native patches', async ({
  page,
}) => {
  await open(page);
  await roi(page);
  await page.locator('#traceFirst').click();
  const m = data.rois[0].methods.overlap,
    p = m.suppressed[0];
  await expect(page.locator('#modeTrace')).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(page.locator('#candidateInfo')).toContainText(
    `#${p.suppressed_raw_index + 1} 억제 → 청록 #${p.kept_raw_index + 1} 유지`,
  );
  await expect(page.locator('#candidateInfo')).toContainText(
    p.box_iou.toFixed(3),
  );
  for (const id of ['A', 'B']) {
    await expect(
      page.locator(`#overlay${id} [data-patch="${p.kept_patch_id}"]`),
    ).toHaveAttribute(
      'x',
      String(m.patches.find((q) => q.id === p.kept_patch_id).origin_level0[0]),
    );
    await expect(
      page.locator(`#overlay${id} image[data-mask="R1-overlap"]`),
    ).toHaveCount(1);
  }
  await expect(
    page.locator(`#overlayA [data-selected="${p.suppressed_raw_index}"]`),
  ).toHaveCount(1);
  await expect(
    page.locator(`#overlayB [data-selected="${p.suppressed_raw_index}"]`),
  ).toHaveCount(0);
  await synced(page);
  await shot(page, 'candidate-provenance');
  await page.locator('#pairSelect').selectOption('1');
  await expect(page.locator('#candidateInfo')).toContainText(
    `#${m.suppressed[1].suppressed_raw_index + 1}`,
  );
  await page.locator('#modeCompare').click();
  await expect(page.locator('#overlayA [data-selected]')).toHaveCount(0);
  await roi(page, 'R2');
  await expect(page.locator('#traceDetail')).toBeHidden();
});

test('candidate centres are selectable without blocking drag; navigator moves both panes', async ({
  page,
}) => {
  await open(page);
  await roi(page);
  await page.locator('#showCandidates').check();
  const object = data.rois[0].methods.no_overlap.objects.find(
    (o) => o.x > 350 && o.x < 650 && o.y > 350 && o.y < 650,
  );
  const box = await page.locator('#viewerA').boundingBox(),
    c = (await center(page, 'A')).split(',').map(Number),
    z = Number(await page.locator('#viewerA').getAttribute('data-zoom'));
  const x = box.x + box.width / 2 + (object.center_level0[0] - c[0]) * z,
    y = box.y + box.height / 2 + (object.center_level0[1] - c[1]) * z;
  await page.mouse.click(x, y);
  await expect(page.locator('#candidateInfo')).toContainText(
    `무겹침 raw #${object.raw_index + 1}`,
  );
  await expect(page.locator('#overlayB [data-selected]')).toHaveCount(0);
  const before = await center(page, 'A');
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 40, y + 30, { steps: 6 });
  await page.mouse.up();
  await expect.poll(() => center(page, 'A')).not.toBe(before);
  await synced(page);
  const nav = await page.locator('#viewerB .navigator').boundingBox(),
    old = await center(page);
  await page.mouse.click(nav.x + nav.width * 0.65, nav.y + nav.height * 0.35);
  await expect.poll(() => center(page)).not.toBe(old);
  await synced(page);
  await expect(page.locator('#centerCoverage')).toContainText('미분석');
});

test('a stalled overlay cannot indefinitely block the real WSI', async ({
  page,
}) => {
  const pending = [];
  await page.route(`**/${data.rois[0].methods.overlap.overlay}`, (route) => {
    pending.push(route);
  });
  await page.goto('/wsi.html', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#modeCompare')).toBeDisabled();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {
    timeout: 25000,
  });
  await expect(page.locator('#tileWarning')).toContainText('예측 오버레이');
  for (const route of pending) await route.abort();
});
test('unanalysed scan has no fabricated result; old positive and negative GT cases remain accessible', async ({
  page,
}) => {
  await open(page);
  await roi(page);
  await page.locator('#slideOverview').click();
  await expect(page.locator('#centerCoverage')).toContainText('미분석');
  await expect(page.locator('#overlayB [data-mask]')).toHaveCount(3);
  await expect(page.locator('.notice')).toContainText(
    '정확도 개선을 뜻하지 않습니다',
  );
  for (const [sample, caseId] of [
    ['11_1', '11_1-improved'],
    ['10_3', '10_3-worsened'],
  ]) {
    await page.goto(`/index.html?sample=${sample}&case=${caseId}`);
    await expect(page.locator('#after')).toHaveAttribute('data-case', caseId);
  }
});
for (const [width, height] of [
  [1024, 768],
  [390, 844],
  [375, 667],
])
  test(`WSI responsive review ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await open(page);
    await expect(page.locator('#inspector')).toBeHidden();
    if (width <= 760) await page.locator('#toggleRegions').click();
    await roi(page);
    await page.locator('#jumpDifference').click();
    await synced(page);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <= innerWidth &&
          document.body.scrollHeight <= innerHeight,
      ),
    ).toBe(true);
    const box = await page.locator('#viewerB').boundingBox();
    expect(box.height).toBeGreaterThan(180);
    if (width <= 760) {
      await page.locator('#mobileA').click();
      await expect(page.locator('#paneA')).toBeVisible();
      await expect(page.locator('#paneB')).toBeHidden();
      await page.locator('#mobileB').click();
    }
    await shot(page, `mobile-${width}`);
    await page.locator('#toggleResults').click();
    await expect(page.locator('#inspector')).toBeVisible();
    await expect(page.locator('#differenceDetail')).toContainText('64×64');
    await page.locator('#closeResults').click();
    await expect(page.locator('#inspector')).toBeHidden();
  });
test('tile outage and metadata failure are visible and retry fetches real data', async ({
  page,
}) => {
  await page.route('**/slide_files/**', (r) => r.abort());
  await page.goto('/wsi.html');
  await expect(page.locator('#tileWarning')).toBeVisible({ timeout: 25000 });
  await expect(page.locator('#stageTitle')).toHaveText(
    '슬라이드 타일을 열지 못했습니다',
  );
  await shot(page, 'tile-error-injected');
  await page.unroute('**/slide_files/**');
  await page.locator('#retryTiles').click();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {
    timeout: 25000,
  });
  await page.route('**/wsi.json', (r) =>
    r.fulfill({ status: 503, body: 'unavailable' }),
  );
  await page.reload();
  await expect(page.locator('#stageDetail')).toContainText('503');
  await page.unroute('**/wsi.json');
  await page.locator('#retryTiles').click();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {
    timeout: 25000,
  });
});

test('invalid and empty manifests disable actions; missing overlay is disclosed and retried', async ({
  page,
}) => {
  let response = { slide: {}, rois: [] };
  await page.route('**/wsi.json', (r) => r.fulfill({ json: response }));
  await page.goto('/wsi.html');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'error');
  await expect(page.locator('#modeCompare')).toBeDisabled();
  response = { ...data, rois: [] };
  await page.locator('#retryTiles').click();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'empty');
  await expect(page.locator('#modeTrace')).toBeDisabled();
  await page.unroute('**/wsi.json');
  const path = data.rois[0].methods.overlap.overlay;
  await page.route(`**/${path}`, (r) =>
    r.fulfill({ status: 404, body: 'missing' }),
  );
  await page.reload();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {
    timeout: 25000,
  });
  await expect(page.locator('#tileWarning')).toContainText('예측 오버레이');
  await expect(page.locator('#overlayB [data-mask="R1-overlap"]')).toHaveCount(
    0,
  );
  await page.unroute(`**/${path}`);
  await page.locator('#retryTiles').click();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {
    timeout: 25000,
  });
  await expect(page.locator('#overlayB [data-mask="R1-overlap"]')).toHaveCount(
    1,
  );
  await roi(page);
  await page.locator('#jumpDifference').click();
  await synced(page);
});
