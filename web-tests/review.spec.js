import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const data = JSON.parse(
  fs.readFileSync(new URL('../dist/results.json', import.meta.url)),
);
const evidence = JSON.parse(
  fs.readFileSync(new URL('../dist/cases.json', import.meta.url)),
);
const open = async (page) => {
  await page.goto('/');
  await expect(page.locator('#showImproved')).toBeEnabled();
};
const shot = (page, name) =>
  page.screenshot({ path: `captures/interview-${name}.png`, fullPage: true });
fs.mkdirSync('captures', { recursive: true });
const readyCase = async (page, id) => {
  const c = evidence.cases.find((c) => c.id === id);
  await expect(page.locator('#after')).toHaveAttribute('data-case', id);
  await expect(page.locator('#after')).toHaveAttribute(
    'data-center',
    c.center.map((v) => v.toFixed(3)).join(','),
  );
  await expect(page.locator('#sample')).toHaveValue(c.sample_id);
  await expect(page.locator('#caseScores')).toContainText(
    `${c.before.dice.toFixed(3)} → ${c.after.dice.toFixed(3)}`,
  );
  await expect(page.locator('#caseCounts')).toContainText(
    `정답 일치로 변경 ${c.corrected}px`,
  );
  await expect(page.locator('#caseCounts')).toContainText(
    `불일치로 변경 ${c.regressed}px`,
  );
  return c;
};

test('purpose, one-click improvement and regression, all real local cases and exact image metrics', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await open(page);
  await expect(page.locator('.review-guide')).toContainText(
    '경계의 핵 분할 결과',
  );
  await expect(page.locator('.workflow')).toContainText('예제 선택');
  await shot(page, 'first');
  for (const [button, direction] of [
    ['showImproved', 'improved'],
    ['showWorsened', 'worsened'],
  ]) {
    await page.locator('#' + button).click();
    const c = await readyCase(page, evidence.recommended[direction]);
    await expect(page.locator('#before')).toHaveAttribute('data-case', c.id);
    await expect(page.locator('#before')).toHaveAttribute(
      'data-center',
      c.center.map((v) => v.toFixed(3)).join(','),
    );
    await shot(page, direction);
  }
  for (const c of evidence.cases) {
    await page.locator('#caseSelect').selectOption(c.id);
    await readyCase(page, c.id);
    const s = data.samples.find((s) => s.id === c.sample_id);
    const row = page.locator('#imageMetrics tr').first();
    await expect(row.locator('td').nth(1)).toHaveText(
      s.methods.no_overlap.metrics.all.dice.toFixed(3),
    );
    await expect(row.locator('td').nth(2)).toHaveText(
      s.methods.overlap.metrics.all.dice.toFixed(3),
    );
  }
  await page.locator('#caseSelect').selectOption('10_1-worsened');
  await readyCase(page, '10_1-worsened');
  await shot(page, '10_1-worsened');
  await page.locator('#sample').selectOption('10_2');
  await expect(page.locator('#activeImage')).toHaveText('TNBC 10_2');
  await expect(page.locator('#caseDetail')).toBeHidden();
  await expect(page.locator('#after')).not.toHaveAttribute('data-case', /./);
  expect(errors).toEqual([]);
});

test('canvas highlight colors occur at the exported corrected and regressed pixel coordinates', async ({
  page,
}) => {
  await open(page);
  await page.locator('#showImproved').click();
  const c = await readyCase(page, evidence.recommended.improved);
  const points = [];
  for (const [key, color] of [
    ['corrected', [34, 211, 172]],
    ['regressed', [255, 69, 131]],
  ]) {
    points.push(
      ...c[key + '_runs']
        .filter(([y, x, n]) => y > 2 && y < 61 && x > 2 && x < 60)
        .slice(0, 8)
        .map(([y, x, n]) => ({ x: x + c.bbox[0], y: y + c.bbox[1], color })),
    );
  }
  expect(points.length).toBeGreaterThan(5);
  const pixels = () =>
    page.locator('#after').evaluate((canvas, points) => {
      const r = canvas.getBoundingClientRect(),
        ratio = canvas.width / r.width;
      const zoom = Number(canvas.dataset.zoom),
        [cx, cy] = canvas.dataset.center.split(',').map(Number);
      return points.map((p) => [
        ...canvas
          .getContext('2d')
          .getImageData(
            Math.floor((r.width / 2 + (p.x + 0.5 - cx) * zoom) * ratio),
            Math.floor((r.height / 2 + (p.y + 0.5 - cy) * zoom) * ratio),
            1,
            1,
          ).data,
      ]);
    }, points);
  await page.locator('#caseHighlight').uncheck();
  const plain = await pixels();
  await page.locator('#caseHighlight').check();
  const marked = await pixels();
  for (let i = 0; i < points.length; i++)
    for (let rgb = 0; rgb < 3; rgb++) {
      const expected = Math.round(
        plain[i][rgb] * (1 - 185 / 255) + (points[i].color[rgb] * 185) / 255,
      );
      expect(Math.abs(marked[i][rgb] - expected)).toBeLessThanOrEqual(2);
    }
});

