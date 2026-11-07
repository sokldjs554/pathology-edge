const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'),
  vm = require('node:vm');
const context = {};
vm.runInNewContext(
  fs.readFileSync(__dirname + '/../dist/viewer-math.js', 'utf8'),
  context,
);
const M = context.ViewerMath;
test('cursor anchor remains the same source pixel through zoom', () => {
  for (const [w, h, z, cx, cy, x, y, next] of [
    [700, 500, 2, 270, 230, 103, 137, 5],
    [390, 400, 0.6, 256, 256, 300, 100, 1.5],
  ]) {
    const before = M.toImage(x, y, M.transform(w, h, z, cx, cy));
    const after = M.zoomAt(w, h, z, cx, cy, x, y, next);
    const actual = M.toImage(x, y, M.transform(w, h, next, after.x, after.y));
    assert.ok(Math.abs(actual.x - before.x) < 1e-10);
    assert.ok(Math.abs(actual.y - before.y) < 1e-10);
  }
});
test('pan cannot expose space outside the source when zoomed; small images remain centered', () => {
  const c = M.clampCenter(400, 300, 2, -100, 900, 512, 512);
  assert.equal(c.x, 100);
  assert.equal(c.y, 437);
  const b = M.bounds(400, 300, 2, c.x, c.y, 512, 512);
  assert.equal(b.x0, 0);
  assert.equal(b.y1, 512);
  const f = M.clampCenter(900, 700, 1, 100, -20, 512, 512);
  assert.equal(f.x, 256);
  assert.equal(f.y, 256);
});
test('fit shows the complete source with padding and round-trips image coordinates', () => {
  const z = M.fitZoom(400, 300, 512, 512);
  assert.equal(z, 276 / 512);
  const t = M.transform(400, 300, z, 256, 256),
    p = M.toImage(t.ox + 128 * z, t.oy + 384 * z, t);
  assert.equal(p.x, 128);
  assert.equal(p.y, 384);
});
test('selection radius stays fixed in screen pixels; visible filtering keeps original indexes', () => {
  const objects = [
    { x: 10, y: 10 },
    { x: 30, y: 30 },
    { x: 100, y: 100 },
  ];
  assert.equal(M.nearest(objects, 14, 10, 2), 0);
  assert.equal(M.nearest(objects, 14, 10, 4), -1);
  const list = M.visible(objects, { x0: 20, y0: 20, x1: 100, y1: 100 });
  assert.equal(list.length, 1);
  assert.equal(list[0].index, 1);
});
