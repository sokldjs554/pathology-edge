'use strict';
// Presentation over the original saved results and original selection engine.
window.WorkbenchUI = {
  lastSample: null,
  lastRows: '',
  lastCrop: '',
  refresh() {
    const ready = state.phase === 'ready' && !!state.sample;
    for (const id of ['candidateQuery', 'edgeOnly', 'objectSource', 'visibleOnly', 'toolPan', 'toolSelect', 'maximizeBefore', 'maximizeAfter']) $(id).disabled = !ready;
    const sampleId = state.sample?.id || null;
    if (sampleId !== this.lastSample) {
      this.lastSample = sampleId;
      this.lastRows = '';
      $('candidateQuery').value = '';
      $('edgeOnly').checked = false;
      $('candidateRows').replaceChildren();
    }
    if (!ready) {
      $('candidateRows').replaceChildren();
      $('candidateCount').textContent = '—';
      $('candidateEmpty').hidden = false;
      $('candidateEmpty').textContent = state.phase === 'error' ? '결과를 불러온 뒤 후보를 확인할 수 있습니다.' : state.phase === 'empty' ? '표시할 예제가 없습니다.' : '저장된 후보를 불러오는 중입니다.';
      $('selectionPreview').hidden = true;
      this.lastCrop = this.lastRows = '';
      return;
    }
    const side = $('objectSource').value;
    const objects = paneData(side).objects;
    const rows = WorkbenchData.rows(objects, {
      query: $('candidateQuery').value,
      edgeOnly: $('edgeOnly').checked,
      bounds: $('visibleOnly').checked ? currentBounds() : null,
    });
    $('candidateCount').textContent = `${rows.length} / ${objects.length}개 · ${side === 'before' ? 'A' : 'B'}`;
    $('candidateEmpty').hidden = rows.length !== 0;
    $('candidateEmpty').textContent = '조건에 맞는 후보가 없습니다. 번호나 필터를 확인하세요.';
    const key = `${sampleId}/${state.mode}/${side}/${rows.map(r => r.index).join(',')}`;
    if (key !== this.lastRows) {
      this.lastRows = key;
      const fragment = document.createDocumentFragment();
      for (const { object: o, index } of rows) {
        const tr = node('tr');
        tr.dataset.index = String(index);
        const first = node('td');
        const button = node('button', `#${index + 1}`, 'candidate-link');
        button.type = 'button';
        button.setAttribute('aria-label', `${side === 'before' ? 'A' : 'B'} 후보 ${index + 1} 위치와 상세 정보`);
        button.addEventListener('click', () => {
          this.setTool('select');
          selectObject(side, index, true);
        });
        first.append(button);
        tr.append(first, node('td', `${o.x.toFixed(1)}, ${o.y.toFixed(1)}`), node('td', String(o.area)), node('td', fmt(o.score)), node('td', String(o.patch_id)), node('td', o.touches_edge ? '접촉' : '—'));
        fragment.append(tr);
      }
      $('candidateRows').replaceChildren(fragment);
    }
    for (const row of $('candidateRows').children) {
      const selected = state.selected?.side === side && state.selected.index === Number(row.dataset.index);
      row.classList.toggle('selected', selected);
      row.querySelector('button').setAttribute('aria-pressed', String(selected));
    }
    const selected = state.selected;
    $('selectionPreview').hidden = !selected;
    if (selected) {
      const cropKey = `${sampleId}/${state.mode}/${selected.side}/${selected.index}`;
      if (cropKey !== this.lastCrop) {
        this.lastCrop = cropKey;
        const box = WorkbenchData.cropBox(selected.o, state.sample.width, state.sample.height);
        const canvas = $('selectedCrop'), ctx = canvas.getContext('2d');
        const scale = Math.min(canvas.width / box.width, canvas.height / box.height);
        const x = (canvas.width - box.width * scale) / 2, y = (canvas.height - box.height * scale) / 2;
        ctx.fillStyle = '#19292e'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(state.images.base, box.x, box.y, box.width, box.height, x, y, box.width * scale, box.height * scale);
        const [x0,y0,x1,y1] = selected.o.bbox;
        ctx.strokeStyle = '#ffe27b'; ctx.lineWidth = 2;
        ctx.strokeRect(x + (x0-box.x)*scale, y + (y0-box.y)*scale, (x1-x0)*scale, (y1-y0)*scale);
        $('cropCaption').textContent = `${selected.side === 'before' ? 'A' : 'B'} #${selected.index + 1} · 원본 조직 / 노란 상자: 후보 범위`;
      }
    } else this.lastCrop = '';
  },
  setTool(tool) {
    state.tool = tool;
    document.body.dataset.tool = tool;
    $('toolPan').setAttribute('aria-pressed', String(tool === 'pan'));
    $('toolSelect').setAttribute('aria-pressed', String(tool === 'select'));
    if (tool === 'select') $('objects').checked = true;
    draw();
  },
  setExpanded(side) {
    state.expandedSide = side;
    $('panes').dataset.expanded = side || '';
    for (const [name, key] of [['Before','before'],['After','after']]) {
      const b = $(`maximize${name}`), expanded = side === key;
      b.setAttribute('aria-pressed', String(expanded));
      b.setAttribute('aria-label', expanded ? '좌우 비교로 복원' : `${key === 'before' ? 'A' : 'B'} 영상 크게 보기`);
      b.title = b.getAttribute('aria-label');
      b.textContent = expanded ? '↔' : '⛶';
    }
    requestAnimationFrame(() => {
      if (state.phase !== 'ready') return;
      if (state.fitMode) fit(); else { clampView(); draw(); renderObjectOptions(); }
    });
  },
  toggleDock(open) {
    $('candidateDock').hidden = !open;
    $('toggleDock').setAttribute('aria-expanded', String(open));
  },
};
for (const id of ['candidateQuery','edgeOnly']) $(id).addEventListener(id === 'candidateQuery' ? 'input' : 'change', () => WorkbenchUI.refresh());
$('toolPan').addEventListener('click', () => WorkbenchUI.setTool('pan'));
$('toolSelect').addEventListener('click', () => WorkbenchUI.setTool('select'));
// Checking the existing candidate overlay remains a direct route to selection.
$('objects').addEventListener('change', () => WorkbenchUI.setTool($('objects').checked ? 'select' : 'pan'));
$('toggleDock').addEventListener('click', () => WorkbenchUI.toggleDock($('candidateDock').hidden));
$('closeDock').addEventListener('click', () => { WorkbenchUI.toggleDock(false); $('toggleDock').focus(); });
for (const [name, side] of [['Before','before'],['After','after']]) $(`maximize${name}`).addEventListener('click', () => WorkbenchUI.setExpanded(state.expandedSide === side ? null : side));
$('focusMode').addEventListener('click', () => {
  if (state.focus) { WorkbenchUI.dockBeforeFocus = !$('candidateDock').hidden; WorkbenchUI.toggleDock(false); }
  else WorkbenchUI.toggleDock(WorkbenchUI.dockBeforeFocus ?? true);
});
const compactWorkbench = matchMedia('(max-width:760px)');
compactWorkbench.addEventListener('change', () => { WorkbenchUI.setExpanded(null); WorkbenchUI.toggleDock(!compactWorkbench.matches && innerHeight >= 820); });
WorkbenchUI.toggleDock(!compactWorkbench.matches && innerHeight >= 820);
WorkbenchUI.setTool('pan');
WorkbenchUI.refresh();
