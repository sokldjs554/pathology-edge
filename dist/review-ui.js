'use strict';
// Post-hoc review of saved masks. No model execution or new experiment scores.
const Review = {
  data: null,
  selected: null,
  layer: null,
  intent: 0,
  signed(value, digits = 3) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
  },
  async load(source, sourceText) {
    this.data = null;
    try {
      const response = await fetch('cases.json', {
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const bytes = await crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(sourceText),
      );
      const hash = [...new Uint8Array(bytes)]
        .map((v) => v.toString(16).padStart(2, '0'))
        .join('');
      if (
        data.schema_version !== 1 ||
        data.source_sha256?.['results.json'] !== hash ||
        data.model_sha256 !== source.model_sha256 ||
        !Array.isArray(data.cases) ||
        !data.recommended
      )
        throw new Error('실험 결과와 사례 파일의 출처가 다릅니다');
      const ids = new Set();
      for (const c of data.cases) {
        if (
          ids.has(c.id) ||
          !source.samples.some((s) => s.id === c.sample_id) ||
          !['improved', 'worsened'].includes(c.direction) ||
          !Array.isArray(c.bbox) ||
          c.bbox.length !== 4 ||
          !c.bbox.every(Number.isInteger) ||
          c.bbox[2] - c.bbox[0] !== 64 ||
          c.bbox[3] - c.bbox[1] !== 64 ||
          Math.min(c.bbox[0], c.bbox[1]) < 32 ||
          Math.max(c.bbox[2], c.bbox[3]) > 480 ||
          !Array.isArray(c.center) ||
          c.center[0] !== c.bbox[0] + 32 ||
          c.center[1] !== c.bbox[1] + 32
        )
          throw new Error('사례 좌표 또는 예제 정보가 올바르지 않습니다');
        ids.add(c.id);
      }
      this.data = data;
      $('caseSelect').replaceChildren(
        ...data.cases.map(
          (c) =>
            new Option(
              `${c.sample_id} · 국소 ${c.direction === 'improved' ? '개선' : '악화'}`,
              c.id,
            ),
        ),
      );
      $('caseLoadNotice').textContent =
        '정답과 대조한 저장 사례를 사용할 수 있습니다.';
      $('caseLoadNotice').className = 'sr-only';
    } catch (error) {
      this.notice(
        `경계 사례를 열 수 없습니다: ${error.message}. 기존 영상 비교는 사용할 수 있습니다. 페이지를 새로고침해 재시도하세요.`,
      );
    }
    this.refresh();
  },
  notice(text) {
    $('caseLoadNotice').textContent = text;
    $('caseLoadNotice').className = '';
  },
  refresh() {
    const ready = state.phase === 'ready';
    for (const [id, direction] of [
      ['showImproved', 'improved'],
      ['showWorsened', 'worsened'],
    ])
      $(id).disabled = !ready || !this.data?.recommended[direction];
    $('jumpBoundary').disabled =
      !ready || !this.data?.cases.some((c) => c.sample_id === state.sample?.id);
    $('caseSelect').disabled = !ready;
  },
  clear() {
    if (this.selected)
      $('modeDescription').textContent =
        '같은 모델 · 무겹침과 64px 겹침을 같은 시야에서 비교';
    this.selected = this.layer = null;
    $('caseDetail').hidden = true;
    for (const canvas of canvases) delete canvas.dataset.case;
  },
  current() {
    const candidates =
      this.data?.cases.filter((c) => c.sample_id === state.sample?.id) || [];
    // Largest absolute net change in this image, without hiding regressions.
    return candidates.sort(
      (a, b) => Math.abs(b.net_corrected) - Math.abs(a.net_corrected),
    )[0];
  },
  evidenceLayer(c) {
    const [x, y] = c.bbox;
    const read = (image) =>
      image.getContext('2d').getImageData(x, y, 64, 64).data;
    const a = read(state.images.no_overlap),
      b = read(state.images.overlap),
      t = read(state.images.truth);
    const corrected = new Uint8Array(4096),
      regressed = new Uint8Array(4096);
    const stats = [
      { tp: 0, fp: 0, fn: 0 },
      { tp: 0, fp: 0, fn: 0 },
    ];
    for (let i = 0; i < 4096; i++) {
      const px = x + (i % 64),
        py = y + Math.floor(i / 64);
      const inBand = [128, 256, 384].some(
        (k) => (px >= k - 8 && px < k + 8) || (py >= k - 8 && py < k + 8),
      );
      if (!inBand) continue;
      const av = a[i * 4 + 3] > 0,
        bv = b[i * 4 + 3] > 0,
        tv = t[i * 4 + 3] > 0;
      corrected[i] = Number(av !== tv && bv === tv);
      regressed[i] = Number(av === tv && bv !== tv);
      [av, bv].forEach((p, j) => {
        stats[j].tp += Number(p && tv);
        stats[j].fp += Number(p && !tv);
        stats[j].fn += Number(!p && tv);
      });
    }
    for (const [name, expected] of [
      ['corrected', corrected],
      ['regressed', regressed],
    ]) {
      const decoded = new Uint8Array(4096);
      for (const run of c[name + '_runs']) {
        const [ry, rx, length] = run;
        if (
          !run.every(Number.isInteger) ||
          ry < 0 ||
          ry >= 64 ||
          rx < 0 ||
          length < 1 ||
          rx + length > 64
        )
          throw new Error('강조 픽셀 좌표가 올바르지 않습니다');
        for (let j = 0; j < length; j++) decoded[ry * 64 + rx + j]++;
      }
      if (
        !decoded.every((v, i) => v === expected[i]) ||
        expected.reduce((a, b) => a + b, 0) !== c[name]
      )
        throw new Error('강조 영역이 실제 저장 마스크와 일치하지 않습니다');
    }
    stats.forEach((s, j) => {
      const denominator = 2 * s.tp + s.fp + s.fn;
      if (
        Math.abs(
          (denominator ? (2 * s.tp) / denominator : 1) -
            c[j ? 'after' : 'before'].dice,
        ) > 1e-12
      )
        throw new Error('선택 영역 점수가 저장 마스크와 일치하지 않습니다');
    });
    const layer = document.createElement('canvas');
    layer.width = layer.height = 64;
    const ctx = layer.getContext('2d'),
      pixels = ctx.createImageData(64, 64);
    for (let i = 0; i < 4096; i++) {
      if (corrected[i]) pixels.data.set([34, 211, 172, 185], i * 4);
      if (regressed[i]) pixels.data.set([255, 69, 131, 185], i * 4);
    }
    ctx.putImageData(pixels, 0, 0);
    return layer;
  },
  async open(id) {
    const c = this.data?.cases.find((c) => c.id === id);
    if (!c) return;
    const intent = ++this.intent;
    let request = state.request;
    if (state.sample?.id !== c.sample_id) {
      const loading = loadSample(c.sample_id);
      request = state.request;
      await loading;
    }
    // Let loadSample's fit render first, then apply the requested review viewport.
    await new Promise(requestAnimationFrame);
    if (
      intent !== this.intent ||
      request !== state.request ||
      state.phase !== 'ready' ||
      state.sample?.id !== c.sample_id
    )
      return;
    try {
      const layer = this.evidenceLayer(c);
      setMode('boundary');
      setScope('all');
      $('objects').checked = false;
      $('grid').checked = true;
      $('caseHighlight').checked = true;
      this.selected = c;
      this.layer = layer;
      $('caseDetail').hidden = false;
      $('caseSelect').value = c.id;
      $('caseCoordinates').textContent =
        `동일 PNG 좌표 x ${c.bbox[0]}–${c.bbox[2]}, y ${c.bbox[1]}–${c.bbox[3]} (끝 좌표 제외)`;
      $('caseScores').textContent =
        `국소 경계 Dice ${fmt(c.before.dice)} → ${fmt(c.after.dice)} (Δ ${this.signed(c.after.dice - c.before.dice)})`;
      $('caseCounts').replaceChildren(
        node('span', `정답 일치로 변경 ${c.corrected}px`, 'corrected'),
        node('br'),
        node('span', `불일치로 변경 ${c.regressed}px`, 'regressed'),
      );
      const methods = state.sample.methods;
      const imageDelta =
        methods.overlap.metrics.all.dice - methods.no_overlap.metrics.all.dice;
      $('caseImageContext').textContent =
        `이 상자 안 경계 띠만의 점수입니다. ${c.sample_id} 이미지 전체 Dice 차이는 ${this.signed(imageDelta)}로, 국소 사례와 방향이 다를 수 있습니다. 아래 이미지 지표는 확대해도 바뀌지 않습니다.`;
      $('modeDescription').textContent =
        `${c.sample_id} · 국소 ${c.direction === 'improved' ? '개선' : '악화'} · 흰 상자 = 동일 영역 · 청록 개선 / 분홍 악화`;
      // Do not cover the only canvas with the floating inspector on small screens.
      if (innerWidth >= 1200) setTab('image');
      else setTab('image', false);
      state.fitMode = false;
      state.cx = c.center[0];
      state.cy = c.center[1];
      const views = visibleCanvases().map(dimensions);
      state.zoom = Math.min(
        6,
        ...views.map((v) => Math.min(v.width, v.height) / 108),
      );
      clampView();
      draw();
      renderObjectOptions();
      $('status').textContent =
        `${c.sample_id} · 선택 경계 ${c.center.join(', ')}px · 사후 선택 사례 · 상세는 결과 패널`;
    } catch (error) {
      this.clear();
      this.notice(
        `사례 표시 중단: ${error.message}. 기존 이미지 지표를 확인하세요.`,
      );
      draw();
    }
  },
  draw(ctx, canvas) {
    const c = this.selected;
    if (!c || state.mode !== 'boundary') return;
    canvas.dataset.case = c.id;
    const [x, y, x1, y1] = c.bbox;
    if ($('caseHighlight').checked) {
      ctx.save();
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(this.layer, x, y);
      ctx.restore();
    }
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.6 / state.zoom;
    ctx.setLineDash([]);
    ctx.strokeRect(x, y, x1 - x, y1 - y);
    const size = 11 / state.zoom;
    ctx.font = `${size}px Arial`;
    ctx.fillStyle = '#15242bd9';
    ctx.fillRect(x, y - 18 / state.zoom, 110 / state.zoom, 17 / state.zoom);
    ctx.fillStyle = '#fff';
    ctx.fillText(
      `ROI ${c.center.join(',')}`,
      x + 3 / state.zoom,
      y - 5 / state.zoom,
    );
  },
  summary(data) {
    const a = data.summary.no_overlap,
      b = data.summary.overlap;
    const ratio = b.median_image_seconds / a.median_image_seconds;
    $('performanceRows').replaceChildren();
    for (const [key, label] of [
      ['all', '전체 Dice'],
      ['boundary', '경계 Dice'],
      ['interior', '내부 Dice'],
    ]) {
      const delta = b.macro_dice[key] - a.macro_dice[key];
      const tr = node('tr');
      tr.append(
        node('td', label),
        node('td', fmt(a.macro_dice[key])),
        node('td', fmt(b.macro_dice[key])),
        node('td', this.signed(delta), delta < 0 ? 'negative' : 'positive'),
      );
      tr.title = `반올림 전 A ${a.macro_dice[key]} / B ${b.macro_dice[key]} / Δ ${delta}`;
      $('performanceRows').append(tr);
    }
    const tr = node('tr');
    tr.append(
      node('td', '시간 중앙값'),
      node('td', ms(a.median_image_seconds)),
      node('td', ms(b.median_image_seconds)),
      node('td', `${ratio.toFixed(2)}배`),
    );
    $('performanceRows').append(tr);
    $('costSummary').textContent =
      `경계 Dice ${this.signed(b.macro_dice.boundary - a.macro_dice.boundary, 6)} / 전체 ${this.signed(b.macro_dice.all - a.macro_dice.all, 6)}. 처리 시간은 ${ratio.toFixed(2)}배, 내부 Dice는 소폭 감소했습니다.`;
    $('perImageRows').replaceChildren();
    let improved = 0,
      worsened = 0;
    for (const s of data.samples) {
      const a = s.methods.no_overlap,
        b = s.methods.overlap;
      const all = b.metrics.all.dice - a.metrics.all.dice,
        boundary = b.metrics.boundary.dice - a.metrics.boundary.dice;
      if (all > 0) improved++;
      else if (all < 0) worsened++;
      const tr = node('tr'),
        td = node('td'),
        button = node('button', s.id);
      button.setAttribute('aria-label', `${s.id} 이미지와 경계 사례 열기`);
      button.addEventListener('click', async () => {
        const c = this.data?.cases.find(
          (c) =>
            c.sample_id === s.id &&
            c.direction === (all < 0 ? 'worsened' : 'improved'),
        );
        if (c) await this.open(c.id);
        else await loadSample(s.id);
        setTab('image', false);
        if (innerWidth < 1200) {
          $('workbench').classList.add('inspector-hidden');
          $('toggleInspector').setAttribute('aria-expanded', 'false');
        }
      });
      td.append(button);
      tr.append(
        td,
        node('td', this.signed(all), all < 0 ? 'negative' : 'positive'),
        node(
          'td',
          this.signed(boundary),
          boundary < 0 ? 'negative' : 'positive',
        ),
        node(
          'td',
          `${(a.median_seconds * 1000).toFixed(0)}/${(b.median_seconds * 1000).toFixed(0)}`,
        ),
      );
      tr.title = `${s.id}: A ${ms(a.median_seconds)} / B ${ms(b.median_seconds)}. Δ 전체 ${all}, 경계 ${boundary}`;
      $('perImageRows').append(tr);
    }
    $('imageDirectionSummary').textContent =
      `전체 Dice 증가 ${improved}개 / 감소 ${worsened}개. 10_1도 전체·경계 모두 감소합니다. 예제 번호로 실제 영역을 여세요.`;
  },
  bind() {
    $('showImproved').addEventListener('click', () =>
      this.open(this.data?.recommended.improved),
    );
    $('showWorsened').addEventListener('click', () =>
      this.open(this.data?.recommended.worsened),
    );
    $('caseSelect').addEventListener('change', (e) =>
      this.open(e.target.value),
    );
    $('caseHighlight').addEventListener('change', draw);
    $('showResults').addEventListener('click', () => setTab('experiment'));
    document
      .querySelectorAll('[data-terms]')
      .forEach((el) =>
        el.addEventListener('click', () => $('termsDialog').showModal()),
      );
    $('closeTerms').addEventListener('click', () => $('termsDialog').close());
  },
};
