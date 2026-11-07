/* Pure image-space geometry. Display zoom is CSS px per PNG px, never objective magnification. */
(function (root) {
  'use strict';
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  function fitZoom(width, height, imageWidth, imageHeight, padding = 12) {
    return Math.max(
      0.1,
      Math.min(
        (width - 2 * padding) / imageWidth,
        (height - 2 * padding) / imageHeight,
      ),
    );
  }
  function transform(width, height, zoom, cx, cy) {
    return {
      scale: zoom,
      ox: width / 2 - cx * zoom,
      oy: height / 2 - cy * zoom,
    };
  }
  function toImage(x, y, t) {
    return { x: (x - t.ox) / t.scale, y: (y - t.oy) / t.scale };
  }
  function bounds(width, height, zoom, cx, cy, imageWidth, imageHeight) {
    return {
      x0: clamp(cx - width / (2 * zoom), 0, imageWidth),
      y0: clamp(cy - height / (2 * zoom), 0, imageHeight),
      x1: clamp(cx + width / (2 * zoom), 0, imageWidth),
      y1: clamp(cy + height / (2 * zoom), 0, imageHeight),
    };
  }
  function clampCenter(width, height, zoom, cx, cy, imageWidth, imageHeight) {
    const hw = width / (2 * zoom),
      hh = height / (2 * zoom);
    return {
      x: hw >= imageWidth / 2 ? imageWidth / 2 : clamp(cx, hw, imageWidth - hw),
      y:
        hh >= imageHeight / 2
          ? imageHeight / 2
          : clamp(cy, hh, imageHeight - hh),
    };
  }
  function zoomAt(width, height, zoom, cx, cy, x, y, nextZoom) {
    const anchor = toImage(x, y, transform(width, height, zoom, cx, cy));
    return {
      zoom: nextZoom,
      x: anchor.x - (x - width / 2) / nextZoom,
      y: anchor.y - (y - height / 2) / nextZoom,
    };
  }
  function nearest(objects, x, y, zoom, radiusCSS = 12) {
    let found = -1,
      distance = radiusCSS * radiusCSS;
    objects.forEach((o, i) => {
      const d = ((o.x - x) ** 2 + (o.y - y) ** 2) * zoom * zoom;
      if (d <= distance) {
        distance = d;
        found = i;
      }
    });
    return found;
  }
  function visible(objects, b) {
    return objects
      .map((o, index) => ({ o, index }))
      .filter(
        ({ o }) => o.x >= b.x0 && o.x < b.x1 && o.y >= b.y0 && o.y < b.y1,
      );
  }
  const api = {
    clamp,
    fitZoom,
    transform,
    toImage,
    bounds,
    clampCenter,
    zoomAt,
    nearest,
    visible,
  };
  root.ViewerMath = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);
