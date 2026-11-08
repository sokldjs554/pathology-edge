'use strict';
const WSI = {
  data: null,
  roi: null,
  mode: 'explore',
  viewers: {},
  pair: null,
  selected: null,
  boundary: null,
  syncing: false,
  frames: 0,
  tiles: { loaded: 0, failed: 0, levels: new Set() },
  failedOverlays: new Set(),
};
const $ = (id) => document.getElementById(id);
const number = (n) => Number(n).toLocaleString('en-US');
const text = (id, value) => {
  $(id).textContent = value;
};
const escape = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[
        c
      ],
  );
const row = (name, value) =>
  `<div class="trace-row"><span>${escape(name)}</span><span>${escape(value)}</span></div>`;
const rect = (box, color, extra = '') =>
  `<rect x="${box[0]}" y="${box[1]}" width="${box[2] - box[0]}" height="${box[3] - box[1]}" fill="none" stroke="${color}" stroke-width="1.5" vector-effect="non-scaling-stroke" ${extra}/>`;
const pointLabel = (x, y, value, color = '#fff') =>
  `<text x="${x}" y="${y}" fill="${color}" stroke="#263a42" paint-order="stroke" stroke-width="2" vector-effect="non-scaling-stroke" data-screen-label>${escape(value)}</text>`;

