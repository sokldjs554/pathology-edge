import { test, expect } from '@playwright/test';
import fs from 'node:fs';

const data = JSON.parse(
  fs.readFileSync(new URL('../dist/ihc/results.json', import.meta.url), 'utf8'),
);
const firstWrong = data.examples.find(
  (example) => example.kind === 'incorrect',
);
const ready = async (page, example = firstWrong) => {
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready');
  await expect(page.locator('#sourceImage')).toHaveAttribute(
    'data-example',
    example.id,
  );
  await expect(page.locator('#cropImage')).toHaveAttribute(
    'data-example',
    example.id,
  );
  await expect(page.locator('#truthLabel')).toHaveText(
    data.classes[example.gt_class].label_ko,
  );
  await expect(page.locator('#predictionLabel')).toHaveText(
    data.classes[example.pred_class].label_ko,
  );
};

test('IHC source pixels, all 16 real cases, GT coordinates and scores follow the export', async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/ihc.html');
  await ready(page);
  await expect(page.locator('#scopeNote')).toContainText('정답 중심점');
  await expect(page.locator('#scopeNote')).toContainText('검출');
  for (const kind of ['incorrect', 'correct']) {
    await page
      .locator(kind === 'incorrect' ? '#filterWrong' : '#filterCorrect')
      .click();
    const examples = data.examples.filter((example) => example.kind === kind);
    await expect(page.locator('.example-item')).toHaveCount(examples.length);
    for (const example of examples) {
      await page.locator('#exampleSelect').selectOption(example.id);
      await ready(page, example);
      await expect(page.locator('#gtPoint')).toHaveAttribute(
        'cx',
        String(example.center[0] + 0.5),
      );
      await expect(page.locator('#gtPoint')).toHaveAttribute(
        'cy',
        String(example.center[1] + 0.5),
      );
      await expect(page.locator('#cropPoint')).toHaveAttribute(
        'cx',
        String(example.point_in_crop[0] + 0.5),
      );
      await expect(page.locator('#cropPoint')).toHaveAttribute(
        'cy',
        String(example.point_in_crop[1] + 0.5),
      );
      await expect(page.locator('#sourceImage')).toHaveAttribute(
        'src',
        example.source_image,
      );
      await expect(page.locator('#cropImage')).toHaveAttribute(
        'src',
        example.crop_image,
      );
      await expect(page.locator('#selectedScore')).toHaveText(
        `${(example.confidence * 100).toFixed(1)}%`,
      );
      for (const [index, probability] of example.probabilities.entries()) {
        await expect(
          page.locator('.score-row').nth(index).locator('.score-number'),
        ).toHaveText(`${(probability * 100).toFixed(1)}%`);
      }
      const dimensions = await page
        .locator('#sourceImage')
        .evaluate((img) => [img.naturalWidth, img.naturalHeight]);
      expect(dimensions).toEqual(example.source_size);
    }
  }
  await page.locator('#showPoint').uncheck();
  await expect(page.locator('#sourceOverlay')).toBeHidden();
  await page.locator('#showPoint').check();
  await expect(page.locator('#sourceOverlay')).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath('ihc-desktop.png'),
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test('experiment metrics, confusion, split, limits and NC attribution retain real evidence', async ({
  page,
}) => {
  await page.goto('/ihc.html');
  await ready(page);
  await expect(page.locator('#testMacroF1')).toHaveText(
    data.metrics.test.macro_f1.toFixed(3),
  );
  await expect(page.locator('#testAccuracy')).toHaveText(
    data.metrics.test.accuracy.toFixed(3),
  );
  await expect(page.locator('#testCount')).toContainText('6,419');
  for (const [index, entry] of data.metrics.test.per_class.entries()) {
    const row = page.locator('#classMetrics tr').nth(index);
    await expect(row.locator('td').nth(1)).toHaveText(
      entry.precision.toFixed(3),
    );
    await expect(row.locator('td').nth(2)).toHaveText(entry.recall.toFixed(3));
    await expect(row.locator('td').nth(3)).toHaveText(entry.f1.toFixed(3));
  }
  await page.locator('#confusionDetails summary').click();
  for (const [rowIndex, row] of data.metrics.test.confusion_matrix.entries()) {
    for (const [column, value] of row.entries()) {
      await expect(
        page
          .locator('#confusionRows tr')
          .nth(rowIndex)
          .locator('td')
          .nth(column),
      ).toHaveText(value.toLocaleString('en-US'));
    }
  }
  await expect(page.locator('#splitRows tr')).toHaveCount(3);
  await expect(page.locator('#splitRows')).toContainText('15');
  await expect(page.locator('#splitRows')).toContainText('4');
  await expect(page.locator('#splitRows')).toContainText('10');
  await expect(page.locator('#statisticsDiscrepancy')).toContainText('19,972');
  await expect(page.locator('#statisticsDiscrepancy')).toContainText('36,673');
  await expect(page.locator('#patientLimit')).toContainText('독립');
  await expect(page.locator('#licenseLink')).toHaveAttribute(
    'href',
    data.attribution.license_url,
  );
  await expect(page.locator('#licenseLink')).toHaveText('CC BY-NC 4.0');
  await expect(page.locator('#authors')).toContainText('Štepec');
  await expect(page.locator('#modelLink')).toHaveAttribute(
    'href',
    'ihc/model.json',
  );
  await expect(page.locator('#modelHash')).toHaveText(data.model.sha256);
  await expect(page.locator('#scoreDisclaimer')).toContainText('보정');
});

for (const [width, height] of [
  [390, 844],
  [375, 667],
]) {
  test(`IHC image, example selection, crop and result drawer remain usable at ${width}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height });
    await page.goto('/ihc.html');
    await ready(page);
    await expect(page.locator('#inspector')).toBeHidden();
    const viewport = await page.locator('#imageStage').boundingBox();
    expect(viewport.height).toBeGreaterThan(160);
    const correct = data.examples
      .filter((example) => example.kind === 'correct')
      .at(-1);
    await page.locator('#filterCorrect').click();
    await page.locator('#exampleSelect').selectOption(correct.id);
    await ready(page, correct);
    await expect(page.locator('#cropImage')).toBeVisible();
    await page.locator('#toggleResults').click();
    await expect(page.locator('#inspector')).toBeVisible();
    await expect(page.locator('#testMacroF1')).toBeVisible();
    await page.locator('#closeResults').click();
    await expect(page.locator('#inspector')).toBeHidden();
    await page.locator('#toggleCases').click();
    await expect(page.locator('#examplePanel')).toBeVisible();
    await page.locator('.example-item').first().click();
    await expect(page.locator('#examplePanel')).toBeHidden();
    await ready(
      page,
      data.examples.find((example) => example.kind === 'correct'),
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      await page.evaluate(() => document.body.scrollHeight <= innerHeight),
    ).toBe(true);
    await page.screenshot({
      path: testInfo.outputPath(`ihc-${width}.png`),
      fullPage: true,
    });
  });
}

test('slow response shows a genuine loading state and no old classification', async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  await page.route('**/ihc/results.json', async (route) => {
    await gate;
    await route.fulfill({ json: data });
  });
  await page.goto('/ihc.html');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'loading');
  await expect(page.locator('#stageMessage')).toBeVisible();
  await expect(page.locator('#prevExample')).toBeDisabled();
  await expect(page.locator('#truthLabel')).toHaveText('—');
  release();
  await ready(page);
});

test('HTTP error can retry into the real experiment without inventing metrics', async ({
  page,
}) => {
  let attempt = 0;
  await page.route('**/ihc/results.json', (route) =>
    ++attempt === 1
      ? route.fulfill({ status: 503, body: 'unavailable' })
      : route.fulfill({ json: data }),
  );
  await page.goto('/ihc.html');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'error');
  await expect(page.locator('#stageDetail')).toContainText('503');
  await expect(page.locator('#testMacroF1')).toHaveText('—');
  await expect(page.locator('#imagePlane')).toBeHidden();
  await page.locator('#retryLoad').click();
  await ready(page);
  expect(attempt).toBe(2);
});

test('empty example collection stays empty, then retry restores supplied examples', async ({
  page,
}) => {
  let attempt = 0;
  await page.route('**/ihc/results.json', (route) =>
    route.fulfill({ json: ++attempt === 1 ? { ...data, examples: [] } : data }),
  );
  await page.goto('/ihc.html');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'empty');
  await expect(page.locator('#stageTitle')).toContainText('사례가 없습니다');
  await expect(page.locator('.example-item')).toHaveCount(0);
  await expect(page.locator('#sourceOverlay')).toBeHidden();
  await expect(page.locator('#exampleSelect')).toBeDisabled();
  await page.locator('#retryLoad').click();
  await ready(page);
});

test('missing source image is explicit and retry does not substitute another cell', async ({
  page,
}) => {
  await page.route(`**/${firstWrong.source_image}`, (route) =>
    route.fulfill({ status: 404, body: 'missing image' }),
  );
  await page.goto('/ihc.html');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'error');
  await expect(page.locator('#stageTitle')).toContainText('영상을');
  await expect(page.locator('#imagePlane')).toBeHidden();
  await expect(page.locator('#truthLabel')).toHaveText('—');
  await page.unroute(`**/${firstWrong.source_image}`);
  await page.locator('#retryLoad').click();
  await ready(page, firstWrong);
});

test('out-of-image ground-truth coordinate is rejected rather than displayed', async ({
  page,
}) => {
  const corrupt = structuredClone(data);
  corrupt.examples[0].center = [999, 4];
  await page.route('**/ihc/results.json', (route) =>
    route.fulfill({ json: corrupt }),
  );
  await page.goto('/ihc.html');
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'error');
  await expect(page.locator('#imagePlane')).toBeHidden();
  await expect(page.locator('#sourceOverlay')).toBeHidden();
});