test('aggregate cost, per-image changes and accessible glossary use original precision', async ({
  page,
}) => {
  await open(page);
  await page.locator('#showResults').click();
  await expect(page.locator('#costSummary')).toContainText('+0.035468');
  await expect(page.locator('#costSummary')).toContainText('+0.002789');
  await expect(page.locator('#costSummary')).toContainText('5.41배');
  for (const [i, scope] of ['all', 'boundary', 'interior'].entries()) {
    const row = page.locator('#performanceRows tr').nth(i);
    await expect(row.locator('td').nth(1)).toHaveText(
      data.summary.no_overlap.macro_dice[scope].toFixed(3),
    );
    await expect(row.locator('td').nth(2)).toHaveText(
      data.summary.overlap.macro_dice[scope].toFixed(3),
    );
  }
  await expect(page.locator('#imageDirectionSummary')).toContainText(
    '증가 3개 / 감소 4개',
  );
  await expect(page.locator('#perImageRows tr')).toHaveCount(7);
  await shot(page, 'experiment');
  await page.locator('#perImageRows button').first().click();
  await readyCase(page, '10_1-worsened');
  await expect(page.locator('#delta')).toHaveText('-0.014');
  await page.locator('#panelImage [data-terms]').click();
  await expect(page.locator('#termsDialog')).toBeVisible();
  for (const term of [
    'Dice',
    'IoU',
    'stride',
    '후보',
    '병합',
    'B(겹침) − A(무겹침)',
    '7개 이미지',
  ])
    await expect(page.locator('#termsDialog')).toContainText(term);
  await page.keyboard.press('Escape');
});

for (const [width, height] of [
  [1024, 768],
  [390, 844],
  [375, 667],
])
  test(`boundary review and same ROI A/B remain usable at ${width}x${height}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    await open(page);
    await page.locator('#showImproved').click();
    const c = await readyCase(page, evidence.recommended.improved);
    await expect(page.locator('#inspector')).toBeHidden();
    let box = await page.locator('#after').boundingBox();
    expect(box.height).toBeGreaterThan(170);
    const zoom = Number(await page.locator('#after').getAttribute('data-zoom'));
    expect(64 * zoom).toBeLessThan(Math.min(box.width, box.height));
    if (width <= 760) {
      await page.locator('#mobileBefore').click();
      await expect(page.locator('#before')).toHaveAttribute('data-case', c.id);
      await expect(page.locator('#before')).toHaveAttribute(
        'data-center',
        c.center.map((v) => v.toFixed(3)).join(','),
      );
      await page.locator('#mobileAfter').click();
    }
    await shot(page, String(width));
    await page.locator('#toggleInspector').click();
    await expect(page.locator('#caseScores')).toBeVisible();
    await page.locator('#closeInspector').click();
    await page.locator('#showWorsened').click();
    await readyCase(page, evidence.recommended.worsened);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <= innerWidth &&
          document.body.scrollHeight <= innerHeight,
      ),
    ).toBe(true);
  });

test('missing, mismatched or corrupt case evidence never fabricates a highlight', async ({
  page,
}) => {
  await page.route('**/cases.json', (route) =>
    route.fulfill({ status: 404, body: 'missing' }),
  );
  await page.goto('/');
  await expect(page.locator('#caseLoadNotice')).toContainText('HTTP 404');
  await expect(page.locator('#showImproved')).toBeDisabled();
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready');
  await expect(page.locator('#rawCount')).toHaveText('430');
  await shot(page, 'case-unavailable-injected');
  await page.unroute('**/cases.json');
  await page.route('**/cases.json', (route) =>
    route.fulfill({
      json: { ...evidence, source_sha256: { 'results.json': 'wrong' } },
    }),
  );
  await page.reload();
  await expect(page.locator('#caseLoadNotice')).toContainText(
    '출처가 다릅니다',
  );
  await expect(page.locator('#showImproved')).toBeDisabled();
  await page.unroute('**/cases.json');
  const corrupt = JSON.parse(JSON.stringify(evidence));
  corrupt.cases.find(
    (c) => c.id === corrupt.recommended.improved,
  ).corrected_runs = [];
  await page.route('**/cases.json', (route) =>
    route.fulfill({ json: corrupt }),
  );
  await open(page);
  await page.locator('#showImproved').click();
  await expect(page.locator('#caseLoadNotice')).toContainText(
    '실제 저장 마스크와 일치하지 않습니다',
  );
  await expect(page.locator('#caseDetail')).toBeHidden();
  await expect(page.locator('#after')).not.toHaveAttribute('data-case', /./);
});