function layoutPanels() {
  $('toggleRegions').setAttribute(
    'aria-expanded',
    !$('workbench').classList.contains('regions-hidden'),
  );
  $('toggleResults').setAttribute(
    'aria-expanded',
    !$('workbench').classList.contains('results-hidden'),
  );
}
function showResults() {
  $('workbench').classList.remove('results-hidden');
  if (innerWidth <= 760) $('workbench').classList.add('regions-hidden');
  layoutPanels();
}
function ready() {
  document.body.dataset.phase = 'ready';
  $('stageMessage').hidden = true;
  text('status', '실제 WSI 타일 · 저장된 ROI 결과 · 새 모델 실행 없음');
  controls(false);
}
function controls(disabled) {
  for (const id of [
    'modeExplore',
    'modeCompare',
    'modeTrace',
    'zoomIn',
    'zoomOut',
    'home',
    'native',
    'slideOverview',
  ])
    $(id).disabled = disabled;
  document.querySelectorAll('.roi-item').forEach((b) => {
    b.disabled = disabled;
  });
}
function failure(message, metadata = false) {
  text('tileWarningText', message);
  $('tileWarning').hidden = false;
  if (metadata || !WSI.tiles.loaded) {
    document.body.dataset.phase = 'error';
    $('stageMessage').hidden = false;
    text(
      'stageTitle',
      metadata
        ? '분석 목록을 열지 못했습니다'
        : '슬라이드 타일을 열지 못했습니다',
    );
    text('stageDetail', message);
  }
  text('status', message);
}
function resizeViewers() {
  for (const [id, viewer] of Object.entries(WSI.viewers)) {
    const box = $('viewer' + id).getBoundingClientRect();
    if (box.width > 0 && box.height > 0 && viewer.viewport) {
      viewer.viewport.resize(
        new OpenSeadragon.Point(box.width, box.height),
        true,
      );
      viewer.forceRedraw();
    }
  }
}
function synchronize(source) {
  if (WSI.syncing || WSI.mode === 'explore' || !source.world.getItemCount())
    return;
  const target = source === WSI.viewers.A ? WSI.viewers.B : WSI.viewers.A;
  if (!target?.world.getItemCount()) return;
  const center = source.viewport.getCenter(true);
  const pixels = source.viewport.viewportToImageZoom(
    source.viewport.getZoom(true),
  );
  const zoom = target.viewport.imageToViewportZoom(pixels);
  WSI.syncing = true;
  if (Math.abs(target.viewport.getZoom(true) - zoom) > 1e-9)
    target.viewport.zoomTo(zoom, null, true);
  if (target.viewport.getCenter(true).distanceTo(center) > 1e-10)
    target.viewport.panTo(center, true);
  WSI.syncing = false;
}
function updateView(source = WSI.viewers.B) {
  if (!source?.world.getItemCount()) return;
  synchronize(source);
  if (WSI.frames) return;
  WSI.frames = requestAnimationFrame(() => {
    WSI.frames = 0;
    for (const [id, viewer] of Object.entries(WSI.viewers)) {
      if (!viewer.world.getItemCount() || !$('viewer' + id).clientWidth)
        continue;
      const v = viewer.viewport,
        bounds = v.viewportToImageRectangle(v.getBounds(true));
      const center = v.viewportToImageCoordinates(v.getCenter(true));
      const scale = v.viewportToImageZoom(v.getZoom(true));
      const svg = $('overlay' + id);
      svg.setAttribute(
        'viewBox',
        `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`,
      );
      svg.setAttribute('preserveAspectRatio', 'none');
      svg
        .querySelectorAll('[data-screen-label]')
        .forEach((label) => label.setAttribute('font-size', 11 / scale));
      $('viewer' + id).dataset.center =
        `${center.x.toFixed(4)},${center.y.toFixed(4)}`;
      $('viewer' + id).dataset.zoom = scale.toFixed(6);
      $('viewer' + id).dataset.bounds = [
        bounds.x,
        bounds.y,
        bounds.width,
        bounds.height,
      ].join(',');
      const targetUm = (80 * WSI.data.slide.mpp_x) / scale;
      const unit = 10 ** Math.floor(Math.log10(targetUm));
      const um =
        [1, 2, 5, 10]
          .map((n) => n * unit)
          .filter((n) => n <= targetUm)
          .pop() || unit;
      text(
        'scale' + id,
        um >= 1000 ? `${um / 1000} mm` : `${Number(um.toPrecision(3))} µm`,
      );
      $('scaleBar' + id).style.width =
        `${(um / WSI.data.slide.mpp_x) * scale}px`;
      if (id === 'B') {
        text('zoomReadout', `${Math.round(scale * 100)}%`);
        text(
          'position',
          `level-0 중심 x ${Math.round(center.x)} · y ${Math.round(center.y)}`,
        );
        const roi = WSI.data.rois.find(
          (r) =>
            center.x >= r.origin[0] &&
            center.x < r.origin[0] + r.width &&
            center.y >= r.origin[1] &&
            center.y < r.origin[1] + r.height,
        );
        text(
          'centerCoverage',
          roi ? `현재 중심: ${roi.id} 분석 범위` : '현재 중심: 미분석',
        );
      }
    }
  });
}
function setMode(mode) {
  if (!WSI.data) return;
  if (mode !== 'explore' && !WSI.roi) {
    selectROI(WSI.data.rois[0].id, mode);
    return;
  }
  if (mode !== WSI.mode) {
    WSI.pair = null;
    WSI.selected = null;
  }
  WSI.mode = mode;
  $('panes').classList.toggle('explore', mode === 'explore');
  for (const [id, key] of [
    ['modeExplore', 'explore'],
    ['modeCompare', 'compare'],
    ['modeTrace', 'trace'],
  ])
    $(id).setAttribute('aria-pressed', mode === key);
  text('titleA', mode === 'trace' ? '병합 전 · 원시 후보' : '겹침 없이 처리');
  text(
    'titleB',
    mode === 'explore'
      ? 'CMU-1 실제 스캔'
      : mode === 'trace'
        ? '병합 후 · 유지 후보'
        : '겹쳐 처리 + 확률 병합',
  );
  text(
    'metaA',
    mode === 'trace'
      ? '동일 overlap 출력의 후보 분기'
      : '128px 패치 / stride 128',
  );
  text(
    'metaB',
    mode === 'explore'
      ? '분석된 ROI만 예측 표시'
      : mode === 'trace'
        ? 'NMS · 픽셀 마스크는 동일'
        : '128px 패치 / stride 64 · Hann',
  );
  text('mobileA', mode === 'trace' ? 'A 병합 전' : 'A 무겹침');
  text('mobileB', mode === 'trace' ? 'B 병합 후' : 'B 겹침');
  text(
    'viewContext',
    mode === 'explore'
      ? '전체 스캔 탐색 · ROI 밖에는 예측 없음'
      : mode === 'trace'
        ? '같은 겹침 결과 · 원시 후보 → NMS 유지 후보'
        : '동일 원본 위치 · A 무겹침 / B 겹침 + Hann 병합',
  );
  if (mode === 'trace') {
    $('showCandidates').checked = true;
    WSI.boundary = null;
  }
  $('differenceDetail').hidden = !WSI.boundary;
  $('traceDetail').hidden = mode !== 'trace' && !WSI.selected;
  renderOverlays();
  requestAnimationFrame(() => {
    resizeViewers();
    synchronize(WSI.viewers.B);
    updateView();
  });
}
function fit(box, margin = 0) {
  requestAnimationFrame(() => {
    resizeViewers();
    const v = WSI.viewers.B.viewport;
    v.fitBounds(
      v.imageToViewportRectangle(
        box[0] - margin,
        box[1] - margin,
        box[2] - box[0] + margin * 2,
        box[3] - box[1] + margin * 2,
      ),
      true,
    );
    synchronize(WSI.viewers.B);
    updateView();
  });
}
function selectROI(id, mode = 'compare') {
  const roi = WSI.data.rois.find((r) => r.id === id);
  if (!roi) return;
  WSI.roi = roi;
  WSI.pair = null;
  WSI.selected = null;
  WSI.boundary = null;
  $('jumpDifference').disabled = !roi.difference.cases.length;
  document
    .querySelectorAll('.roi-item')
    .forEach((el) => el.setAttribute('aria-current', el.dataset.roi === id));
  text('activeRegion', `${id} · 분석한 관심 영역`);
  text(
    'regionDescription',
    '같은 native 1024×1024 입력에 두 패치 방식을 실행했습니다. 아래 수치는 이 ROI 전체 기준이며 현재 시야의 점수가 아닙니다.',
  );
  text(
    'regionCoordinates',
    `level-0 x ${roi.origin[0]}–${roi.origin[0] + roi.width} · y ${roi.origin[1]}–${roi.origin[1] + roi.height}`,
  );
  const a = roi.methods.no_overlap,
    b = roi.methods.overlap;
  $('roiMetrics').innerHTML = [
    [
      'warm 중앙값 (s)',
      a.median_seconds.toFixed(3),
      b.median_seconds.toFixed(3),
    ],
    [
      'worker peak MiB',
      a.peak_process_rss_mib.toFixed(1),
      b.peak_process_rss_mib.toFixed(1),
    ],
    ['패치 수', a.patch_count, b.patch_count],
    ['원시 후보', a.raw_count, b.raw_count],
    ['NMS 유지 후보', a.merged_count, b.merged_count],
    ['억제 후보', a.suppressed_count, b.suppressed_count],
  ]
    .map(
      ([label, av, bv]) =>
        `<tr><td>${label}</td><td>${av}</td><td>${bv}</td></tr>`,
    )
    .join('');
  text(
    'regionDifference',
    `ROI 전체 예측 변화 ${number(roi.difference.changed_pixels)}px. 공통 경계띠 ${number(roi.difference.boundary_pixels)}px 중 변화 ${number(roi.difference.boundary_changed_pixels)}px. GT 정확도 아님.`,
  );
  text(
    'timingScope',
    'CPU · torch 4 / OpenCV 1 thread. ROI×방식별 독립 프로세스, warmup 1회 후 3회 중앙값. patch·forward·stitch·component·NMS 포함, WSI 읽기·모델 로드·저장 제외. peak RSS는 읽기·모델·warmup·3회 실행을 포함한 프로세스 절대 최댓값입니다. OS 파일 캐시·공유 호스트 부하는 통제하지 않았습니다.',
  );
  $('regionResult').hidden = false;
  $('pairSelect').innerHTML =
    '<option value="">후보 쌍 선택</option>' +
    b.suppressed
      .map(
        (p, i) =>
          `<option value="${i}">#${p.suppressed_raw_index + 1} → #${p.kept_raw_index + 1} · patch ${p.suppressed_patch_id}/${p.kept_patch_id}</option>`,
      )
      .join('');
  $('candidateInfo').replaceChildren();
  setMode(mode);
  fit(
    [
      roi.origin[0],
      roi.origin[1],
      roi.origin[0] + roi.width,
      roi.origin[1] + roi.height,
    ],
    70,
  );
  if (innerWidth <= 760) {
    $('workbench').classList.add('regions-hidden');
    layoutPanels();
  }
}
function jumpDifference() {
  if (!WSI.roi) selectROI(WSI.data.rois[0].id);
  const c = WSI.roi.difference.cases[0];
  if (!c) return;
  WSI.pair = null;
  WSI.selected = null;
  WSI.boundary = c;
  $('showDifference').checked = true;
  setMode('compare');
  text(
    'differenceCoordinates',
    `${c.id} · level-0 [${c.bbox_level0.join(', ')}]`,
  );
  text(
    'differenceCounts',
    `선택 64×64 안에서 B 추가 ${c.added_pixels}px · B 제거 ${c.removed_pixels}px. 경계띠 내 변화 ${c.boundary_changed_pixels}px. 실제 128px 경계에 중심을 둔 창 중 경계 변화 수가 가장 큰 곳입니다.`,
  );
  $('differenceDetail').hidden = false;
  $('traceDetail').hidden = true;
  fit(c.bbox_level0, 96);
  if (innerWidth > 1199) showResults();
}
function pairInfo(pair) {
  const m = WSI.roi.methods.overlap;
  const removed = m.raw[pair.suppressed_raw_index],
    kept = m.raw[pair.kept_raw_index];
  const patch = (o) => m.patches.find((p) => p.id === o.patch_id);
  $('candidateInfo').innerHTML =
    `<p><b>분홍 #${removed.raw_index + 1} 억제 → 청록 #${kept.raw_index + 1} 유지</b></p>` +
    [
      row('원 패치 ID', `${removed.patch_id} → ${kept.patch_id}`),
      row('억제 패치 원점', patch(removed).origin_level0.join(', ')),
      row('유지 패치 원점', patch(kept).origin_level0.join(', ')),
      row('억제 후보 native 상자', removed.bbox_level0.join(', ')),
      row('유지 후보 native 상자', kept.bbox_level0.join(', ')),
      row(
        '박스 IoU / 임계값',
        `${pair.box_iou.toFixed(3)} / ${pair.iou_threshold}`,
      ),
      row(
        '중심 거리 / 임계값',
        `${pair.center_distance.toFixed(2)} / ${pair.distance_threshold}px`,
      ),
      row(
        '실제 억제 조건',
        [
          pair.iou_trigger ? 'IoU 충족' : '',
          pair.distance_trigger ? '거리 충족' : '',
        ]
          .filter(Boolean)
          .join(' + '),
      ),
      row(
        '경계에 닿음 (억제 / 유지)',
        `${removed.touches_edge ? '예' : '아니오'} / ${kept.touches_edge ? '예' : '아니오'}`,
      ),
      row(
        '평균 확률 (억제 / 유지)',
        `${removed.score.toFixed(3)} / ${kept.score.toFixed(3)}`,
      ),
    ].join('') +
    '<p>원 구현 우선순위: 패치 가장자리에 닿지 않은 후보 우선 → 평균 확률 내림차순. IoU 또는 중심 거리가 조건을 충족하면 억제합니다. 상자는 반열린 [x0,y0,x1,y1) 좌표입니다.</p>';
}
function selectPair(index) {
  if (!WSI.roi) selectROI(WSI.data.rois[0].id, 'trace');
  const p = WSI.roi.methods.overlap.suppressed[index];
  if (!p) return;
  setMode('trace');
  WSI.pair = p;
  WSI.selected = null;
  $('pairSelect').value = String(index);
  pairInfo(p);
  renderOverlays();
  const m = WSI.roi.methods.overlap,
    a = m.raw[p.suppressed_raw_index],
    b = m.raw[p.kept_raw_index];
  const x = (a.center_level0[0] + b.center_level0[0]) / 2,
    y = (a.center_level0[1] + b.center_level0[1]) / 2;
  fit([x - 150, y - 150, x + 150, y + 150]);
}
function selectCandidate(method, rawIndex) {
  const m = WSI.roi.methods[method],
    o = m.raw[rawIndex];
  const p =
    method === 'overlap' &&
    m.suppressed.find(
      (pair) =>
        pair.suppressed_raw_index === rawIndex ||
        pair.kept_raw_index === rawIndex,
    );
  if (p) {
    selectPair(m.suppressed.indexOf(p));
    return;
  }
  WSI.pair = null;
  WSI.boundary = null;
  WSI.selected = { method, object: o };
  $('pairSelect').value = '';
  const patch = m.patches.find((p) => p.id === o.patch_id);
  $('candidateInfo').innerHTML =
    `<p><b>${method === 'overlap' ? '겹침' : '무겹침'} raw #${rawIndex + 1}</b> · 이 후보의 실제 패치 출처</p>` +
    row('패치 ID', o.patch_id) +
    row('패치 native 원점', patch.origin_level0.join(', ')) +
    row('native 상자', o.bbox_level0.join(', ')) +
    row('평균 확률', o.score.toFixed(3)) +
    '<p>이 후보와 연결된 억제·유지 쌍은 저장 결과에 없습니다.</p>';
  $('traceDetail').hidden = false;
  $('differenceDetail').hidden = true;
  renderOverlays();
  showResults();
}
function renderOverlays() {
  if (!WSI.data) return;
  for (const id of ['A', 'B']) {
    const method =
      id === 'A' && WSI.mode !== 'trace' ? 'no_overlap' : 'overlap';
    let markup = '';
    for (const r of WSI.data.rois) {
      const [x, y] = r.origin,
        box = [x, y, x + r.width, y + r.height];
      if (
        $('showMask').checked &&
        !WSI.failedOverlays.has(r.methods[method].overlay)
      )
        markup += `<image data-mask="${r.id}-${method}" href="${r.methods[method].overlay}" x="${x}" y="${y}" width="${r.width}" height="${r.height}" opacity="${Number($('overlayOpacity').value) / 100}"/>`;
      if (
        $('showDifference').checked &&
        r === WSI.roi &&
        WSI.mode !== 'trace' &&
        !WSI.failedOverlays.has(r.difference.overlay)
      )
        markup += `<image data-difference="${r.id}" href="${r.difference.overlay}" x="${x}" y="${y}" width="${r.width}" height="${r.height}"/>`;
      if ($('showBounds').checked)
        markup +=
          rect(box, '#42b9d7', `class="hit" data-roi="${r.id}"`) +
          pointLabel(x, y - 12, `${r.id} · 분석 ROI`, '#bcefff');
    }
    const r = WSI.roi;
    if (r) {
      const [x, y] = r.origin,
        m = r.methods[method];
      if ($('showGrid').checked) {
        for (let n = 128; n < 1024; n += 128)
          markup += `<path data-grid d="M${x + n} ${y}v1024 M${x} ${y + n}h1024" fill="none" stroke="#ffcd59" stroke-opacity=".7" stroke-width="1" stroke-dasharray="4 4" vector-effect="non-scaling-stroke"/>`;
      }
      if ($('showCandidates').checked) {
        const candidates =
          WSI.mode === 'trace' && id === 'A' ? m.raw : m.objects;
        markup += candidates
          .map((o) =>
            rect(
              o.bbox_level0,
              '#2cd5d0',
              `class="hit" data-candidate="${o.raw_index}" data-method="${method}"`,
            ),
          )
          .join('');
      }
      if (WSI.boundary)
        markup +=
          rect(
            WSI.boundary.bbox_level0,
            'white',
            'data-boundary stroke-dasharray="5 3"',
          ) +
          pointLabel(
            WSI.boundary.bbox_level0[0],
            WSI.boundary.bbox_level0[1] - 8,
            '동일 경계 64px',
          );
      const selected = WSI.pair
        ? [
            {
              object: r.methods.overlap.raw[WSI.pair.suppressed_raw_index],
              method: 'overlap',
              color: '#ff72bf',
              kept: false,
            },
            {
              object: r.methods.overlap.raw[WSI.pair.kept_raw_index],
              method: 'overlap',
              color: '#53ffff',
              kept: true,
            },
          ]
        : WSI.selected && WSI.selected.method === method
          ? [{ ...WSI.selected, color: '#53ffff', kept: true }]
          : [];
      for (const s of selected) {
        const o = s.object,
          patch = r.methods[s.method].patches.find((p) => p.id === o.patch_id);
        markup +=
          rect(
            patch.bbox_level0,
            s.color,
            `data-patch="${patch.id}" stroke-dasharray="7 4"`,
          ) +
          pointLabel(
            patch.origin_level0[0] + 2,
            patch.origin_level0[1] + 12,
            `patch ${patch.id}`,
            s.color,
          );
        if (id === 'A' || s.kept || WSI.mode !== 'trace')
          markup +=
            rect(o.bbox_level0, s.color, `data-selected="${o.raw_index}"`) +
            pointLabel(
              o.bbox_level0[2] + 3,
              o.bbox_level0[1],
              `#${o.raw_index + 1}`,
              s.color,
            );
      }
      if (WSI.pair && id === 'A') {
        const [a, b] = selected.map((s) => s.object.center_level0);
        markup += `<path data-pair-line d="M${a[0]} ${a[1]}L${b[0]} ${b[1]}" stroke="white" stroke-width="2" vector-effect="non-scaling-stroke"/>`;
      }
    }
    $('overlay' + id).innerHTML = markup;
  }
  updateView();
}
function setupViewer(id) {
  const viewer = OpenSeadragon({
    id: 'viewer' + id,
    tileSources: WSI.data.slide.tile_source,
    drawer: 'canvas',
    showNavigationControl: false,
    showNavigator: id === 'B',
    navigatorPosition: 'BOTTOM_RIGHT',
    navigatorWidth: 120,
    navigatorHeight: 88,
    navigatorAutoFade: false,
    navigatorBorderColor: '#80969e',
    navigatorDisplayRegionColor: '#23b6ca',
    crossOriginPolicy: 'Anonymous',
    ajaxWithCredentials: false,
    gestureSettingsMouse: {
      scrollToZoom: false,
      clickToZoom: false,
      dblClickToZoom: true,
    },
    gestureSettingsTouch: { pinchToZoom: true, clickToZoom: false },
    animationTime: 0,
    blendTime: 0,
    maxZoomPixelRatio: 4,
    visibilityRatio: 0.8,
  });
  WSI.viewers[id] = viewer;
  viewer.addHandler('open', () => {
    if (id === 'B') viewer.viewport.goHome(true);
    updateView(viewer);
  });
  viewer.addHandler('viewport-change', () => updateView(viewer));
  viewer.addHandler('resize', () => updateView(viewer));
  viewer.addHandler('tile-loaded', (e) => {
    WSI.tiles.loaded++;
    WSI.tiles.levels.add(e.tile.level);
    if (id === 'B' && document.body.dataset.phase !== 'ready') ready();
  });
  viewer.addHandler('tile-load-failed', () => {
    WSI.tiles.failed++;
    failure(
      '일부 상세 타일을 불러오지 못했습니다. 외부 OpenSlide 서버·연결 상태를 확인하고 다시 시도하세요.',
    );
  });
  viewer.addHandler('open-failed', (e) =>
    failure(`슬라이드를 열지 못했습니다: ${e.message}`),
  );
  $('viewer' + id).addEventListener(
    'wheel',
    (e) => {
      if (!viewer.world.getItemCount()) return;
      e.preventDefault();
      e.stopPropagation();
      const v = viewer.viewport,
        r = $('viewer' + id).getBoundingClientRect();
      const factor = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? r.height : 1;
      if (e.ctrlKey || e.metaKey)
        v.zoomBy(
          Math.exp(-e.deltaY * factor * 0.002),
          v.pointFromPixel(
            new OpenSeadragon.Point(e.clientX - r.left, e.clientY - r.top),
          ),
          true,
        );
      else
        v.panBy(
          v.deltaPointsFromPixels(
            new OpenSeadragon.Point(e.deltaX * factor, e.deltaY * factor),
            true,
          ),
          true,
        );
      v.applyConstraints(true);
      updateView(viewer);
    },
    { capture: true, passive: false, signal: WSI.events.signal },
  );
  $('viewer' + id).addEventListener(
    'keydown',
    (e) => {
      if (!viewer.world.getItemCount()) return;
      const v = viewer.viewport;
      const direction = {
        ArrowLeft: [-60, 0],
        ArrowRight: [60, 0],
        ArrowUp: [0, -60],
        ArrowDown: [0, 60],
      }[e.key];
      if (direction) {
        e.preventDefault();
        e.stopPropagation();
        v.panBy(
          v.deltaPointsFromPixels(new OpenSeadragon.Point(...direction), true),
          true,
        );
        v.applyConstraints(true);
      } else if (['+', '=', '-'].includes(e.key)) {
        e.preventDefault();
        v.zoomBy(e.key === '-' ? 0.8 : 1.25, null, true);
      } else if (e.key.toLowerCase() === 'f') {
        e.preventDefault();
        home();
      }
      updateView(viewer);
    },
    { capture: true, signal: WSI.events.signal },
  );
  $('overlay' + id).addEventListener(
    'click',
    (e) => {
      const roi = e.target.closest('[data-roi]');
      const candidate = e.target.closest('[data-candidate]');
      if (roi) selectROI(roi.dataset.roi);
      else if (candidate && WSI.roi)
        selectCandidate(
          candidate.dataset.method,
          Number(candidate.dataset.candidate),
        );
    },
    { signal: WSI.events.signal },
  );
}
function home() {
  WSI.viewers.B?.viewport.goHome(true);
  synchronize(WSI.viewers.B);
  updateView();
}
async function init() {
  WSI.events?.abort();
  WSI.events = new AbortController();
  if (WSI.frames) cancelAnimationFrame(WSI.frames);
  WSI.frames = 0;
  controls(true);
  for (const viewer of Object.values(WSI.viewers)) viewer.destroy();
  WSI.viewers = {};
  WSI.data = null;
  WSI.roi = null;
  WSI.pair = null;
  WSI.selected = null;
  WSI.boundary = null;
  WSI.mode = 'explore';
  $('panes').classList.add('explore');
  for (const id of ['regionResult', 'traceDetail', 'differenceDetail'])
    $(id).hidden = true;
  $('roiList').replaceChildren();
  $('jumpDifference').disabled = true;
  text('activeRegion', '스캔 전체 탐색');
  WSI.tiles = { loaded: 0, failed: 0, levels: new Set() };
  WSI.failedOverlays.clear();
  document.body.dataset.phase = 'loading';
  $('stageMessage').hidden = false;
  $('tileWarning').hidden = true;
  try {
    const response = await fetch('wsi.json', {
      signal: AbortSignal.timeout(20000),
    });
    if (!response.ok) throw new Error(`결과 목록 HTTP ${response.status}`);
    WSI.data = await response.json();
    if (!WSI.data.slide?.tile_source || !Array.isArray(WSI.data.rois))
      throw new Error('WSI 분석 목록 형식이 올바르지 않습니다.');
    if (!WSI.data.rois.length) {
      document.body.dataset.phase = 'empty';
      text('stageTitle', '표시할 분석 ROI가 없습니다');
      text(
        'stageDetail',
        '저장된 분석 영역이 없습니다. 새 추론을 실행하지 않습니다.',
      );
      text('status', '분석 ROI 0개');
      return;
    }
    const s = WSI.data.slide;
    text('slideName', s.name);
    text(
      'slideMeta',
      `${number(s.width)} × ${number(s.height)} · ${s.mpp_x} µm/px · 원본 ${s.objective_power}× objective`,
    );
    $('slideThumb').src = s.thumbnail;
    text(
      'coverageSummary',
      `분석: ${WSI.data.rois.length}개 ROI · 원본 파일 픽셀의 ${(WSI.data.analysis.slide_fraction * 100).toFixed(4)}%. 조직 전체 분석 아님.`,
    );
    $('roiList').innerHTML = WSI.data.rois
      .map(
        (r) =>
          `<button class="roi-item" data-roi="${r.id}" aria-current="false"><img src="${r.thumbnail}" alt="${r.id} 조직 썸네일"><span><strong>${r.id}</strong>1024 × 1024 native<br>저장된 두 방식</span></button>`,
      )
      .join('');
    controls(true);
    $('roiList').onclick = (e) => {
      const b = e.target.closest('[data-roi]');
      if (b) selectROI(b.dataset.roi);
    };
    $('provenance').innerHTML =
      `<p>원본 <a href="${s.source_url}" target="_blank" rel="noreferrer">${escape(s.name)} ↗</a><br>${escape(s.credit)} · <a href="${s.license_url}" target="_blank" rel="noreferrer">${escape(s.license)}</a></p><p>원본 SHA-256</p><div class="hash">${s.source_sha256}</div><p>고정 TinyUNet · TNBC H&E 학습 · threshold 0.5</p><div class="hash">${WSI.data.model.sha256}</div><p>서버 타일은 같은 JP2K 원본에서 생성한 JPEG Q75입니다. 분석은 다운로드한 원본의 native RGB에서 수행했습니다. 뷰어 타일과 손실압축 없는 ROI PNG는 픽셀값이 완전히 같지 않습니다.</p><a href="wsi/provenance.json">실행·출처 기록 ↗</a>`;
    await Promise.all(
      WSI.data.rois
        .flatMap((r) => [
          r.methods.no_overlap.overlay,
          r.methods.overlap.overlay,
          r.difference.overlay,
        ])
        .map(async (path) => {
          const image = new Image();
          image.src = path;
          try {
            await image.decode();
          } catch {
            WSI.failedOverlays.add(path);
          }
        }),
    );
    setupViewer('A');
    setupViewer('B');
    renderOverlays();
    if (WSI.failedOverlays.size) {
      text(
        'tileWarningText',
        '일부 예측 오버레이 파일을 불러오지 못했습니다. 표시 누락은 핵 예측이 없다는 뜻이 아닙니다. 다시 불러오세요.',
      );
      $('tileWarning').hidden = false;
    }
  } catch (error) {
    failure(
      error.name === 'TimeoutError'
        ? '분석 목록 응답 시간이 초과되었습니다.'
        : error.message,
      true,
    );
  }
}
if (innerWidth <= 1199) $('workbench').classList.add('results-hidden');
if (innerWidth <= 760) $('workbench').classList.add('regions-hidden');
layoutPanels();
for (const [id, mode] of [
  ['modeExplore', 'explore'],
  ['modeCompare', 'compare'],
  ['modeTrace', 'trace'],
])
  $(id).onclick = () => {
    setMode(mode);
    if (mode === 'trace') selectPair(0);
  };
