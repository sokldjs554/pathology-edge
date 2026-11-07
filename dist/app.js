'use strict';
const $ = (id) => document.getElementById(id),
  M = ViewerMath;
const state = {
  data: null,
  sample: null,
  images: {},
  phase: 'loading',
  mode: 'boundary',
  scope: 'all',
  zoom: 1,
  cx: 256,
  cy: 256,
  fitMode: true,
  selected: null,
  pair: null,
  request: 0,
  controller: null,
  tab: 'image',
  mobileSide: 'after',
  focus: false,
};
const canvases = [$('before'), $('after')],
  names = {
    classical: 'OpenCV',
    no_overlap: '무겹침',
    overlap: '겹침·병합',
    full: '512px 전체',
  };
const fmt = (n) => Number(n).toFixed(3),
  ms = (n) => `${(n * 1000).toFixed(1)} ms`;
const interactionIds = [
  'modeBoundary',
  'modeMerge',
  'modeSingle',
  'zoomout',
  'zoomin',
  'fit',
  'nativeZoom',
  'jumpBoundary',
  'segmentation',
  'objects',
  'grid',
  'truth',
  'opacity',
  'scopeAll',
  'scopeBoundary',
  'scopeInterior',
  'inspectMerge',
  'jumpDuplicate',
  'nativeZoom',
  'mobileBefore',
  'mobileAfter',
];
const scopeNames = {
  all: '전체 이미지',
  boundary: '기준 경계 ±8px',
  interior: '경계 제외 내부',
};
let animation = 0,
  resizePending = false;
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function imageLoad(src, signal) {
  return new Promise((resolve, reject) => {
    const im = new Image();
    let done = false;
    const cleanup = () => signal?.removeEventListener('abort', abort);
    const abort = () => {
      if (done) return;
      done = true;
      im.onload = im.onerror = null;
      cleanup();
      reject(new DOMException('Canceled', 'AbortError'));
    };
    im.onload = () => {
      if (done) return;
      done = true;
      cleanup();
      resolve(im);
    };
    im.onerror = () => {
      if (done) return;
      done = true;
      cleanup();
      reject(new Error(`이미지 파일을 읽지 못했습니다: ${src}`));
    };
    if (signal?.aborted) {
      abort();
      return;
    }
    signal?.addEventListener('abort', abort, { once: true });
    im.src = src;
  });
}
function setPhase(phase, title = '', detail = '') {
  state.phase = phase;
  document.body.dataset.phase = phase;
  $('stage').setAttribute('aria-busy', String(phase === 'loading'));
  $('stageMessage').hidden = phase === 'ready';
  $('navigatorBox').hidden = phase !== 'ready';
  $('stateTitle').textContent = title;
  $('stateDetail').textContent = detail;
  $('stateSymbol').textContent =
    phase === 'error' ? '!' : phase === 'empty' ? '□' : '◌';
  $('retry').hidden = phase !== 'error';
  $('stageMessage').setAttribute(
    'role',
    phase === 'error' ? 'alert' : 'status',
  );
  interactionIds.forEach((id) => ($(id).disabled = phase !== 'ready'));
  if (phase !== 'ready') {
    $('componentSelect').disabled = true;
    $('suppressionSelect').disabled = true;
  }
}
function activeCanvas() {
  return innerWidth <= 760
    ? $(
        state.mobileSide === 'before' && state.mode !== 'single'
          ? 'before'
          : 'after',
      )
    : $('after');
}
function dimensions(canvas) {
  const r = canvas.getBoundingClientRect();
  return { width: r.width, height: r.height };
}
function visibleCanvases() {
  return canvases.filter(
    (c) =>
      c.getBoundingClientRect().width > 0 &&
      c.getBoundingClientRect().height > 0,
  );
}
function clampView() {
  if (!state.sample) return;
  const { width, height } = dimensions(activeCanvas());
  if (!width || !height) return;
  const c = M.clampCenter(
    width,
    height,
    state.zoom,
    state.cx,
    state.cy,
    state.sample.width,
    state.sample.height,
  );
  state.cx = c.x;
  state.cy = c.y;
}
function fit() {
  if (!state.sample) return;
  const views = visibleCanvases();
  if (!views.length) return;
  state.zoom = Math.min(
    ...views.map((c) => {
      const d = dimensions(c);
      return M.fitZoom(
        d.width,
        d.height,
        state.sample.width,
        state.sample.height,
      );
    }),
  );
  state.cx = state.sample.width / 2;
  state.cy = state.sample.height / 2;
  state.fitMode = true;
  draw();
  renderObjectOptions();
}
function scheduleDraw() {
  if (animation) return;
  animation = requestAnimationFrame(() => {
    animation = 0;
    draw();
  });
}
function layerFrom(image, kind) {
  const c = document.createElement('canvas');
  c.width = image.width;
  c.height = image.height;
  const ctx = c.getContext('2d');
  ctx.drawImage(image, 0, 0);
  const d = ctx.getImageData(0, 0, c.width, c.height);
  for (let i = 0; i < d.data.length; i += 4) {
    const on = kind === 'truth' ? d.data[i] > 127 : d.data[i + 3] > 0;
    d.data[i] = kind === 'truth' ? 170 : 48;
    d.data[i + 1] = kind === 'truth' ? 109 : 188;
    d.data[i + 2] = kind === 'truth' ? 224 : 154;
    d.data[i + 3] = on ? 255 : 0;
  }
  ctx.putImageData(d, 0, 0);
  return c;
}
function scopeShade(width, height, scope) {
  const c = document.createElement('canvas');
  c.width = width;
  c.height = height;
  const ctx = c.getContext('2d');
  const d = ctx.createImageData(width, height);
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const seam = [128, 256, 384].some(
        (v) => (x >= v - 8 && x < v + 8) || (y >= v - 8 && y < v + 8),
      );
      const excluded = scope === 'boundary' ? !seam : seam;
      const i = (y * width + x) * 4;
      d.data[i + 3] = excluded ? 140 : 0;
    }
  ctx.putImageData(d, 0, 0);
  return c;
}
function paneData(side) {
  if (!state.sample) return null;
  if (side === 'before' && state.mode === 'merge') {
    const result = state.sample.methods.overlap;
    return { result, objects: result.raw, mask: 'overlap', raw: true };
  }
  const mode = side === 'before' ? 'no_overlap' : 'overlap';
  const result = state.sample.methods[mode];
  return { result, objects: result.objects, mask: mode, raw: false };
}
function currentBounds() {
  const d = dimensions(activeCanvas());
  return M.bounds(
    d.width,
    d.height,
    state.zoom,
    state.cx,
    state.cy,
    state.sample.width,
    state.sample.height,
  );
}
function draw() {
  if (state.phase !== 'ready' || !state.sample) return;
  for (const [i, canvas] of canvases.entries()) {
    const side = i ? 'after' : 'before',
      p = paneData(side),
      { width, height } = dimensions(canvas);
    if (!width || !height) continue;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    if (
      canvas.width !== Math.round(width * ratio) ||
      canvas.height !== Math.round(height * ratio)
    ) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
    }
    const ctx = canvas.getContext('2d'),
      t = M.transform(width, height, state.zoom, state.cx, state.cy);
    canvas.dataset.zoom = state.zoom.toFixed(5);
    canvas.dataset.center = `${state.cx.toFixed(3)},${state.cy.toFixed(3)}`;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = '#252a2e';
    ctx.fillRect(0, 0, width, height);
    ctx.save();
    ctx.translate(t.ox, t.oy);
    ctx.scale(t.scale, t.scale);
    ctx.drawImage(state.images.base, 0, 0);
    if ($('segmentation').checked) {
      ctx.globalAlpha = Number($('opacity').value) / 100;
      ctx.drawImage(state.images[p.mask], 0, 0);
      ctx.globalAlpha = 1;
    }
    if ($('truth').checked) {
      ctx.globalAlpha = Number($('opacity').value) / 100;
      ctx.drawImage(state.images.truth, 0, 0);
      ctx.globalAlpha = 1;
    }
    if (state.scope !== 'all') ctx.drawImage(state.images[state.scope], 0, 0);
    if ($('grid').checked) {
      ctx.strokeStyle = '#f0bb61';
      ctx.lineWidth = 1 / state.zoom;
      ctx.setLineDash([5 / state.zoom, 4 / state.zoom]);
      ctx.beginPath();
      for (let k = 128; k < state.sample.width; k += 128) {
        ctx.moveTo(k, 0);
        ctx.lineTo(k, state.sample.height);
      }
      for (let k = 128; k < state.sample.height; k += 128) {
        ctx.moveTo(0, k);
        ctx.lineTo(state.sample.width, k);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }
    if ($('objects').checked) {
      const suppressed = new Set(
        state.sample.methods.overlap.suppressed.map((r) => r.suppressed_index),
      );
      p.objects.forEach((o, index) => {
        ctx.strokeStyle =
          p.raw && suppressed.has(index) ? '#f0527b' : '#1679c9';
        ctx.lineWidth = 1.2 / state.zoom;
        ctx.beginPath();
        ctx.arc(o.x, o.y, 3.3 / state.zoom, 0, Math.PI * 2);
        ctx.stroke();
      });
    }
    const box = (o, color, dashed = false) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.8 / state.zoom;
      ctx.setLineDash(dashed ? [4 / state.zoom, 3 / state.zoom] : []);
      ctx.strokeRect(
        o.bbox[0] - 2 / state.zoom,
        o.bbox[1] - 2 / state.zoom,
        o.bbox[2] - o.bbox[0] + 4 / state.zoom,
        o.bbox[3] - o.bbox[1] + 4 / state.zoom,
      );
      ctx.setLineDash([]);
    };
    if (state.pair && state.mode === 'merge') {
      if (side === 'before') {
        box(state.pair.raw, '#ff557f');
        box(state.pair.kept, '#48c7ff', true);
        ctx.beginPath();
        ctx.strokeStyle = '#f1d1dc';
        ctx.lineWidth = 1 / state.zoom;
        ctx.setLineDash([3 / state.zoom, 3 / state.zoom]);
        ctx.moveTo(state.pair.raw.x, state.pair.raw.y);
        ctx.lineTo(state.pair.kept.x, state.pair.kept.y);
        ctx.stroke();
        ctx.setLineDash([]);
      } else box(state.pair.kept, '#48c7ff');
    } else if (state.selected) {
      box(state.selected.o, '#f9e45e');
      ctx.beginPath();
      ctx.strokeStyle = '#ffeb69';
      ctx.lineWidth = 1 / state.zoom;
      const { x, y } = state.selected.o,
        r = 11 / state.zoom;
      ctx.moveTo(x - r, y);
      ctx.lineTo(x + r, y);
      ctx.moveTo(x, y - r);
      ctx.lineTo(x, y + r);
      ctx.stroke();
    }
    ctx.restore();
    // The only calibrated ruler available is in source PNG pixels.
    const unit = [5, 10, 20, 50, 100, 200].reduce(
        (a, b) =>
          Math.abs(b * state.zoom - 65) < Math.abs(a * state.zoom - 65) ? b : a,
        5,
      ),
      bar = unit * state.zoom;
    ctx.fillStyle = '#172027c9';
    ctx.fillRect(10, height - 39, bar + 16, 31);
    ctx.strokeStyle = '#e1e9ee';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(18, height - 22);
    ctx.lineTo(18 + bar, height - 22);
    ctx.stroke();
    ctx.font = '10px Arial';
    ctx.fillStyle = '#e1e9ee';
    ctx.fillText(`${unit} px`, 18, height - 9);
  }
  const b = currentBounds();
  $('viewportBounds').textContent =
    `현재 시야 x ${Math.floor(b.x0)}–${Math.ceil(b.x1)} · y ${Math.floor(b.y0)}–${Math.ceil(b.y1)}`;
  $('zoomvalue').textContent = `${Math.round(state.zoom * 100)}%`;
  const n = $('navigator'),
    ctx = n.getContext('2d');
  ctx.clearRect(0, 0, n.width, n.height);
  ctx.drawImage(state.images.base, 0, 0, n.width, n.height);
  const sx = n.width / state.sample.width,
    sy = n.height / state.sample.height;
  ctx.fillStyle = '#182e4333';
  ctx.fillRect(0, 0, n.width, n.height);
  ctx.drawImage(
    state.images.base,
    b.x0,
    b.y0,
    Math.max(0.01, b.x1 - b.x0),
    Math.max(0.01, b.y1 - b.y0),
    b.x0 * sx,
    b.y0 * sy,
    Math.max(0.01, (b.x1 - b.x0) * sx),
    Math.max(0.01, (b.y1 - b.y0) * sy),
  );
  ctx.strokeStyle = '#ffe05d';
  ctx.lineWidth = 2;
  ctx.strokeRect(
    Math.max(1, b.x0 * sx),
    Math.max(1, b.y0 * sy),
    Math.min(n.width - 2, (b.x1 - b.x0) * sx),
    Math.min(n.height - 2, (b.y1 - b.y0) * sy),
  );
}
function setTab(tab, open = true) {
  state.tab = tab;
  for (const name of ['Image', 'Object', 'Experiment']) {
    const yes = name.toLowerCase() === tab;
    $(`tab${name}`).setAttribute('aria-selected', String(yes));
    $(`tab${name}`).tabIndex = yes ? 0 : -1;
    $(`panel${name}`).hidden = !yes;
  }
  if (open) {
    $('workbench').classList.remove('inspector-hidden');
    $('toggleInspector').setAttribute('aria-expanded', 'true');
  }
  if (tab === 'object') renderObjectOptions();
}
function updatePanels() {
  if (!state.sample) return;
  const a = state.sample.methods.no_overlap,
    b = state.sample.methods.overlap;
  $('activeImage').textContent = `TNBC ${state.sample.id}`;
  $('imageTitle').textContent = `${state.sample.id} · H&E · 512 × 512 px`;
  $('imageMetrics').replaceChildren();
  for (const [key, label] of [
    ['dice', 'Dice'],
    ['iou', 'IoU'],
    ['precision', 'Precision'],
    ['recall', 'Recall'],
  ]) {
    const tr = node('tr');
    tr.append(
      node('td', label),
      node('td', fmt(a.metrics[state.scope][key])),
      node('td', fmt(b.metrics[state.scope][key])),
    );
    $('imageMetrics').append(tr);
  }
  const delta = b.metrics[state.scope].dice - a.metrics[state.scope].dice;
  $('delta').textContent = `${delta >= 0 ? '+' : ''}${fmt(delta)}`;
  $('delta').className = delta >= 0 ? 'positive' : 'negative';
  $('metricScope').textContent =
    state.scope === 'all' ? '전체 512 × 512 px' : scopeNames[state.scope];
  $('scopeExplanation').textContent =
    state.scope === 'all'
      ? '아래 지표는 전체 이미지 기준입니다. 확대·이동해도 재계산하지 않습니다.'
      : state.scope === 'boundary'
        ? '밝게 남긴 띠가 평가 영역입니다. 기준 경계 양쪽 8px의 저장된 지표이며 현재 시야 점수가 아닙니다.'
        : '기준 경계 양쪽 8px를 제외한 영역입니다. 어둡게 표시한 띠는 계산에서 제외합니다.';
  $('rawCount').textContent = b.raw_count;
  $('mergedCount').textContent = b.merged_count;
  $('suppressedCount').textContent = b.suppressed_count;
  $('timing').textContent = `${ms(a.median_seconds)} / ${ms(b.median_seconds)}`;
  $('modelShort').textContent = `TinyUNet / ${state.data.threshold}`;
  $('beforeTitle').textContent =
    state.mode === 'merge' ? '겹침 · 병합 전' : '무겹침';
  $('afterTitle').textContent =
    state.mode === 'merge' ? '겹침 · 병합 후' : '겹침 + 병합';
  $('beforeMeta').textContent =
    state.mode === 'merge' ? 'raw 후보' : 'stride 128';
  $('afterMeta').textContent = state.mode === 'merge' ? 'NMS 후' : 'stride 64';
  $('countBefore').textContent =
    `${state.mode === 'merge' ? b.raw_count : a.merged_count} 후보`;
  $('countAfter').textContent = `${b.merged_count} 후보`;
  $('diceBefore').textContent =
    state.mode === 'merge'
      ? `원시 후보 ${b.raw_count}`
      : `Dice ${fmt(a.metrics[state.scope].dice)}`;
  $('diceAfter').textContent =
    state.mode === 'merge'
      ? `유지 ${b.merged_count} · 억제 ${b.suppressed_count}`
      : `Dice ${fmt(b.metrics[state.scope].dice)}`;
  $('scopeBefore').textContent = $('scopeAfter').textContent =
    state.mode === 'merge'
      ? '동일 겹침 추론 · 성분 경로'
      : scopeNames[state.scope];
  $('mobileBefore').textContent =
    state.mode === 'merge' ? 'A 병합 전' : 'A 무겹침';
  $('mobileAfter').textContent =
    state.mode === 'merge' ? 'B 병합 후' : 'B 겹침 처리';
  $('objectSource').options[1].text =
    state.mode === 'merge' ? 'A · 병합 전 raw' : 'A · 무겹침';
  $('jumpDuplicate').disabled = !b.suppressed.length;
  $('mobileBefore').disabled = state.mode === 'single';
}
function clearSelection() {
  state.selected = null;
  state.pair = null;
  $('pairInfo').textContent =
    '분홍 상자는 억제 후보, 파란 상자는 유지 후보입니다. 두 후보가 같은 실제 핵인지는 별도 검토가 필요합니다.';
  $('selectedInfo').replaceChildren();
  $('selectionEmpty').hidden = false;
  $('selectionText').textContent =
    '후보 표시를 켜고 원을 누르거나 아래 목록에서 선택하세요.';
}
function setMode(mode) {
  if (state.phase !== 'ready') return;
  state.mode = mode;
  if (mode === 'merge') $('objects').checked = true;
  clearSelection();
  $('workbench').dataset.mode = mode;
  for (const [id, value] of [
    ['modeBoundary', 'boundary'],
    ['modeMerge', 'merge'],
    ['modeSingle', 'single'],
  ])
    $(id).setAttribute('aria-pressed', String(mode === value));
  $('panes').classList.toggle('single', mode === 'single');
  $('mobileBefore').disabled = mode === 'single';
  if (mode === 'single') setMobileSide('after');
  $('modeDescription').textContent =
    mode === 'merge'
      ? '같은 겹침 추론 · 분홍: 억제 후보 / 파랑: 유지 후보'
      : mode === 'single'
        ? '겹침 처리 영상 단일 검토 · 결과 패널에서 기준 방식과 수치 비교'
        : '같은 모델 · 무겹침과 64px 겹침을 같은 시야에서 비교';
  updatePanels();
  renderObjectOptions();
  requestAnimationFrame(() => {
    if (state.fitMode) fit();
    else {
      clampView();
      draw();
    }
  });
}
function setScope(scope) {
  state.scope = scope;
  for (const [id, value] of [
    ['scopeAll', 'all'],
    ['scopeBoundary', 'boundary'],
    ['scopeInterior', 'interior'],
  ])
    $(id).setAttribute('aria-pressed', String(value === scope));
  updatePanels();
  draw();
}
function renderObjectOptions() {
  if (!state.sample) return;
  const side = $('objectSource').value,
    p = paneData(side);
  let list = p.objects.map((o, index) => ({ o, index }));
  if ($('visibleOnly').checked) list = M.visible(p.objects, currentBounds());
  const selected =
    state.selected?.side === side ? String(state.selected.index) : '';
  const hint = new Option(
    list.length ? `${list.length}개 후보 · 선택…` : '현재 시야에 후보 없음',
    '',
  );
  hint.disabled = true;
  $('componentSelect').replaceChildren(
    hint,
    ...list.map(
      ({ o, index }) =>
        new Option(
          `#${index + 1} · (${o.x.toFixed(0)}, ${o.y.toFixed(0)})`,
          String(index),
        ),
    ),
  );
  $('componentSelect').value = list.some(
    ({ index }) => String(index) === selected,
  )
    ? selected
    : '';
  $('componentSelect').disabled = !list.length;
}
function selectObject(side, index, move = false) {
  if (!state.sample) return;
  const p = paneData(side),
    o = p.objects[index];
  if (!o) return;
  state.selected = { side, index, o };
  state.pair = null;
  $('objects').checked = true;
  $('objectSource').value = side;
  $('selectionEmpty').hidden = true;
  $('selectionText').textContent =
    `${side === 'before' ? 'A' : 'B'} · ${p.raw ? '병합 전 raw' : side === 'before' ? '무겹침' : '병합 후'} #${index + 1}`;
  const info = [
    ['중심 x, y', `${o.x.toFixed(1)}, ${o.y.toFixed(1)} px`],
    ['상자 x₀,y₀,x₁,y₁', o.bbox.join(', ')],
    ['patch ID', String(o.patch_id)],
    ['성분 면적', `${o.area} px²`],
    ['확률 평균', fmt(o.score)],
    ['패치 경계 접촉', o.touches_edge ? '있음' : '없음'],
  ];
  $('selectedInfo').replaceChildren();
  info.forEach(([k, v]) =>
    $('selectedInfo').append(node('dt', k), node('dd', v)),
  );
  setTab('object');
  if (move) {
    state.cx = o.x;
    state.cy = o.y;
    state.zoom = Math.max(state.zoom, 3);
    state.fitMode = false;
  }
  requestAnimationFrame(() => {
    clampView();
    draw();
    renderObjectOptions();
  });
}
function selectPair(index) {
  if (state.phase !== 'ready') return;
  const b = state.sample.methods.overlap,
    pair = b.suppressed[index];
  if (!pair) return;
  if (state.mode !== 'merge') setMode('merge');
  const keptIndex = b.objects.findIndex((o) => o.raw_index === pair.kept_index);
  selectObject('after', keptIndex, false);
  state.pair = {
    raw: b.raw[pair.suppressed_index],
    kept: b.raw[pair.kept_index],
  };
  state.cx = (state.pair.raw.x + state.pair.kept.x) / 2;
  state.cy = (state.pair.raw.y + state.pair.kept.y) / 2;
  state.zoom = 4;
  state.fitMode = false;
  $('suppressionSelect').value = String(index);
  $('pairInfo').textContent =
    `억제 raw #${pair.suppressed_index + 1} (patch ${state.pair.raw.patch_id}) → 유지 raw #${pair.kept_index + 1} (patch ${state.pair.kept.patch_id}). NMS가 연결한 후보 쌍이며 실제로 같은 핵인지는 검토가 필요합니다.`;
  requestAnimationFrame(() => {
    clampView();
    draw();
    renderObjectOptions();
  });
}
function setMobileSide(side) {
  state.mobileSide = side;
  $('panes').classList.toggle('show-before', side === 'before');
  $('mobileBefore').setAttribute('aria-pressed', String(side === 'before'));
  $('mobileAfter').setAttribute('aria-pressed', String(side === 'after'));
  scheduleDraw();
}
function validateData(data) {
  if (
    !data ||
    !Array.isArray(data.samples) ||
    !data.summary ||
    !Array.isArray(data.limits)
  )
    throw new Error('결과 파일 형식을 확인해 주세요.');
  for (const s of data.samples) {
    if (
      typeof s.id !== 'string' ||
      s.width !== 512 ||
      s.height !== 512 ||
      !s.methods?.overlap?.metrics?.all ||
      !s.methods?.no_overlap?.objects
    )
      throw new Error('예제의 이미지·결과 정보가 올바르지 않습니다.');
  }
  return data;
}
function populateData() {
  const data = state.data;
  $('sampleCount').textContent = data.samples.length;
  $('traySampleCount').textContent = data.samples.length;
  $('sample').replaceChildren(
    ...data.samples.map((s) => new Option(`TNBC ${s.id}`, s.id)),
  );
  $('sample').disabled = !data.samples.length;
  if (!data.samples.length) $('sample').append(new Option('예제 없음', ''));
  $('sampleList').replaceChildren();
  for (const s of data.samples) {
    const button = node('button', undefined, 'sample-item');
    button.dataset.sample = s.id;
    button.setAttribute('aria-label', `TNBC ${s.id} 열기`);
    button.setAttribute('aria-current', 'false');
    const img = node('img');
    img.src = s.image;
    img.alt = '';
    img.loading = 'lazy';
    const d =
      s.methods.overlap.metrics.all.dice -
      s.methods.no_overlap.metrics.all.dice;
    button.append(
      img,
      node('span', s.id, 'sample-name'),
      node(
        'span',
        `Δ ${d >= 0 ? '+' : ''}${fmt(d)}`,
        `sample-delta ${d < 0 ? 'negative' : ''}`,
      ),
    );
    button.addEventListener('click', () => loadSample(s.id));
    $('sampleList').append(button);
  }
  $('limits').replaceChildren(...data.limits.map((text) => node('li', text)));
  $('summaryRows').replaceChildren();
  for (const [mode, r] of Object.entries(data.summary)) {
    const tr = node('tr');
    if (mode === 'overlap') tr.className = 'highlight';
    tr.append(
      node('td', names[mode]),
      node('td', fmt(r.macro_dice.all)),
      node('td', fmt(r.macro_dice.boundary)),
    );
    $('summaryRows').append(tr);
  }
  $('provenanceBody').replaceChildren(
    node(
      'p',
      `${data.dataset}. train 33 / validation 10 / test 7. 케이스 그룹 분리.`,
    ),
    node(
      'p',
      `${data.model}. seed ${data.seed}, threshold ${data.threshold}. 학습 ${data.training_seconds.toFixed(1)}초.`,
    ),
    node('p', '모델 SHA-256'),
    node('div', data.model_sha256, 'hash'),
    node(
      'p',
      `독립 프로세스 peak RSS: 무겹침 ${data.summary.no_overlap.peak_process_rss_mib.toFixed(1)} / 겹침 ${data.summary.overlap.peak_process_rss_mib.toFixed(1)} MiB.`,
    ),
  );
}
function resetNumbers() {
  for (const id of [
    'delta',
    'rawCount',
    'mergedCount',
    'suppressedCount',
    'timing',
    'modelShort',
    'countBefore',
    'countAfter',
    'diceBefore',
    'diceAfter',
  ])
    $(id).textContent = '—';
  $('imageMetrics').replaceChildren();
  $('activeImage').textContent = '결과 대기';
  $('viewportBounds').textContent = '현재 시야 —';
  $('cursorPosition').textContent = 'x — · y — px';
  $('componentSelect').replaceChildren(new Option('선택할 후보 없음', ''));
  $('suppressionSelect').replaceChildren(new Option('병합 사례 없음', ''));
  clearSelection();
}
async function loadSample(id) {
  if (!state.data) return;
  const candidate = state.data.samples.find((s) => s.id === id);
  if (!candidate) return;
  state.controller?.abort();
  const controller = new AbortController();
  state.controller = controller;
  const ticket = ++state.request;
  state.sample = null;
  resetNumbers();
  setPhase(
    'loading',
    `TNBC ${id}의 저장된 결과를 읽는 중`,
    '이미지와 오버레이를 불러옵니다. 새로운 추론을 실행하지 않습니다.',
  );
  $('status').textContent = `${id} 결과 파일 불러오는 중…`;
  $('imageTitle').textContent = `${id} · 결과 파일 로딩`;
  $('sample').value = id;
  const timeout = setTimeout(
    () => controller.abort(new Error('timeout')),
    15000,
  );
  try {
    const [base, before, after, truth] = await Promise.all([
      imageLoad(candidate.image, controller.signal),
      imageLoad(candidate.methods.no_overlap.overlay, controller.signal),
      imageLoad(candidate.methods.overlap.overlay, controller.signal),
      imageLoad(candidate.gt, controller.signal),
    ]);
    if (ticket !== state.request) return;
    if (
      [base, before, after, truth].some(
        (im) => im.width !== candidate.width || im.height !== candidate.height,
      )
    )
      throw new Error('이미지와 결과의 크기가 다릅니다.');
    state.sample = candidate;
    state.images = {
      base,
      no_overlap: layerFrom(before, 'mask'),
      overlap: layerFrom(after, 'mask'),
      truth: layerFrom(truth, 'truth'),
      boundary: scopeShade(512, 512, 'boundary'),
      interior: scopeShade(512, 512, 'interior'),
    };
    state.cx = 256;
    state.cy = 256;
    state.fitMode = true;
    setPhase('ready');
    document
      .querySelectorAll('.sample-item')
      .forEach((el) =>
        el.setAttribute('aria-current', String(el.dataset.sample === id)),
      );
    const list = candidate.methods.overlap.suppressed;
    const empty = new Option(
      list.length ? `${list.length}개 억제 대응 · 선택…` : '병합 사례 없음',
      '',
    );
    empty.disabled = true;
    empty.selected = true;
    $('suppressionSelect').replaceChildren(
      empty,
      ...list.map(
        (p, i) =>
          new Option(
            `raw #${p.suppressed_index + 1} → #${p.kept_index + 1}`,
            String(i),
          ),
      ),
    );
    $('suppressionSelect').disabled = !list.length;
    updatePanels();
    renderObjectOptions();
    $('status').textContent = `${id} · 저장된 실제 결과 · PNG 픽셀 좌표`;
    if (innerWidth <= 760) {
      $('workbench').classList.add('tray-hidden');
      $('toggleTray').setAttribute('aria-expanded', 'false');
    }
    history.replaceState(
      null,
      '',
      `${location.pathname}?sample=${encodeURIComponent(id)}`,
    );
    requestAnimationFrame(fit);
  } catch (error) {
    if (ticket !== state.request) return;
    state.sample = null;
    setPhase(
      'error',
      `TNBC ${id}를 불러오지 못했습니다`,
      error.name === 'AbortError'
        ? '15초 안에 파일을 받지 못했습니다. 연결을 확인한 뒤 다시 시도하세요.'
        : error.message,
    );
    $('status').textContent =
      `${id} 로딩 실패 · 이전 이미지의 수치는 표시하지 않습니다.`;
    $('imageTitle').textContent = `${id} · 로딩 실패`;
  } finally {
    clearTimeout(timeout);
  }
}
async function init() {
  state.controller?.abort();
  const controller = new AbortController();
  state.controller = controller;
  const ticket = ++state.request;
  setPhase(
    'loading',
    '저장된 분석 목록을 읽는 중',
    '실시간 추론이 아니라 공개 예제의 결과 파일을 불러옵니다.',
  );
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch('results.json', { signal: controller.signal });
    if (!response.ok)
      throw new Error(`결과 파일 응답 오류 (HTTP ${response.status})`);
    const data = validateData(await response.json());
    if (ticket !== state.request) return;
    state.data = data;
    populateData();
    if (!data.samples.length) {
      state.sample = null;
      resetNumbers();
      setPhase(
        'empty',
        '표시할 예제가 없습니다',
        '결과 파일에 공개 예제가 없습니다. 새 분석이 실행된 상태가 아닙니다.',
      );
      $('status').textContent = '예제 0개';
      return;
    }
    const requested = new URLSearchParams(location.search).get('sample');
    await loadSample(
      data.samples.some((s) => s.id === requested)
        ? requested
        : data.samples[0].id,
    );
  } catch (error) {
    if (ticket !== state.request) return;
    setPhase(
      'error',
      '분석 목록을 불러오지 못했습니다',
      error.name === 'AbortError'
        ? '응답 시간이 초과되었습니다. 다시 시도하세요.'
        : error.message,
    );
    $('status').textContent = '결과 파일 로딩 실패';
  } finally {
    clearTimeout(timeout);
  }
}
function setZoom(next, x, y, canvas = activeCanvas()) {
  if (state.phase !== 'ready') return;
  const d = dimensions(canvas);
  const n = M.zoomAt(
    d.width,
    d.height,
    state.zoom,
    state.cx,
    state.cy,
    x ?? d.width / 2,
    y ?? d.height / 2,
    M.clamp(next, 0.2, 16),
  );
  state.zoom = n.zoom;
  state.cx = n.x;
  state.cy = n.y;
  state.fitMode = false;
  clampView();
  draw();
  renderObjectOptions();
}
function eventPoint(event, canvas) {
  const r = canvas.getBoundingClientRect();
  return { x: event.clientX - r.left, y: event.clientY - r.top };
}
for (const [i, canvas] of canvases.entries()) {
  let drag = null,
    pinch = null;
  const pointers = new Map();
  canvas.addEventListener(
    'wheel',
    (e) => {
      if (state.phase !== 'ready') return;
      e.preventDefault();
      const d = dimensions(canvas);
      const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? d.height : 1;
      const dx = e.deltaX * unit,
        dy = e.deltaY * unit;
      if (e.ctrlKey || e.metaKey) {
        const p = eventPoint(e, canvas);
        setZoom(state.zoom * Math.exp(-dy * 0.002), p.x, p.y, canvas);
      } else {
        // Trackpad two-finger scrolling and ordinary wheels translate the view.
        state.cx += dx / state.zoom;
        state.cy += dy / state.zoom;
        state.fitMode = false;
        clampView();
        draw();
        renderObjectOptions();
      }
    },
    { passive: false },
  );
  canvas.addEventListener('pointerdown', (e) => {
    if (state.phase !== 'ready') return;
    const p = eventPoint(e, canvas);
    pointers.set(e.pointerId, p);
    canvas.setPointerCapture(e.pointerId);
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { distance: Math.hypot(a.x - b.x, a.y - b.y) };
      drag = null;
    } else drag = { x: p.x, y: p.y, cx: state.cx, cy: state.cy, moved: false };
  });
  canvas.addEventListener('pointermove', (e) => {
    if (state.phase !== 'ready') return;
    const p = eventPoint(e, canvas),
      d = dimensions(canvas),
      q = M.toImage(
        p.x,
        p.y,
        M.transform(d.width, d.height, state.zoom, state.cx, state.cy),
      );
    $('cursorPosition').textContent =
      q.x >= 0 && q.y >= 0 && q.x < 512 && q.y < 512
        ? `x ${q.x.toFixed(1)} · y ${q.y.toFixed(1)} px`
        : '영상 밖';
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, p);
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()],
        distance = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch.distance > 0)
        setZoom(
          (state.zoom * distance) / pinch.distance,
          (a.x + b.x) / 2,
          (a.y + b.y) / 2,
          canvas,
        );
      pinch.distance = distance;
      return;
    }
    if (!drag) return;
    if (Math.abs(p.x - drag.x) + Math.abs(p.y - drag.y) > 4) drag.moved = true;
    state.cx = drag.cx - (p.x - drag.x) / state.zoom;
    state.cy = drag.cy - (p.y - drag.y) / state.zoom;
    state.fitMode = false;
    clampView();
    scheduleDraw();
  });
  canvas.addEventListener('pointerup', (e) => {
    pointers.delete(e.pointerId);
    if (pinch) {
      pinch = null;
      drag = null;
      return;
    }
    if (drag && !drag.moved && state.sample && $('objects').checked) {
      const p = eventPoint(e, canvas),
        d = dimensions(canvas),
        q = M.toImage(
          p.x,
          p.y,
          M.transform(d.width, d.height, state.zoom, state.cx, state.cy),
        ),
        side = i ? 'after' : 'before',
        list = paneData(side).objects;
      const nearest = M.nearest(list, q.x, q.y, state.zoom);
      if (nearest >= 0) selectObject(side, nearest);
    }
    drag = null;
    renderObjectOptions();
  });
  canvas.addEventListener('pointercancel', () => {
    drag = null;
    pinch = null;
    pointers.clear();
  });
  canvas.addEventListener('keydown', (e) => {
    if (state.phase !== 'ready') return;
    if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      setZoom(state.zoom * 1.25);
    } else if (e.key === '-') {
      e.preventDefault();
      setZoom(state.zoom / 1.25);
    } else if (e.key.toLowerCase() === 'f') {
      e.preventDefault();
      fit();
    } else if (
      ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)
    ) {
      e.preventDefault();
      state.cx +=
        (e.key === 'ArrowRight' ? 35 : e.key === 'ArrowLeft' ? -35 : 0) /
        state.zoom;
      state.cy +=
        (e.key === 'ArrowDown' ? 35 : e.key === 'ArrowUp' ? -35 : 0) /
        state.zoom;
      state.fitMode = false;
      clampView();
      draw();
      renderObjectOptions();
    }
  });
}
function navigateMini(e) {
  if (state.phase !== 'ready') return;
  const r = $('navigator').getBoundingClientRect();
  state.cx = ((e.clientX - r.left) / r.width) * state.sample.width;
  state.cy = ((e.clientY - r.top) / r.height) * state.sample.height;
  state.fitMode = false;
  clampView();
  draw();
  renderObjectOptions();
}
let miniDrag = false;
$('navigator').addEventListener('pointerdown', (e) => {
  miniDrag = true;
  $('navigator').setPointerCapture(e.pointerId);
  navigateMini(e);
});
$('navigator').addEventListener('pointermove', (e) => {
  if (miniDrag) navigateMini(e);
});
$('navigator').addEventListener('pointerup', () => {
  miniDrag = false;
});
$('navigator').addEventListener('pointercancel', () => {
  miniDrag = false;
});
$('navigator').addEventListener('keydown', (e) => {
  if (!e.key.startsWith('Arrow') || state.phase !== 'ready') return;
  e.preventDefault();
  state.cx += e.key === 'ArrowRight' ? 30 : e.key === 'ArrowLeft' ? -30 : 0;
  state.cy += e.key === 'ArrowDown' ? 30 : e.key === 'ArrowUp' ? -30 : 0;
  state.fitMode = false;
  clampView();
  draw();
  renderObjectOptions();
});
$('sample').addEventListener('change', () => loadSample($('sample').value));
$('retry').addEventListener('click', () =>
  state.data?.samples.length ? loadSample($('sample').value) : init(),
);
$('modeBoundary').addEventListener('click', () => setMode('boundary'));
$('modeMerge').addEventListener('click', () => setMode('merge'));
$('modeSingle').addEventListener('click', () => setMode('single'));
$('scopeAll').addEventListener('click', () => setScope('all'));
$('scopeBoundary').addEventListener('click', () => setScope('boundary'));
$('scopeInterior').addEventListener('click', () => setScope('interior'));
$('zoomin').addEventListener('click', () => setZoom(state.zoom * 1.25));
$('zoomout').addEventListener('click', () => setZoom(state.zoom / 1.25));
$('nativeZoom').addEventListener('click', () => setZoom(1));
$('fit').addEventListener('click', fit);
$('jumpBoundary').addEventListener('click', () => {
  if (state.mode !== 'boundary') setMode('boundary');
  $('grid').checked = true;
  state.cx = 256;
  state.cy = 256;
  state.zoom = 3;
  state.fitMode = false;
  clampView();
  draw();
  renderObjectOptions();
});
for (const id of ['segmentation', 'objects', 'grid', 'truth'])
  $(id).addEventListener('change', draw);
