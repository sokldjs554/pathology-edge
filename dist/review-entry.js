'use strict';
// Progressive disclosure over verified saved evidence; no new metrics or inference.
window.ReviewEntry = {
  lastKey: '',
  refresh() {
    const ready = state.phase === 'ready' && state.sample;
    const layout = Studio.layout;
    const c = ready && layout === 'compare' && state.mode === 'boundary' ? Review.selected : null;
    const key = [state.phase, state.sample?.id, state.mode, layout, Studio.comparison, c?.id].join('/');
    if (key === this.lastKey) return;
    this.lastKey = key;
    $('caseEvidence').hidden = !c;
    $('returnComparison').hidden = layout === 'compare' && Studio.comparison === 'two' && state.mode === 'boundary';
    $('outcomeScore').textContent = '';
    $('outcomeScore').title = '';
    $('outcomePixels').title = '';
    if (!ready) {
      $('outcomeLabel').textContent = state.phase === 'error' ? '결과를 불러오지 못했습니다' : state.phase === 'empty' ? '표시할 예제가 없습니다' : '저장된 결과 불러오는 중';
      $('outcomePixels').textContent = '';
      return;
    }
    if (c) {
      $('outcomeLabel').textContent = `${c.sample_id} · 선택 상자 경계 Dice`;
      $('outcomeScore').textContent = `${fmt(c.before.dice)} → ${fmt(c.after.dice)}`;
      $('outcomeScore').className = c.after.dice >= c.before.dice ? 'positive' : 'negative';
      $('outcomeScore').title = '0–1, 높을수록 정답과 유사 · A(무겹침) → B(겹침·결합)';
      $('outcomePixels').textContent = `정답 일치로 변경 ${c.corrected}px · 불일치로 변경 ${c.regressed}px`;
      $('outcomePixels').title = '흰 64px 상자 안의 경계 띠만 평가한 사후 선택 사례. 이미지 전체 점수나 핵 개수가 아닙니다. 청록: 일치로 변경 / 분홍: 불일치로 변경.';
    } else if (state.mode === 'merge') {
      const m = state.sample.methods.overlap;
      $('outcomeLabel').textContent = `${state.sample.id} · 중복 후보 억제`;
      $('outcomeScore').textContent = `${m.raw_count} → ${m.merged_count} 후보`;
      $('outcomeScore').className = '';
      $('outcomePixels').textContent = '같은 겹침 추론의 병합 전·후 · 실제 핵 수와 구분';
    } else {
      $('outcomeLabel').textContent = layout === 'compare' ? 'A 겹침 없음 → B 겹침·결합' : layout === 'data' ? '후보 표의 행을 선택하면 영상 위치로 이동합니다' : 'B 결과 탐색 중';
      $('outcomePixels').textContent = layout === 'compare' ? '개선·악화 사례를 선택해 같은 경계를 확인하세요.' : '경계 사례 버튼으로 A/B 비교에 돌아갈 수 있습니다.';
    }
  },
  closeTools(focus = false) {
    $('detailTools').open = false;
    if (focus) $('detailTools').querySelector('summary').focus();
  },
};
$('returnComparison').addEventListener('click',()=>{
  if(state.mode !== 'boundary')setMode('boundary');
  Studio.setComparison('two');
  $('detailTools').querySelector('summary').focus();
});
$('caseEvidence').addEventListener('click',()=>{
  setTab('image');
  $('inspector').querySelector('.inspector-scroll').scrollTop=0;
  $('closeInspector').focus();
});
$('detailTools').addEventListener('click',e=>{
  // Layer/selection controls stay open while adjusting; navigation actions close.
  const button=e.target.closest('.menu-buttons button');
  if(!button)return;
  ReviewEntry.closeTools();
  if(['toggleInspector','showResults'].includes(button.id)&&!$('workbench').classList.contains('inspector-hidden'))$('closeInspector').focus();
  else $('detailTools').querySelector('summary').focus();
});
document.addEventListener('pointerdown',e=>{
  if($('detailTools').open&&!$('detailTools').contains(e.target))ReviewEntry.closeTools();
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&$('detailTools').open){ReviewEntry.closeTools(true);e.preventDefault();}
});
$('detailTools').addEventListener('focusout',()=>{
  requestAnimationFrame(()=>{
    if($('detailTools').open&&!$('detailTools').contains(document.activeElement))ReviewEntry.closeTools();
  });
});
ReviewEntry.refresh();