for (const id of [
  'showBounds',
  'showMask',
  'showGrid',
  'showCandidates',
  'showDifference',
  'overlayOpacity',
])
  $(id).addEventListener('input', renderOverlays);
$('jumpDifference').onclick = jumpDifference;
$('traceFirst').onclick = () => selectPair(0);
$('pairSelect').onchange = (e) => {
  if (e.target.value !== '') selectPair(Number(e.target.value));
};
$('zoomIn').onclick = () => {
  WSI.viewers.B?.viewport.zoomBy(1.25, null, true);
  updateView();
};
$('zoomOut').onclick = () => {
  WSI.viewers.B?.viewport.zoomBy(0.8, null, true);
  updateView();
};
$('native').onclick = () => {
  const v = WSI.viewers.B?.viewport;
  if (v) v.zoomTo(v.imageToViewportZoom(1), null, true);
  updateView();
};
$('home').onclick = home;
$('slideOverview').onclick = () => {
  setMode('explore');
  requestAnimationFrame(home);
};
for (const [id, cls] of [
  ['toggleRegions', 'regions-hidden'],
  ['toggleResults', 'results-hidden'],
])
  $(id).onclick = () => {
    $('workbench').classList.toggle(cls);
    layoutPanels();
    requestAnimationFrame(() => {
      resizeViewers();
      updateView();
    });
  };
$('closeResults').onclick = () => {
  $('workbench').classList.add('results-hidden');
  layoutPanels();
  requestAnimationFrame(() => {
    resizeViewers();
    updateView();
  });
};
for (const id of ['A', 'B'])
  $('mobile' + id).onclick = () => {
    $('panes').classList.toggle('show-a', id === 'A');
    $('mobileA').setAttribute('aria-pressed', id === 'A');
    $('mobileB').setAttribute('aria-pressed', id === 'B');
  };
$('help').onclick = () => $('helpDialog').showModal();
$('closeHelp').onclick = () => $('helpDialog').close();
$('retryTiles').onclick = () => {
  if (!WSI.viewers.B?.viewport || WSI.failedOverlays.size) {
    init();
    return;
  }
  const box = WSI.viewers.B.viewport.viewportToImageRectangle(
    WSI.viewers.B.viewport.getBounds(true),
  );
  WSI.tiles.loaded = 0;
  WSI.tiles.failed = 0;
  $('tileWarning').hidden = true;
  for (const v of Object.values(WSI.viewers)) {
    v.addOnceHandler('open', () =>
      fit([box.x, box.y, box.x + box.width, box.y + box.height]),
    );
    v.open(WSI.data.slide.tile_source);
  }
};
init();
