/* Pure views over saved candidates. No model execution or score recalculation. */
(function (root) {
  'use strict';
  const api = {
    rows(objects, { query = '', bounds = null, edgeOnly = false } = {}) {
      const id = String(query).trim().replace(/^#/, '');
      return objects.map((object, index) => ({ object, index })).filter(({ object: o, index }) =>
        (!id || String(index + 1) === id) &&
        (!edgeOnly || o.touches_edge) &&
        (!bounds || (o.x >= bounds.x0 && o.x < bounds.x1 && o.y >= bounds.y0 && o.y < bounds.y1))
      );
    },
    cropBox(object, width, height) {
      const [x0, y0, x1, y1] = object.bbox;
      const size = Math.max(64, x1 - x0 + 24, y1 - y0 + 24);
      const w = Math.min(width, size), h = Math.min(height, size);
      return {
        x: Math.max(0, Math.min(width - w, (x0 + x1 - w) / 2)),
        y: Math.max(0, Math.min(height - h, (y0 + y1 - h) / 2)),
        width: w, height: h,
      };
    },
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WorkbenchData = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
