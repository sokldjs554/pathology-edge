#!/usr/bin/env python3
"""Audited normalized-detector comparison, separate from the deployed model."""
import argparse,base64,io,json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_ki67_union_review import panel
from pathology_edge.ki67_normalized_experiment import checked,primary_models,job_name
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_union import retain_candidates
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,load_sample


def export(root,output):
    root,output=Path(root),Path(output);p=checked(root,selected=True);audit=read_json(root/'audit.json')
    if not audit['all_checks_passed'] or audit['selection_lock_sha256']!=sha(root/'selection-lock.json') or audit['classifier_lock_sha256']!=sha(root/'classifier-lock.json'):raise ValueError('Matching completed audit required')
    selection=read_json(root/'selection.json');models=primary_models(selection);manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'};examples=[];summary=[]
    for m in models:
        seed=m['seed'];folder=root/job_name(16,seed);trial=m['selected'] or m['diagnostic'];epoch=trial['epoch'];saved=np.load(folder/'validation-peaks.npz',allow_pickle=False);rows=read_rows(folder/'validation.json.gz');candidates=[]
        for i,r in enumerate(rows):
            lo,hi=saved[f'offsets_{epoch}'][i:i+2];xy=retain_candidates(saved[f'points_{epoch}'][lo:hi],saved[f'scores_{epoch}'][lo:hi].astype(np.float64),**trial['config'])['points_xy']
            panels=dict(A=panel(r['a_points'],r['gt_points']),B=panel(xy,r['gt_points']));a,b=panels['A']['counts'],panels['B']['counts']
            candidates.append(dict(seed=seed,image=r['image'],case_id=r['case_id'],gt=r['gt_points'],panels=panels,epoch=epoch,config=trial['config'],eligible=m['selected'] is not None,delta_errors=b['fp']+b['fn']-a['fp']-a['fn']))
        for label,row in [('오류 합 변화 최소',min(candidates,key=lambda r:(r['delta_errors'],r['image']))),('오류 합 변화 최대',max(candidates,key=lambda r:(r['delta_errors'],r['image'])))]:
            rgb,_,_=load_sample(p['data_dir'],manifest[row['image']]);buffer=io.BytesIO();Image.fromarray(rgb).save(buffer,format='PNG')
            examples.append({**row,'selection_reason':label,'rgb':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()})
        summary.append(dict(seed=seed,eligible=m['selected'] is not None,A=m['baseline'],B=trial,feasible_trials=m['feasible_trials'],parameters=m['parameter_count']))
    ablation=[dict(width=m['width'],seed=m['seed'],eligible=m['selected'] is not None,parameters=m['parameter_count'],feasible_trials=m['feasible_trials'],best_f1=m['diagnostic']['case_macro_f1']) for m in selection['models']]
    data=dict(summary=summary,ablation=ablation,examples=examples,stability=read_json(root/'stability.json'),source_commit=p['source_commit'],selection_sha256=sha(root/'selection-lock.json'),audit_sha256=sha(root/'audit.json'))
    output.mkdir(parents=True,exist_ok=False);(output/'index.html').write_text(TEMPLATE.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')))
    fresh_json(output/'review-manifest.json',dict(html_sha256=sha(output/'index.html'),source_commit=p['source_commit'],audit_sha256=data['audit_sha256'],examples=[{k:v for k,v in r.items() if k not in ('rgb','gt','panels')} for r in examples]))


TEMPLATE='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge · 정규화 검출기 검토</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f4f6f7;color:#243b46;font:14px system-ui,sans-serif}header{background:white;border-bottom:1px solid #bccad1;padding:16px 22px}h1{font-size:20px;margin:0 0 8px}main{max-width:1450px;margin:auto;padding:16px 22px}p{line-height:1.65}.notice{border-left:4px solid #9e6c2b;padding:12px;background:#fff4df}.scroll{overflow:auto}table{width:100%;background:white;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #d2dde3;text-align:left;white-space:nowrap;font-variant-numeric:tabular-nums}th{font-size:12px}nav,.legend{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:15px 0}nav label{max-width:100%;min-width:0}select,button{max-width:100%;padding:9px;font:inherit;background:white;border:1px solid #9aacb6;border-radius:3px}button{cursor:pointer}.panels{display:grid;grid-template-columns:1fr 1fr;gap:12px}.panel{border:1px solid #bbc9d0;background:white}.title{background:#2c424b;color:white;padding:10px}.counts{padding:10px;line-height:1.7}canvas{width:100%;display:block}details{margin:17px 0}footer{margin-top:24px;font-size:12px;line-height:1.8}code{overflow-wrap:anywhere}@media(max-width:650px){header,main{padding:12px}.panels{grid-template-columns:1fr}h1{font-size:18px}}</style>
<header><h1>PathologyEdge · 정규화 검출기 검토</h1><div>잘못 찾은 후보(FP)와 놓친 세포(FN)를 함께 줄일 수 있는지, 같은 영상에서 비교합니다.</div></header>
<main><p id="outcome" class="notice"></p><p><strong>검증227장·4케이스</strong> · A: 기존 소형 검출기 · B: GroupNorm을 넣은 width16 검출기. FP·FN은 이미지 합계, F1·재현율은 케이스별 평균입니다. F1·재현율은 높을수록, FP·FN은 낮을수록 좋습니다.</p>
<div class="scroll"><table><thead><tr><th>seed</th><th>채택 조건</th><th>epoch / 임계값 / 거리</th><th>FP A → B</th><th>FN A → B</th><th>F1 A → B</th><th>재현율 A → B</th><th>B 종양+ / 종양− 위치 재현율</th></tr></thead><tbody id="summary"></tbody></table></div>
<p>채택 조건: FP·FN 각각 악화 없음(하나는 감소), 기존 재현율 하한 유지(케이스 평균0.4798·종양+0.5590·종양−0.3398), 각 케이스 재현율 ≥ A의90%. 모두 충족해야 통과입니다.</p>
<nav><label>실제 사례 <select id="example" aria-label="실제 사례"></select></label><button id="prev">이전</button><button id="next">다음</button><label><input type="checkbox" id="overlay" checked> 후보·정답 표시</label></nav><p id="case"></p>
<div class="legend"><span style="color:#007bba">● 정답과 일대일 대응</span><span style="color:#c62664">● FP: 대응하지 않은 후보</span><span style="color:#8d5b00">○ 정답 중심 · × FN</span></div><div class="panels" id="panels"></div>
<details><summary>작은 모델 비교군과 실험 범위</summary><p>주 비교 모델은 결과를 보기 전에 width16으로 정했습니다. width4는 별도 비교군이며 결과가 좋더라도 주 모델 대신 선택하지 않습니다. 두 새 모델 모두 처음부터24epoch를 학습했습니다. A는 기존16epoch 모델이므로 구조·정규화만의 인과 효과를 분리한 실험은 아닙니다.</p><div class="scroll"><table><thead><tr><th>너비</th><th>seed</th><th>파라미터</th><th>조건 통과 설정 수</th><th>최고 검증 F1(진단)</th></tr></thead><tbody id="ablation"></tbody></table></div></details>
<details open><summary>자동 Ki-67와 외부 평가의 연결</summary><p id="stability"></p><p>검출 조건을 통과한 주 모델만 실제 예측 위치에서 세포를 분류합니다. 세포 분류 F1 상승과 같은 케이스의 양성률 오차 감소를 별도로 확인하며, 양성률만 좋아졌다는 이유로 전체 분석 성공이라 판단하지 않습니다. 기존 Patherea 테스트·BCData는 재평가입니다. 새 DeepLIIF는 폐·방광의 전체 세포 양성·음성 비교로, 종양세포 전용 Ki-67 지수·임상·전체 WSI 검증과 다릅니다. 이 화면은 위 검증 자료의 검출 사례를 보여줍니다.</p></details>
<details><summary>사례 선택·표시 기준과 한계</summary><p>각 seed에서 이미지별 (FP+FN)의 B−A 변화가 최소·최대인 실제 사례를 선택했습니다. 사후 설명용이며 평균을 대표하지 않습니다. 같은224×224px 좌표에서 정답과6px 이내 일대일 대응합니다. 후보 원은 핵의 윤곽이 아닙니다. 전체 조건을 통과한 설정이 없으면 최고 검증 F1의 <strong>진단용 미채택 모델</strong>을 표시합니다.</p><p>검증 자료는 반복 사용됐고, 점수는 보정된 임상 확률이 아닙니다. 표시를 끄면 원영상만 보이며 계산된 수치는 바뀌지 않습니다. 새로 학습된 모델은 기본 배포 모델로 교체되지 않았습니다.</p></details>
<footer>연구·교육용 · 저장된 결과 열람 · 화면에서 실시간 추론하지 않음<br>Patherea Breast-P1: <a href="https://huggingface.co/datasets/ds2268/patherea">Štepec et al.</a>, CC BY-NC4.0 · 예측/대응 표시 추가<br><code id="provenance"></code></footer></main>
<script>const data=__DATA__, $=id=>document.getElementById(id),fmt=x=>x.toFixed(4);let current=0,version=0;const n=data.summary.filter(r=>r.eligible).length;
$('outcome').textContent=`검증 채택 조건 ${n}/3 seed 충족. `+(n?'통과 모델만 후속 평가 대상으로 잠갔습니다. 검증 통과와 실제 테스트 성공은 구분합니다.':'새 모델을 채택하지 않았고 테스트·외부 새 추론을 실행하지 않았습니다. B는 실패 분석용 진단 모델입니다.');
$('summary').innerHTML=data.summary.map(r=>`<tr><td>${r.seed}</td><td>${r.eligible?'충족':'미충족 · 진단용'}</td><td>${r.B.epoch} / ${r.B.config.threshold} / ${r.B.config.min_distance}px</td><td>${r.A.localization.fp} → ${r.B.localization.fp}</td><td>${r.A.localization.fn} → ${r.B.localization.fn}</td><td>${fmt(r.A.case_macro_f1)} → ${fmt(r.B.case_macro_f1)}</td><td>${fmt(r.A.case_macro_recall)} → ${fmt(r.B.case_macro_recall)}</td><td>${r.B.tumor_recalls.map(fmt).join(' / ')}</td></tr>`).join('');
$('ablation').innerHTML=data.ablation.map(r=>`<tr><td>${r.width}${r.width===16?' · 주 모델':' · 비교군'}</td><td>${r.seed}</td><td>${r.parameters}</td><td>${r.feasible_trials}/864</td><td>${fmt(r.best_f1)}</td></tr>`).join('');
$('stability').textContent=n?`기존 테스트 검출 안정성 ${data.stability.test_passes}/3 · 자동 분류+양성률 조건 ${data.stability.pipeline_passes}/3. 미채택 seed도 분모3에 포함합니다.`:'적격 모델이 없어 후속 테스트·외부 추론을 보류했습니다. 성공 증거0/3은 테스트를 세 번 실행해 실패했다는 뜻이 아닙니다.';
$('provenance').textContent=`training source ${data.source_commit} · selection SHA256 ${data.selection_sha256} · audit SHA256 ${data.audit_sha256}`;
data.examples.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${e.seed} · ${e.selection_reason} · ${e.image}`;$('example').append(o)});
function render(){const token=++version,e=data.examples[current];$('example').value=current;$('case').textContent=`${e.image} · ${e.case_id} · 같은224×224px · epoch${e.epoch} · ${e.eligible?'선택 조건 충족':'미채택 · 진단용'} · 오류 합 B−A ${e.delta_errors>=0?'+':''}${e.delta_errors}`;$('panels').innerHTML='';for(const key of ['A','B']){const p=e.panels[key],section=document.createElement('section');section.className='panel';section.innerHTML=`<div class="title">${key==='A'?'A · 기존 검출기':'B · 정규화 검출기'}</div><canvas width="672" height="672" aria-label="${key} 검출 비교"></canvas><div class="counts">후보 ${p.points.length} · TP ${p.counts.tp} · FP ${p.counts.fp} · FN ${p.counts.fn}<br>이 이미지 F1 ${fmt(p.counts.f1)} · 재현율 ${fmt(p.counts.recall)}</div>`;$('panels').append(section);const ctx=section.querySelector('canvas').getContext('2d'),im=new Image();im.onload=()=>{if(token!==version)return;ctx.drawImage(im,0,0,672,672);if(!$('overlay').checked)return;ctx.scale(3,3);ctx.lineWidth=.7;const hit=new Set(p.matched),missed=new Set(p.missed);p.points.forEach(([x,y],i)=>{ctx.fillStyle=hit.has(i)?'#007bba':'#c62664';ctx.beginPath();ctx.arc(x,y,1.4,0,Math.PI*2);ctx.fill()});e.gt.forEach(([x,y],i)=>{ctx.strokeStyle='#ffd057';ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.stroke();if(missed.has(i)){ctx.beginPath();ctx.moveTo(x-2,y-2);ctx.lineTo(x+2,y+2);ctx.moveTo(x+2,y-2);ctx.lineTo(x-2,y+2);ctx.stroke()}})};im.src=e.rgb}}
$('example').onchange=()=>{current=Number($('example').value);render()};$('prev').onclick=()=>{current=(current+data.examples.length-1)%data.examples.length;render()};$('next').onclick=()=>{current=(current+1)%data.examples.length;render()};$('overlay').onchange=render;render();</script></html>'''


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--review',required=True,type=Path);a=p.parse_args();export(a.output,a.review)