$('opacity').addEventListener('input', () => {
  $('opacityValue').textContent = `${$('opacity').value}%`;
  draw();
});
$('inspectMerge').addEventListener('click', () => {
  setMode('merge');
  setTab('object');
});
$('jumpDuplicate').addEventListener('click', () => selectPair(0));
$('suppressionSelect').addEventListener('change', () =>
  selectPair(Number($('suppressionSelect').value)),
);
$('objectSource').addEventListener('change', () => {
  clearSelection();
  renderObjectOptions();
  draw();
});
$('componentSelect').addEventListener('change', () =>
  selectObject(
    $('objectSource').value,
    Number($('componentSelect').value),
    true,
  ),
);
$('visibleOnly').addEventListener('change', renderObjectOptions);
for (const name of ['Image', 'Object', 'Experiment'])
  $(`tab${name}`).addEventListener('click', () =>
    setTab(name.toLowerCase(), false),
  );
const tabs = ['tabImage', 'tabObject', 'tabExperiment'];
tabs.forEach((id, index) =>
  $(id).addEventListener('keydown', (e) => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const next =
      e.key === 'Home'
        ? 0
        : e.key === 'End'
          ? 2
          : (index + (e.key === 'ArrowRight' ? 1 : 2)) % 3;
    $(tabs[next]).click();
    $(tabs[next]).focus();
  }),
);
$('mobileBefore').addEventListener('click', () => setMobileSide('before'));
$('mobileAfter').addEventListener('click', () => setMobileSide('after'));
function togglePanel(which) {
  const cls = which === 'tray' ? 'tray-hidden' : 'inspector-hidden',
    button = which === 'tray' ? 'toggleTray' : 'toggleInspector';
  const hidden = $('workbench').classList.toggle(cls);
  $(button).setAttribute('aria-expanded', String(!hidden));
}
$('toggleTray').addEventListener('click', () => togglePanel('tray'));
$('toggleInspector').addEventListener('click', () => togglePanel('inspector'));
$('closeInspector').addEventListener('click', () => {
  $('workbench').classList.add('inspector-hidden');
  $('toggleInspector').setAttribute('aria-expanded', 'false');
  $('toggleInspector').focus();
});
$('focusMode').addEventListener('click', () => {
  state.focus = !state.focus;
  for (const cls of ['tray-hidden', 'inspector-hidden'])
    $('workbench').classList.toggle(cls, state.focus);
  $('focusMode').setAttribute('aria-pressed', String(state.focus));
  $('focusMode').textContent = state.focus ? '패널 복원' : '영상 넓게';
  $('toggleTray').setAttribute('aria-expanded', String(!state.focus));
  $('toggleInspector').setAttribute('aria-expanded', String(!state.focus));
});
$('failure').addEventListener('click', () =>
  loadSample(state.data.worst_delta_sample),
);
$('help').addEventListener('click', () => $('helpDialog').showModal());
$('closeHelp').addEventListener('click', () => $('helpDialog').close());
const narrow = matchMedia('(max-width:1199px)'),
  mobile = matchMedia('(max-width:760px)');
function responsive() {
  if (narrow.matches) {
    $('workbench').classList.add('inspector-hidden');
    $('toggleInspector').setAttribute('aria-expanded', 'false');
  }
  if (mobile.matches) {
    $('workbench').classList.add('tray-hidden');
    $('toggleTray').setAttribute('aria-expanded', 'false');
  }
}
responsive();
narrow.addEventListener('change', responsive);
mobile.addEventListener('change', responsive);
new ResizeObserver(() => {
  if (resizePending) return;
  resizePending = true;
  requestAnimationFrame(() => {
    resizePending = false;
    if (state.phase === 'ready') {
      if (state.fitMode) fit();
      else {
        clampView();
        draw();
        renderObjectOptions();
      }
    }
  });
}).observe($('stage'));
init();
