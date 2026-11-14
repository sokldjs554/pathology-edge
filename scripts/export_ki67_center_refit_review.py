#!/usr/bin/env python3
"""Export audited native A/B validation examples; standalone saved-result viewer."""
import argparse
import base64
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_ki67_union_review import panel
from pathology_edge.ki67_center_refit import checked
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_union import retain_candidates
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,load_sample


def export(root,output):
    root,output=Path(root),Path(output);p=checked(root,selected=True);audit=read_json(root/'audit.json')
    if not audit['all_checks_passed'] or audit['selection_lock_sha256']!=sha(root/'selection-lock.json'):raise ValueError('Matching audit required')
    models=read_json(root/'selection.json')['models'];manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'};summary=[];examples=[]
    for m in models:
        seed=m['seed'];trial=m['selected'] or m['diagnostic'];epoch=trial['epoch'];saved=np.load(root/f'validation-peaks-{seed}.npz',allow_pickle=False);rows=read_rows(root/f'validation-{seed}.json.gz');candidates=[]
        xy=saved[f'points_{epoch}'];sc=saved[f'scores_{epoch}'].astype(np.float64);offsets=saved[f'offsets_{epoch}']
        for index,r in enumerate(rows):
            a,b=offsets[index:index+2];new=retain_candidates(xy[a:b],sc[a:b],**trial['config'])['points_xy'];panels=dict(A=panel(r['a_points'],r['gt_points']),B=panel(new,r['gt_points']));ac,bc=panels['A']['counts'],panels['B']['counts']
            candidates.append(dict(seed=seed,image=r['image'],case_id=r['case_id'],gt=r['gt_points'],panels=panels,epoch=epoch,config=trial['config'],eligible=m['selected'] is not None,delta_errors=bc['fp']+bc['fn']-ac['fp']-ac['fn']))
        for label,row in [('오류 합 최소 변화',min(candidates,key=lambda r:(r['delta_errors'],r['image']))),('오류 합 최대 변화',max(candidates,key=lambda r:(r['delta_errors'],r['image'])))]:
            rgb,_,_=load_sample(p['data_dir'],manifest[row['image']]);buffer=io.BytesIO();Image.fromarray(rgb).save(buffer,format='PNG');examples.append({**row,'selection_reason':label,'rgb':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()})
        history=read_rows(root/f'trials-{seed}.json.gz');summary.append(dict(seed=seed,eligible=m['selected'] is not None,feasible_trials=m['feasible_trials'],A=m['baseline'],B=trial,epoch0=m['epoch0_diagnostic'],history=[dict(epoch=h['epoch'],loss=h['train_loss'],feasible=h['feasible_trials'],best_f1=max(t['case_macro_f1'] for t in h['trials'])) for h in history]))
    data=dict(summary=summary,examples=examples,source_commit=p['source_commit'],selection_lock_sha256=sha(root/'selection-lock.json'),stability=read_json(root/'stability.json'),scope=p['scope'])
    output.mkdir(parents=True,exist_ok=False);(output/'index.html').write_text(TEMPLATE.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')))
    fresh_json(output/'review-manifest.json',dict(html_sha256=sha(output/'index.html'),source_commit=p['source_commit'],selection_lock_sha256=data['selection_lock_sha256'],examples=[{k:v for k,v in r.items() if k not in ('rgb','gt','panels')} for r in examples]))


TEMPLATE='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge · 검출기 추가 학습</title>
<style>*{box-sizing:border-box}body{margin:0;color:#263d48;background:#f4f6f7;font:14px system-ui,sans-serif}header{padding:16px 22px;background:white;border-bottom:1px solid #b9c8cf}h1{font-size:20px;margin:0 0 7px}main{max-width:1450px;padding:16px 22px;margin:auto}p{line-height:1.6}.notice{border-left:4px solid #a7692b;padding:12px;background:#fff3e2;margin-bottom:14px}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;background:white}td,th{padding:9px;border-bottom:1px solid #d6e0e4;text-align:left;white-space:nowrap;font-variant-numeric:tabular-nums}th{font-size:12px}nav{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:18px 0}nav label{min-width:0;max-width:100%}select,button{max-width:100%;padding:8px;font:inherit;background:white;border:1px solid #9bacb3;border-radius:3px}button{cursor:pointer}.panels{display:grid;grid-template-columns:1fr 1fr;gap:12px}.panel{background:white;border:1px solid #b9c8cf}.title{padding:10px;background:#263f49;color:white}.counts{padding:10px;line-height:1.6}canvas{display:block;width:100%}.legend{display:flex;gap:15px;flex-wrap:wrap;margin:12px 0}.matched{color:#007bba}.fp{color:#c62664}.gt{color:#906000}details{margin:16px 0}footer{font-size:12px;color:#526772;line-height:1.7;margin:22px 0}code{overflow-wrap:anywhere;font-size:11px}@media(max-width:650px){header,main{padding:12px}.panels{grid-template-columns:1fr}h1{font-size:18px}}</style>
<header><h1>PathologyEdge · 검출기 추가 학습 검토</h1><div>같은 소형 모델을 더 학습했을 때, 잘못 찾은 후보와 놓친 세포를 함께 줄였는지 확인합니다.</div></header>
<main><div id="outcome" class="notice"></div><p>아래는 <strong>검증227장·4케이스</strong>의 결과입니다. FP·FN은 이미지 합계, F1·재현율은 케이스별 평균입니다. F1·재현율은 높을수록, FP·FN은 낮을수록 좋습니다.</p>
<div class="tablewrap"><table><thead><tr><th>seed</th><th>전체 선택 조건</th><th>추가 epoch / 임계값 / 거리</th><th>FP A → B</th><th>FN A → B</th><th>F1 A → B</th><th>재현율 A → B</th><th>B 종양+ / 종양− 위치 재현율</th></tr></thead><tbody id="summary"></tbody></table></div>
<p>채택 조건: A보다 FP·FN 각각 악화 없음(하나는 감소), 기존 LoG 재현율 하한 유지(케이스 평균0.4798·종양+0.5590·종양−0.3398), 각 케이스 재현율 ≥ A의90%.</p>
<details><summary>변경한 학습 범위와 epoch0 대조</summary><p>기존16epoch 가중치에서 시작해24epoch를 추가 학습했습니다. 이전 optimizer 상태가 없어 새 Adam을 사용했으며, 처음부터 연속40epoch 학습한 재현 결과가 아닙니다. 구조·손실·자료는 유지했습니다. 임계값 탐색 범위는 기존보다 넓어졌으므로 추가 학습만의 효과라고 단정하지 않습니다. epoch0은 새 탐색 범위에서 원래 가중치를 평가한 대조이며 채택 후보에서 제외했습니다.</p><div class="tablewrap"><table><thead><tr><th>seed</th><th>A 원래 설정 F1</th><th>epoch0 새 범위 최고 F1</th><th>추가 학습 결과 F1</th></tr></thead><tbody id="control"></tbody></table></div></details>
<nav><label>실제 사례 <select id="example" aria-label="실제 사례"></select></label><button id="prev">이전</button><button id="next">다음</button><label><input id="overlay" type="checkbox" checked> 후보·정답 표시</label></nav><p id="case"></p>
<div class="legend"><span class="matched">● 정답과 일대일 대응한 후보</span><span class="fp">● FP: 대응하지 않은 후보</span><span class="gt">○ 정답 중심 · × FN</span></div><div class="panels" id="panels"></div>
<details><summary>표시와 사례 선택 기준</summary><p>같은224×224 원영상·좌표의 A(원래 검출기)와 B(추가 학습 결과)를 비교합니다. B는 전체 조건을 통과한 설정이며, 통과 설정이 없으면 최고 검증 F1의 진단용 설정입니다. 후보 원은 핵 윤곽이 아닙니다. 두 모델이 독립적으로 중심을 예측하므로 이전 위치 보정 화면처럼 후보 간 이동 화살표를 그리지 않습니다.</p><p>각 seed에서 이미지별 (FP+FN) B−A 변화가 최소·최대인 두 사례를 고릅니다. 사후 설명용으로 전체 성능을 대표하지 않습니다. 주석과6px 이내 일대일 대응하며 세포 유형의 분류 정확도와 구분합니다.</p></details>
<details open><summary>해석 범위</summary><p>기존에 여러 번 사용한 검증 자료의 탐색 실험입니다. 세 seed는 기존 검출기와 추가 학습 seed를 짝지었습니다. 주석되지 않은 모든 위치가 전문가가 확인한 비세포 정답인 것은 아닙니다. 점수는 보정된 임상 확률이 아닙니다. 임상·전체 WSI·새 미노출 외부 일반화를 입증하지 않습니다.</p><p id="testscope"></p></details>
<footer>연구·교육용 · 저장된 결과 열람 · 화면에서 실시간 추론하지 않음<br>Patherea Breast-P1: <a href="https://huggingface.co/datasets/ds2268/patherea">Štepec et al.</a>, CC BY-NC4.0 · 예측/대응 표시 추가<br><code id="provenance"></code></footer></main>
<script>const data=__DATA__;const $=id=>document.getElementById(id);const fmt=x=>x.toFixed(4);let current=0,version=0;const passed=data.summary.filter(r=>r.eligible).length;
$('outcome').textContent=`검증 선택 조건 ${passed}/3 seed 충족. `+(passed?'통과 모델만 잠근 후 기존 테스트·외부 자료에서 재평가했습니다. 기본 배포 모델은 변경하지 않았습니다.':'새 모델을 채택하지 않았고 테스트·외부 새 추론도 실행하지 않았습니다. B는 실패 분석용 진단 모델입니다.');
$('summary').innerHTML=data.summary.map(r=>`<tr><td>${r.seed}</td><td>${r.eligible?'충족':'미충족 · 진단용'}</td><td>${r.B.epoch} / ${r.B.config.threshold} / ${r.B.config.min_distance}px</td><td>${r.A.localization.fp} → ${r.B.localization.fp}</td><td>${r.A.localization.fn} → ${r.B.localization.fn}</td><td>${fmt(r.A.case_macro_f1)} → ${fmt(r.B.case_macro_f1)}</td><td>${fmt(r.A.case_macro_recall)} → ${fmt(r.B.case_macro_recall)}</td><td>${r.B.tumor_recalls.map(fmt).join(' / ')}</td></tr>`).join('');
$('control').innerHTML=data.summary.map(r=>`<tr><td>${r.seed}</td><td>${fmt(r.A.case_macro_f1)}</td><td>${fmt(r.epoch0.case_macro_f1)}</td><td>${fmt(r.B.case_macro_f1)}</td></tr>`).join('');
$('testscope').textContent=passed?`기존 테스트의 안정성 조건 충족: ${data.stability.test_passes}/3. 검증 통과 여부와 별개이며 모든 세 seed를 분모에 포함합니다.`:'적격 모델이 없어 테스트 성공 증거는0/3입니다. 테스트를 세 번 실행해서 실패했다는 뜻이 아닙니다.';
$('provenance').textContent=`source ${data.source_commit} · selection SHA256 ${data.selection_lock_sha256}`;
data.examples.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${e.seed} · ${e.selection_reason} · ${e.image}`;$('example').append(o)});
function render(){const token=++version,e=data.examples[current];$('example').value=current;$('case').textContent=`${e.image} · ${e.case_id} · 같은224×224px · 추가epoch ${e.epoch} · 임계값${e.config.threshold}, 거리${e.config.min_distance}px · ${e.eligible?'선택 조건 충족':'조건 미충족 · 진단용'} · B−A 오류 합 ${e.delta_errors>=0?'+':''}${e.delta_errors}`;$('panels').innerHTML='';for(const key of ['A','B']){const p=e.panels[key],section=document.createElement('section');section.className='panel';section.innerHTML=`<div class="title">${key==='A'?'A · 원래 검출기 / 원래 설정':'B · 추가 학습 결과 / 선택 또는 진단 설정'}</div><canvas width="672" height="672" aria-label="${key} 검출 비교"></canvas><div class="counts">후보 ${p.points.length} · TP ${p.counts.tp} · FP ${p.counts.fp} · FN ${p.counts.fn}<br>이 이미지 F1 ${fmt(p.counts.f1)} · 재현율 ${fmt(p.counts.recall)}</div>`;$('panels').append(section);const ctx=section.querySelector('canvas').getContext('2d'),im=new Image();im.onload=()=>{if(token!==version)return;ctx.drawImage(im,0,0,672,672);if(!$('overlay').checked)return;ctx.scale(3,3);ctx.lineWidth=.7;const hit=new Set(p.matched),missed=new Set(p.missed);p.points.forEach(([x,y],i)=>{ctx.fillStyle=hit.has(i)?'#007bba':'#c62664';ctx.beginPath();ctx.arc(x,y,1.4,0,Math.PI*2);ctx.fill()});e.gt.forEach(([x,y],i)=>{ctx.strokeStyle='#ffd057';ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.stroke();if(missed.has(i)){ctx.beginPath();ctx.moveTo(x-2,y-2);ctx.lineTo(x+2,y+2);ctx.moveTo(x+2,y-2);ctx.lineTo(x-2,y+2);ctx.stroke()}})};im.src=e.rgb}}
$('example').onchange=()=>{current=Number($('example').value);render()};$('prev').onclick=()=>{current=(current+data.examples.length-1)%data.examples.length;render()};$('next').onclick=()=>{current=(current+1)%data.examples.length;render()};$('overlay').onchange=render;render();</script></html>'''

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--review',type=Path,required=True);a=parser.parse_args();export(a.output,a.review)
