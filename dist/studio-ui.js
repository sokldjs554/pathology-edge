'use strict';
// Three review layouts, backed exclusively by the existing saved image/results.
window.Studio = {
  layout: 'compare',
  comparison: 'two',
  updateViewState() {
    $('viewState').textContent = this.layout === 'image' ? 'B 결과 탐색 중' : this.layout === 'data' ? '후보 데이터 · B 결과' : innerWidth <= 760 ? 'A/B 버튼으로 같은 위치 전환' : this.comparison === 'four' ? 'A/B · 원본 · 정답 비교' : 'A/B 경계 비교 중';
  },
  updateFilmstrip() {
    const four = this.layout === 'compare' && this.comparison === 'four';
    if (four !== !!this.fourActive) {
      if (four) this.trayWasHidden = $('workbench').classList.contains('tray-hidden');
      const hidden = four || innerWidth <= 760 || this.trayWasHidden;
      $('workbench').classList.toggle('tray-hidden', !!hidden);
      $('toggleTray').setAttribute('aria-expanded', String(!hidden));
      this.fourActive = four;
    }
  },
  setComparison(comparison) {
    if (!['two', 'four'].includes(comparison)) return;
    this.comparison = comparison;
    document.body.dataset.comparison = comparison;
    for (const [id,value] of [['modeBoundary','two'],['compareFour','four']]) $(id).setAttribute('aria-pressed',String(value===comparison && state.mode==='boundary'));
    this.setLayout('compare');
  },
  startView() {
    // Start a desktop pathology view at native source resolution. Fit remains
    // an explicit control; switching layouts preserves the current camera.
    if (this.layout !== 'image' || innerWidth <= 760 || state.phase !== 'ready') return;
    state.zoom = Math.max(state.zoom, 1); state.fitMode = false; clampView(); draw(); renderObjectOptions();
  },
  setLayout(layout) {
    if (!['image', 'compare', 'data'].includes(layout)) return;
    if (layout !== 'compare') Review.intent++;
    this.layout = layout;
    document.body.dataset.layout = layout;
    $('workspaceName').textContent = {image:'병리 영상 작업대 · B 결과 탐색',compare:'나눠 본 영상, 핵 예측도 같을까요?',data:'영상과 후보 데이터 연결'}[layout];
    this.updateViewState();
    window.ReviewEntry?.refresh();
    this.updateFilmstrip();
    if (layout !== 'compare') setMobileSide('after');
    WorkbenchUI.setExpanded(null);
    WorkbenchUI.toggleDock(layout === 'data');
    $('workbench').classList.add('inspector-hidden');
    $('toggleInspector').setAttribute('aria-expanded','false');
    if (state.mode === 'single' && layout === 'compare' && state.phase === 'ready') setMode('boundary');
    requestAnimationFrame(() => { if (state.phase === 'ready') { if (state.fitMode) fit(); else { clampView(); draw(); } } });
  },
  drawReferences() {
    for (const [id, truth] of [['referenceSource',false],['referenceTruth',true]]) {
      const canvas = $(id), d = dimensions(canvas);
      if (!d.width || !d.height || state.phase !== 'ready') continue;
      const ratio = Math.min(devicePixelRatio || 1,2);
      canvas.width = Math.round(d.width*ratio); canvas.height = Math.round(d.height*ratio);
      const ctx = canvas.getContext('2d'), t = M.transform(d.width,d.height,state.zoom,state.cx,state.cy);
      canvas.dataset.center = `${state.cx.toFixed(3)},${state.cy.toFixed(3)}`;
      canvas.dataset.zoom = state.zoom.toFixed(5);
      ctx.setTransform(ratio,0,0,ratio,0,0); ctx.fillStyle='#202022'; ctx.fillRect(0,0,d.width,d.height);
      ctx.translate(t.ox,t.oy); ctx.scale(t.scale,t.scale); ctx.imageSmoothingEnabled=state.zoom<1;
      ctx.drawImage(state.images.base,0,0);
      if(truth) { ctx.globalAlpha=.55;ctx.drawImage(state.images.truth,0,0);ctx.globalAlpha=1; }
      if(state.selected) {
        const [x0,y0,x1,y1]=state.selected.o.bbox;ctx.strokeStyle='#f2ca68';ctx.lineWidth=1.8/state.zoom;ctx.strokeRect(x0,y0,x1-x0,y1-y0);
      }
    }
  },
};
// Data occupies a dedicated column, not a dock hidden by laptop-height heuristics.
$('workbench').append($('candidateDock'));
$('compareFour').addEventListener('click',()=>{if(state.mode!=='boundary')setMode('boundary');Studio.setComparison('four');});
$('toggleDock').addEventListener('click',()=>Studio.setLayout(Studio.layout==='data'?'compare':'data'));
$('closeDock').addEventListener('click',()=>Studio.setLayout('compare'));
$('modeMerge').addEventListener('click',()=>{Review.intent++;Studio.setComparison('two');});
for(const id of ['showImproved','showWorsened','jumpBoundary']) $(id).addEventListener('click',()=>Studio.setComparison('two'));
$('modeSingle').addEventListener('click',()=>Studio.setLayout('image'));
// References use the same camera and inverse coordinate mapping as A/B.
for(const id of ['referenceSource','referenceTruth']) {
  const c=$(id); let drag=null;
  c.addEventListener('pointerdown',e=>{if(state.phase!=='ready')return;drag={x:e.clientX,y:e.clientY,cx:state.cx,cy:state.cy};c.setPointerCapture(e.pointerId);});
  c.addEventListener('pointermove',e=>{if(!drag)return;state.cx=drag.cx-(e.clientX-drag.x)/state.zoom;state.cy=drag.cy-(e.clientY-drag.y)/state.zoom;state.fitMode=false;clampView();scheduleDraw();});
  for(const ev of ['pointerup','pointercancel','lostpointercapture'])c.addEventListener(ev,()=>{drag=null;});
  c.addEventListener('wheel',e=>{if(state.phase!=='ready')return;e.preventDefault();const p=eventPoint(e,c),d=dimensions(c),unit=e.deltaMode===1?16:e.deltaMode===2?d.height:1;
    if(e.ctrlKey||e.metaKey)setZoom(state.zoom*Math.exp(-e.deltaY*unit*.002),p.x,p.y,c);
    else {state.cx+=e.deltaX*unit/state.zoom;state.cy+=e.deltaY*unit/state.zoom;state.fitMode=false;clampView();draw();renderObjectOptions();}
  },{passive:false});
  c.addEventListener('keydown',e=>{if(state.phase!=='ready')return;const shifts={ArrowLeft:[-25,0],ArrowRight:[25,0],ArrowUp:[0,-25],ArrowDown:[0,25]};if(shifts[e.key]){e.preventDefault();state.cx+=shifts[e.key][0]/state.zoom;state.cy+=shifts[e.key][1]/state.zoom;state.fitMode=false;clampView();draw();}});
}
new ResizeObserver(()=>{if(state.phase==='ready')Studio.drawReferences();}).observe($('panes'));
matchMedia('(max-width:760px)').addEventListener('change',()=>{Studio.updateFilmstrip();Studio.updateViewState();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&state.expandedSide)WorkbenchUI.setExpanded(null);});
Studio.setComparison('two');
