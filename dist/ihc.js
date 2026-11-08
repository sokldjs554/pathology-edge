(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const shortNames = ['종양 +', '종양 −', '비종양 +', '비종양 −'];
  const number = (value) => Number(value).toLocaleString('en-US');
  const fixed = (value, digits = 3) => Number(value).toFixed(digits);
  const percent = (value) => `${(Number(value) * 100).toFixed(1)}%`;
  const text = (id, value) => {
    $(id).textContent = value;
  };
  const element = (tag, content, className) => {
    const node = document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (className) node.className = className;
    return node;
  };
  let data = null;
  let selected = null;
  let kind = 'incorrect';
  let generation = 0;
  let fetchController = null;
  let failureKind = null;

  function validate(payload) {
    const fail = (message) => {
      throw new Error(`결과 자료 검증 실패: ${message}`);
    };
    const finite = (value) =>
      typeof value === 'number' && Number.isFinite(value);
    if (
      payload?.schema_version !== 'pathology-edge.ihc.v1' ||
      payload.task !== 'gt_center_cell_classification'
    )
      fail('지원하지 않는 실험 형식');
    if (
      payload.scope?.provided_centers !== true ||
      payload.scope.detection_evaluated !== false ||
      payload.scope.segmentation_evaluated !== false ||
      payload.scope.clinical_assay !== false
    )
      fail('실험 범위가 다릅니다');
    if (
      !Array.isArray(payload.classes) ||
      payload.classes.length !== 4 ||
      !payload.classes.every(
        (entry, index) =>
          entry.id === index && typeof entry.label_ko === 'string',
      )
    )
      fail('클래스 정보');
    const metrics = payload.metrics?.test;
    if (
      !metrics ||
      !finite(metrics.macro_f1) ||
      !finite(metrics.accuracy) ||
      !Array.isArray(metrics.per_class) ||
      metrics.per_class.length !== 4
    )
      fail('테스트 지표');
    const matrix = metrics.confusion_matrix;
    if (
      !Array.isArray(matrix) ||
      matrix.length !== 4 ||
      !matrix.every(
        (row) =>
          Array.isArray(row) &&
          row.length === 4 &&
          row.every((count) => Number.isInteger(count) && count >= 0),
      )
    )
      fail('혼동행렬');
    const total = matrix.flat().reduce((sum, count) => sum + count, 0);
    if (total !== metrics.cell_count || total < 1) fail('테스트 세포 수');
    const matrixF1 = matrix.map((row, index) => {
      const support = row.reduce((sum, value) => sum + value, 0);
      const calls = matrix.reduce((sum, other) => sum + other[index], 0);
      const entry = metrics.per_class[index];
      if (
        entry.id !== index ||
        entry.support !== support ||
        !['precision', 'recall', 'f1'].every((key) => finite(entry[key]))
      )
        fail('클래스별 지표');
      return support + calls ? (2 * row[index]) / (support + calls) : 0;
    });
    if (
      Math.abs(matrixF1.reduce((a, b) => a + b, 0) / 4 - metrics.macro_f1) >
      1e-9
    )
      fail('macro-F1과 혼동행렬 불일치');
    const seenCases = new Set();
    let cells = 0;
    for (const split of ['train', 'validation', 'test']) {
      const info = payload.protocol?.split?.[split];
      if (
        !info ||
        !Array.isArray(info.case_ids) ||
        !Number.isInteger(info.image_count) ||
        !Number.isInteger(info.cell_count)
      )
        fail('분리 정보');
      for (const id of info.case_ids) {
        if (seenCases.has(id)) fail('분할 간 case 중복');
        seenCases.add(id);
      }
      cells += info.cell_count;
    }
    if (
      cells !== payload.dataset?.cell_count ||
      payload.protocol.split.test.cell_count !== total
    )
      fail('전체·분리별 세포 수');
    if (!Array.isArray(payload.examples)) fail('표시 사례 목록');
    const seenExamples = new Set();
    for (const example of payload.examples) {
      if (
        !example ||
        typeof example.id !== 'string' ||
        seenExamples.has(example.id)
      )
        fail('중복·누락된 사례 ID');
      seenExamples.add(example.id);
      if (
        !['correct', 'incorrect'].includes(example.kind) ||
        ![example.gt_class, example.pred_class].every(
          (value) => Number.isInteger(value) && value >= 0 && value < 4,
        )
      )
        fail('정답·예측 클래스');
      if (
        (example.gt_class === example.pred_class) !==
        (example.kind === 'correct')
      )
        fail('정답·실패 구분');
      if (!payload.protocol.split.test.case_ids.includes(example.case_id))
        fail('테스트 밖의 표시 사례');
      if (
        !Array.isArray(example.center) ||
        example.center.length !== 2 ||
        !example.center.every(
          (value) => Number.isInteger(value) && value >= 0 && value < 224,
        )
      )
        fail('정답 중심 좌표');
      if (JSON.stringify(example.source_size) !== '[224,224]')
        fail('원본 패치 크기');
      const box = example.crop_bbox;
      if (
        !Array.isArray(box) ||
        box.length !== 4 ||
        !box.every(Number.isInteger) ||
        box[0] < 0 ||
        box[1] < 0 ||
        box[2] > 224 ||
        box[3] > 224 ||
        box[2] - box[0] !== 48 ||
        box[3] - box[1] !== 48
      )
        fail('crop 범위');
      const point = [example.center[0] - box[0], example.center[1] - box[1]];
      if (
        !point.every((value) => value >= 0 && value < 48) ||
        JSON.stringify(point) !== JSON.stringify(example.point_in_crop)
      )
        fail('crop 안의 중심 좌표');
      for (const [field, suffix] of [
        ['source_image', 'source'],
        ['crop_image', 'crop'],
      ]) {
        if (
          typeof example[field] !== 'string' ||
          !new RegExp(`^ihc/examples/[a-z0-9-]+-${suffix}\\.png$`).test(
            example[field],
          )
        )
          fail('영상 파일 경로');
      }
      const probabilities = example.probabilities;
      if (
        !Array.isArray(probabilities) ||
        probabilities.length !== 4 ||
        !probabilities.every(
          (value) => finite(value) && value >= 0 && value <= 1,
        ) ||
        Math.abs(probabilities.reduce((a, b) => a + b, 0) - 1) > 1e-6
      )
        fail('모델 점수');
      const max = Math.max(...probabilities);
      if (
        !finite(example.confidence) ||
        Math.abs(example.confidence - max) > 1e-6 ||
        probabilities.indexOf(max) !== example.pred_class
      )
        fail('예측과 모델 점수 불일치');
    }
    if (!/^[a-f0-9]{64}$/.test(payload.model?.sha256 || '')) fail('모델 해시');
    return payload;
  }

  function filteredExamples() {
    return data ? data.examples.filter((example) => example.kind === kind) : [];
  }

  function controls() {
    const examples = filteredExamples();
    const exists = Boolean(data?.examples.length);
    $('filterWrong').disabled =
      !exists || !data.examples.some((example) => example.kind === 'incorrect');
    $('filterCorrect').disabled =
      !exists || !data.examples.some((example) => example.kind === 'correct');
    $('exampleSelect').disabled = examples.length === 0;
    $('prevExample').disabled = examples.length < 2;
    $('nextExample').disabled = examples.length < 2;
    $('showPoint').disabled = document.body.dataset.phase !== 'ready';
  }

  function setPhase(phase, title = '', detail = '') {
    document.body.dataset.phase = phase;
    $('stageMessage').hidden = phase === 'ready';
    $('retryLoad').hidden = !['error', 'empty'].includes(phase);
    if (phase !== 'ready') {
      text('stageTitle', title);
      text('stageDetail', detail);
      text('status', detail || title);
    }
    controls();
  }

  function clearSelection() {
    $('imagePlane').hidden = true;
    $('sourceOverlay').setAttribute('hidden', '');
    $('cropOverlay').setAttribute('hidden', '');
    $('cropImage').hidden = true;
    $('cropPlaceholder').hidden = false;
    for (const id of ['sourceImage', 'cropImage']) {
      $(id).removeAttribute('src');
      $(id).removeAttribute('data-example');
    }
    for (const id of ['truthLabel', 'predictionLabel', 'selectedScore'])
      text(id, '—');
    text('verdict', '선택 대기');
    $('verdict').className = 'verdict';
    text('selectedId', '');
    text('pointPosition', 'GT 좌표 —');
    text(
      'caseExplanation',
      '실제 사례를 선택하면 정답과 예측의 차이를 표시합니다.',
    );
    $('classScores').replaceChildren();
  }

  function addRow(target, values, headerFirst = false) {
    const row = element('tr');
    values.forEach((value, index) =>
      row.append(element(headerFirst && index === 0 ? 'th' : 'td', value)),
    );
    target.append(row);
  }

  function renderExperiment() {
    const metrics = data.metrics.test;
    text('testMacroF1', fixed(metrics.macro_f1));
    text('testAccuracy', fixed(metrics.accuracy));
    const test = data.protocol.split.test;
    text(
      'testCount',
      `${test.case_ids.length} test case · ${number(test.image_count)} 패치 · ${number(test.cell_count)}개 정답 중심`,
    );
    $('classMetrics').replaceChildren();
    metrics.per_class.forEach((entry, index) =>
      addRow($('classMetrics'), [
        shortNames[index],
        fixed(entry.precision),
        fixed(entry.recall),
        fixed(entry.f1),
      ]),
    );
    $('confusionRows').replaceChildren();
    metrics.confusion_matrix.forEach((row, index) =>
      addRow($('confusionRows'), [shortNames[index], ...row.map(number)], true),
    );
    $('splitRows').replaceChildren();
    for (const [key, label] of [
      ['train', 'Train'],
      ['validation', 'Validation'],
      ['test', 'Test'],
    ]) {
      const split = data.protocol.split[key];
      addRow($('splitRows'), [
        label,
        split.case_ids.length,
        number(split.image_count),
        number(split.cell_count),
      ]);
    }
    text(
      'selectionMethod',
      `저자 fold ${data.protocol.author_test_fold} test 고정 · seed ${data.protocol.seed}. C 후보 ${data.protocol.C_candidates.join(' / ')} 중 validation macro-F1으로 C=${data.protocol.selected_C} 선택. 정규화는 train만 사용하고 test로 조정하지 않았습니다.`,
    );
    text(
      'modelMethod',
      `${data.protocol.features.length}개 고정 RGB/HSV/optical-density 색상 특징과 CPU 다중 클래스 로지스틱 회귀입니다. 사전학습 모델·경계 분할을 쓰지 않았고, 네 점수의 argmax로 분류합니다.`,
    );
    const runtime = data.runtime;
    text(
      'runtimeText',
      `전체 ${fixed(runtime.total_wall_seconds, 2)}초 · 영상/라벨 검사·특징 ${fixed(runtime.feature_extraction_seconds, 2)}초 · 학습/선택 ${fixed(runtime.candidate_training_seconds, 2)}초 · 최대 RSS ${fixed(runtime.peak_process_rss_mib, 1)} MiB. BLAS ${runtime.fit_blas_threads} thread, scikit-learn ${runtime.versions['scikit-learn']}.`,
    );
    const discrepancy = data.dataset.statistics_discrepancy;
    text(
      'statisticsDiscrepancy',
      `현재 ZIP의 실제 점 라벨 ${number(discrepancy.actual_downloaded_point_masks)}개. 논문·전체 통계는 ${number(discrepancy.global_stats_txt_and_paper)}개로 차이가 있으며 원인은 미확인입니다. 이 실험은 실제 파일 수를 사용합니다.`,
    );
    const ratio = data.annotated_cell_ratio_summary;
    text(
      'ratioText',
      ratio.case_mae_percentage_points === null
        ? '유효한 분모가 있는 case 비율 결과가 없습니다.'
        : `주석 세포의 종양 양성률 case별 평균 절대오차 ${fixed(ratio.case_mae_percentage_points)} percentage points (${ratio.defined_cases} case). 분모 0으로 제외한 case ${ratio.excluded_zero_denominator_cases}개.`,
    );
    text('authors', data.attribution.authors);
    text('modelHash', data.model.sha256);
    text(
      'sampleNote',
      `전체 테스트 ${number(test.cell_count)}개 세포 중 표시용으로 고른 ${data.examples.length}개입니다. 정답 ${data.examples.filter((example) => example.kind === 'correct').length} · 실패 ${data.examples.filter((example) => example.kind === 'incorrect').length}.`,
    );
  }

  function renderExampleList() {
    const examples = filteredExamples();
    $('filterWrong').setAttribute('aria-pressed', String(kind === 'incorrect'));
    $('filterCorrect').setAttribute('aria-pressed', String(kind === 'correct'));
    $('exampleList').replaceChildren();
    $('exampleSelect').replaceChildren();
    text('caseCount', `${examples.length}개`);
    examples.forEach((example, index) => {
      const option = element(
        'option',
        `${index + 1}. ${example.case_id} · ${shortNames[example.gt_class]}`,
      );
      option.value = example.id;
      $('exampleSelect').append(option);
      const button = element('button', undefined, 'example-item');
      button.type = 'button';
      button.dataset.example = example.id;
      button.setAttribute('aria-current', String(selected?.id === example.id));
      button.setAttribute(
        'aria-label',
        `${kind === 'incorrect' ? '실패' : '정답'} 사례 ${index + 1}, ${example.case_id}, 정답 ${data.classes[example.gt_class].label_ko}`,
      );
      const image = element('img');
      image.src = example.crop_image;
      image.alt = '';
      image.loading = 'lazy';
      const description = element('div');
      description.append(
        element('strong', example.case_id),
        element(
          'span',
          `${shortNames[example.gt_class]} → ${shortNames[example.pred_class]}`,
        ),
      );
      button.append(image, description);
      button.addEventListener('click', () => {
        if (matchMedia('(max-width: 760px)').matches) setCases(false);
        selectExample(example.id);
      });
      $('exampleList').append(button);
    });
    if (!examples.length)
      $('exampleSelect').append(element('option', '표시할 사례 없음'));
    if (selected && examples.some((example) => example.id === selected.id))
      $('exampleSelect').value = selected.id;
    controls();
  }

  function loadImage(path, width, height) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      const timeout = setTimeout(() => {
        image.onload = null;
        image.onerror = null;
        reject(new Error(`영상 요청 시간 초과: ${path}`));
      }, 15000);
      image.onload = () => {
        clearTimeout(timeout);
        if (image.naturalWidth !== width || image.naturalHeight !== height)
          reject(new Error(`원자료와 영상 크기가 다릅니다: ${path}`));
        else resolve(image);
      };
      image.onerror = () => {
        clearTimeout(timeout);
        reject(
          new Error(`원영상 또는 crop 파일을 불러오지 못했습니다: ${path}`),
        );
      };
      image.src = path;
    });
  }

  function updateMarkers(example) {
    const [x, y] = example.center.map((value) => value + 0.5);
    for (const id of ['gtHalo', 'gtPoint']) {
      $(id).setAttribute('cx', x);
      $(id).setAttribute('cy', y);
    }
    $('gtCross').setAttribute(
      'd',
      `M${x - 8},${y}h4 M${x + 4},${y}h4 M${x},${y - 8}v4 M${x},${y + 4}v4`,
    );
    $('cropOutline').setAttribute('x', example.crop_bbox[0]);
    $('cropOutline').setAttribute('y', example.crop_bbox[1]);
    const [cropX, cropY] = example.point_in_crop.map((value) => value + 0.5);
    for (const id of ['cropHalo', 'cropPoint']) {
      $(id).setAttribute('cx', cropX);
      $(id).setAttribute('cy', cropY);
    }
    $('sourceOverlay').toggleAttribute('hidden', !$('showPoint').checked);
    $('cropOverlay').toggleAttribute('hidden', !$('showPoint').checked);
  }

  function renderScores(example) {
    $('classScores').replaceChildren();
    example.probabilities.forEach((probability, index) => {
      const row = element(
        'div',
        undefined,
        `score-row${index === example.pred_class ? ' predicted' : ''}`,
      );
      const title = element('div', undefined, 'score-title');
      title.append(element('span', data.classes[index].label_ko));
      if (index === example.gt_class)
        title.append(element('span', '정답', 'score-tag'));
      if (index === example.pred_class)
        title.append(element('span', '예측', 'score-tag'));
      const track = element('div', undefined, 'score-track');
      const fill = element('div', undefined, 'score-fill');
      fill.style.width = percent(probability);
      track.setAttribute('aria-hidden', 'true');
      track.append(fill);
      row.append(
        title,
        element('span', percent(probability), 'score-number'),
        track,
      );
      $('classScores').append(row);
    });
    if (example.kind === 'correct')
      text(
        'caseExplanation',
        '이 정답 중심에서는 세포 유형이 일치합니다. 주변 세포의 검출 성공 여부를 뜻하지 않습니다.',
      );
    else {
      const sameStain =
        [0, 2].includes(example.gt_class) ===
        [0, 2].includes(example.pred_class);
      const sameTumor = example.gt_class < 2 === example.pred_class < 2;
      const reason =
        sameStain && !sameTumor
          ? '염색의 양성·음성은 같지만 종양 여부를 잘못 분류했습니다.'
          : sameTumor && !sameStain
            ? '종양 여부는 같지만 Ki67 양성·음성을 잘못 분류했습니다.'
            : '종양 여부와 Ki67 양성·음성을 모두 잘못 분류했습니다.';
      text('caseExplanation', reason);
    }
  }

  async function selectExample(id) {
    const example = data?.examples.find((entry) => entry.id === id);
    if (!example) return;
    const ticket = ++generation;
    selected = example;
    kind = example.kind;
    failureKind = null;
    clearSelection();
    renderExampleList();
    text('activeCase', example.case_id);
    text('sourceMeta', '실제 원본 224 × 224 px · 화면 맞춤');
    setPhase(
      'loading',
      '선택한 세포의 영상을 읽는 중',
      `${example.case_id}의 원본과 48px crop을 확인합니다.`,
    );
    try {
      const [source, crop] = await Promise.all([
        loadImage(example.source_image, 224, 224),
        loadImage(example.crop_image, 48, 48),
      ]);
      if (ticket !== generation) return;
      source.id = 'sourceImage';
      crop.id = 'cropImage';
      $('sourceImage').replaceWith(source);
      $('cropImage').replaceWith(crop);
      $('sourceImage').dataset.example = example.id;
      $('cropImage').dataset.example = example.id;
      $('sourceImage').alt =
        `${example.case_id}의 실제 224픽셀 IHC 패치, 정답 중심 ${example.center.join(', ')}`;
      $('cropImage').alt =
        `${example.case_id}의 선택 세포 주변 실제 48픽셀 crop`;
      $('imagePlane').hidden = false;
      $('cropImage').hidden = false;
      $('cropPlaceholder').hidden = true;
      updateMarkers(example);
      text('truthLabel', data.classes[example.gt_class].label_ko);
      text('predictionLabel', data.classes[example.pred_class].label_ko);
      text('selectedScore', percent(example.confidence));
      text('selectedId', example.id);
      text('verdict', example.kind === 'correct' ? '분류 일치' : '분류 불일치');
      $('verdict').className = `verdict ${example.kind}`;
      text(
        'pointPosition',
        `GT 중심 x ${example.center[0]}, y ${example.center[1]}`,
      );
      renderScores(example);
      setPhase('ready');
      text(
        'status',
        `${example.case_id} · ${kind === 'incorrect' ? '실패' : '정답'} 사례 ${filteredExamples().findIndex((entry) => entry.id === example.id) + 1}/${filteredExamples().length} · 저장 결과 열람`,
      );
      const url = new URL(location.href);
      url.searchParams.set('example', example.id);
      history.replaceState(null, '', url);
    } catch (error) {
      if (ticket !== generation) return;
      failureKind = 'image';
      setPhase('error', '선택한 영상을 열지 못했습니다', error.message);
    }
  }

  async function loadResults() {
    fetchController?.abort();
    fetchController = new AbortController();
    const controller = fetchController;
    const ticket = ++generation;
    data = null;
    selected = null;
    failureKind = null;
    clearSelection();
    for (const id of ['testMacroF1', 'testAccuracy']) text(id, '—');
    for (const id of [
      'exampleList',
      'classMetrics',
      'confusionRows',
      'splitRows',
    ])
      $(id).replaceChildren();
    for (const id of [
      'selectionMethod',
      'modelMethod',
      'runtimeText',
      'statisticsDiscrepancy',
      'ratioText',
      'authors',
      'modelHash',
    ])
      text(id, '');
    $('exampleSelect').replaceChildren(element('option', '사례 로딩 중'));
    text('caseCount', '—');
    text('activeCase', '실제 IHC 영상');
    text('testCount', '고정 테스트 정보를 읽는 중');
    setPhase(
      'loading',
      '실제 결과를 읽는 중',
      '저장된 분류와 원영상의 출처를 확인합니다.',
    );
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('ihc/results.json', {
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(`결과 요청 실패 (HTTP ${response.status})`);
      const payload = validate(await response.json());
      if (ticket !== generation) return;
      data = payload;
      renderExperiment();
      if (!data.examples.length) {
        renderExampleList();
        failureKind = 'data';
        setPhase(
          'empty',
          '표시할 세포 사례가 없습니다',
          '결과 파일의 사례 목록이 비어 있습니다. 임의의 영상을 대신 표시하지 않습니다.',
        );
        return;
      }
      const query = new URL(location.href).searchParams.get('example');
      const initial =
        data.examples.find((example) => example.id === query) ||
        data.examples.find((example) => example.kind === 'incorrect') ||
        data.examples[0];
      await selectExample(initial.id);
    } catch (error) {
      if (ticket !== generation) return;
      data = null;
      failureKind = 'data';
      setPhase(
        'error',
        '실제 결과를 열지 못했습니다',
        error.name === 'AbortError'
          ? '결과 요청 시간이 초과되었습니다. 다시 불러올 수 있습니다.'
          : error.message,
      );
    } finally {
      clearTimeout(timeout);
    }
  }

  function setResults(open) {
    document.body.classList.toggle('results-hidden', !open);
    $('toggleResults').setAttribute('aria-expanded', String(open));
    if (open && matchMedia('(max-width: 760px)').matches) setCases(false);
  }
  function setCases(open) {
    document.body.classList.toggle('cases-hidden', !open);
    $('toggleCases').setAttribute('aria-expanded', String(open));
    if (open && matchMedia('(max-width: 760px)').matches) setResults(false);
  }
  function chooseKind(value) {
    kind = value;
    const next = filteredExamples()[0];
    if (next) selectExample(next.id);
  }
  $('filterWrong').addEventListener('click', () => chooseKind('incorrect'));
  $('filterCorrect').addEventListener('click', () => chooseKind('correct'));
  $('exampleSelect').addEventListener('change', (event) =>
    selectExample(event.target.value),
  );
  for (const [id, direction] of [
    ['prevExample', -1],
    ['nextExample', 1],
  ])
    $(id).addEventListener('click', () => {
      const examples = filteredExamples();
      if (!examples.length) return;
      const index = examples.findIndex(
        (example) => example.id === selected?.id,
      );
      selectExample(
        examples[(index + direction + examples.length) % examples.length].id,
      );
    });
  $('showPoint').addEventListener('change', () => {
    if (selected && document.body.dataset.phase === 'ready')
      updateMarkers(selected);
  });
  $('retryLoad').addEventListener('click', () =>
    failureKind === 'image' && selected
      ? selectExample(selected.id)
      : loadResults(),
  );
  $('toggleResults').addEventListener('click', () =>
    setResults(document.body.classList.contains('results-hidden')),
  );
  $('closeResults').addEventListener('click', () => setResults(false));
  $('toggleCases').addEventListener('click', () =>
    setCases(document.body.classList.contains('cases-hidden')),
  );
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !event.target.matches('select')) {
      if (matchMedia('(max-width: 1100px)').matches) setResults(false);
      if (matchMedia('(max-width: 760px)').matches) setCases(false);
    }
  });
  matchMedia('(max-width: 1100px)').addEventListener('change', (event) =>
    setResults(!event.matches),
  );
  matchMedia('(max-width: 760px)').addEventListener('change', (event) =>
    setCases(!event.matches),
  );
  setResults(!matchMedia('(max-width: 1100px)').matches);
  setCases(!matchMedia('(max-width: 760px)').matches);
  loadResults();
})();
