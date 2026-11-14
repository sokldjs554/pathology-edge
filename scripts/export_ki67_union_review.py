#!/usr/bin/env python3
"""Offline same-coordinate A/B/C0/C review from locked validation evidence."""
import argparse
import base64
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_union_experiment import checked,read_rows
from pathology_edge.ki67_union import retain_candidates
from pathology_edge.ki67_evaluation import match_points,count_metrics
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,load_sample


def panel(points,gt):
    points=np.asarray(points).reshape(-1,2);gt=np.asarray(gt).reshape(-1,2);pairs=match_points(points,gt)
    return dict(points=points.tolist(),matched=[i for i,j in pairs],missed=[j for j in range(len(gt)) if j not in {j for i,j in pairs}],
        counts=count_metrics(len(pairs),len(points)-len(pairs),len(gt)-len(pairs)))


def export(root,output):
    root,output=Path(root),Path(output);p=checked(root,selected=True);selection=read_json(root/'selection.json')
    if not read_json(root/'audit.json')['all_checks_passed']:raise ValueError('Audit required before export')
    manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json')};examples=[];summary=[]
    for m in selection['models']:
        seed=m['seed'];trial=m['selected'] or m['diagnostic'];rows=read_rows(root/f'validation-{seed}.json.gz')
        values=np.load(root/f'validation-scores-{seed}.npz',allow_pickle=False)[f"epoch_{trial['epoch']}"].astype(np.float64)
        offset=0;candidates=[]
        for r in rows:
            points=np.asarray(r['points']).reshape(-1,2);scores=values[offset:offset+len(points)];offset+=len(points)
            c=retain_candidates(points,scores,**trial['config'])['points_xy']
            c0=retain_candidates(points,scores,0,trial['config']['min_distance'])['points_xy']
            panels={name:panel(xy,r['gt_points']) for name,xy in dict(A=r['a_points'],B=points,C0=c0,C=c).items()}
            ac,cc=panels['A']['counts'],panels['C']['counts']
            candidates.append(dict(image=r['image'],case_id=r['case_id'],gt=r['gt_points'],panels=panels,
                delta_errors=cc['fp']+cc['fn']-ac['fp']-ac['fn'],seed=seed,epoch=trial['epoch'],config=trial['config'],eligible=m['selected'] is not None))
        for label,r in [('오류 합 최소 변화',min(candidates,key=lambda v:(v['delta_errors'],v['image']))),('오류 합 최대 변화',max(candidates,key=lambda v:(v['delta_errors'],v['image'])))]:
            rgb,_,_=load_sample(p['data_dir'],manifest[r['image']]);buffer=io.BytesIO();Image.fromarray(rgb).save(buffer,format='PNG')
            examples.append({**r,'selection_reason':label,'rgb':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()})
        summary.append(dict(seed=seed,eligible=m['selected'] is not None,feasible_trials=m['feasible_trials'],A=m['baseline'],B=m['union'],C=trial,diagnostic=m['selected'] is None))
    output.mkdir(parents=True,exist_ok=False)
    payload=dict(summary=summary,examples=examples,source_commit=p['source_commit'],selection_lock_sha256=sha(root/'selection-lock.json'),
        scope=p['scope'],example_selection='For each seed, minimum/maximum image-level (FP+FN) change C-A on validation. Diagnostic checkpoint when no eligible model; neither ranking nor images used for model selection.')
    html=TEMPLATE.replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
    (output/'index.html').write_text(html)
    fresh_json(output/'review-manifest.json',dict(html_sha256=sha(output/'index.html'),examples=[{k:v for k,v in r.items() if k not in ('rgb','panels','gt')} for r in examples],selection_lock_sha256=payload['selection_lock_sha256'],source_commit=p['source_commit']))

TEMPLATE='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge · 후보 통합 검토</title>
<style>*{box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif;background:#f4f6f7;color:#23333c}header{background:#fff;border-bottom:1px solid #b8c5ca;padding:15px 22px}h1{font-size:20px;margin:0 0 5px}p{line-height:1.5;margin:6px 0}main{padding:14px 22px;max-width:1600px;margin:auto}button,select{font:inherit;padding:8px;max-width:100%;border:1px solid #8da1aa;background:#fff;border-radius:3px}button{cursor:pointer}.notice{border-left:4px solid #aa6530;background:#fff5e7;padding:10px 14px;margin:10px 0}.tablewrap{overflow:auto}table{border-collapse:collapse;background:#fff;width:100%;font-variant-numeric:tabular-nums}td,th{padding:8px;border-bottom:1px solid #d5dfe3;text-align:left;white-space:nowrap}th{font-size:12px;color:#4c606b}nav{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:15px 0}nav label{min-width:0;max-width:100%}.panels{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.panel{background:#fff;border:1px solid #bfccd2}.title,.counts{padding:9px}.title{background:#233942;color:#fff;min-height:50px}.counts{font-size:13px;line-height:1.6}canvas{width:100%;display:block;image-rendering:auto}.legend{display:flex;flex-wrap:wrap;gap:16px;margin:10px 0}.matched{color:#007bba}.fp{color:#c62664}.gt{color:#976600}details{margin:15px 0}code{overflow-wrap:anywhere;font-size:11px}footer{font-size:12px;color:#526772;padding:20px 0}@media(max-width:900px){.panels{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:480px){main,header{padding:12px}.panels{grid-template-columns:1fr}h1{font-size:18px}}</style>
<header><h1>PathologyEdge · 후보 통합 + 이진 CNN 검토</h1><p>검출 후보를 더 모은 뒤, 놓친 세포와 잘못 남긴 후보를 함께 줄였는지 확인합니다.</p></header>
<main><div id="outcome" class="notice"></div><p>아래 표는 <strong>검증 227장 · 4개 케이스</strong>의 위치 검출 결과입니다. F1·재현율은 높을수록 좋고, FP·FN은 낮을수록 좋습니다.</p>
<div class="tablewrap"><table><thead><tr><th>seed</th><th>선택 조건</th><th>A FP / FN</th><th>C FP / FN</th><th>케이스 평균 F1 A → C</th><th>케이스 평균 재현율 A → C</th><th>양성 / 음성 종양 위치 재현율 C</th></tr></thead><tbody id="summary"></tbody></table></div>
<p id="context"></p><nav><label>실제 사례 <select id="example" aria-label="실제 사례"></select></label><button id="prev">이전</button><button id="next">다음</button><label><input id="overlay" type="checkbox" checked> 후보·정답 표시</label></nav>
<p id="case"></p><div class="legend"><span class="matched">● 정답과 일대일 대응한 후보</span><span class="fp">● FP: 대응하지 않은 후보</span><span class="gt">○ 정답 중심 · × FN</span></div>
<div class="panels" id="panels"></div>
<details><summary>비교 방법과 용어</summary><p>A: 기존 학습 검출기. B: 느슨한 학습 후보 + LoG 후보, 같은 좌표만 통합. C0: CNN 점수순 거리 억제, 임계값 0. C: 같은 점수와 거리 기준에 선택 임계값 적용. B는 후보 공급 확인용으로 억제 정책이 동일한 비교가 아닙니다.</p><p>FP는 정답과 대응하지 않은 후보, FN은 놓친 정답입니다. 6px 이내에서 클래스와 무관하게 일대일 대응합니다. 재현율은 TP/(TP+FN), F1은 2TP/(2TP+FP+FN)입니다. 표의 F1·재현율은 케이스별 평균, FP·FN은 227장 합계입니다. 양성/음성 종양 재현율은 실제 종양 클래스별 위치 검출 비율이며 분류 정확도가 아닙니다.</p><p>사례는 seed별 C−A의 FP+FN 변화가 가장 작고 큰 검증 이미지를 고릅니다. 후보 원은 핵 경계가 아닙니다. 네 화면의 영상과 좌표는 같습니다.</p></details>
<details open><summary>해석 범위</summary><p>세 seed는 기존 검출기 seed와 새 CNN seed를 짝지은 비교입니다. 검출기·4분류기를 다시 학습하지 않았습니다. 주석에서 멀리 떨어진 후보를 음성 대용으로 사용했으므로 실제 세포가 음성 학습 자료에 포함됐을 가능성이 있습니다. 점수는 보정된 임상 확률이 아닙니다.</p><p>기존에 사용한 검증 데이터의 탐색적 실험입니다. 조건을 통과하지 못한 모델의 화면은 실패 분석용입니다. 새로운 외부 일반화, 임상 검증, WSI 전체 검증을 의미하지 않습니다.</p></details><footer>연구·교육용 · 저장 결과 열람 · 화면에서 실시간 추론하지 않음<br><code id="provenance"></code></footer></main>
<script>const data=__DATA__;const $=id=>document.getElementById(id);let current=0,renderVersion=0;const fmt=v=>v.toFixed(4);const names={A:'A · 기존 학습 검출기',B:'B · 후보 통합만',C0:'C0 · 점수순 거리 억제',C:'C · CNN 임계값 + 거리 억제'};const passed=data.summary.filter(x=>x.eligible).length;
$('outcome').textContent=`세 seed 중 ${passed}/3 조건 충족. `+(passed===0?'대체 모델을 채택하지 않았습니다. C는 검증 F1이 가장 높았던 진단용 모델입니다. 테스트·외부 재평가는 실행하지 않았습니다.':'통과 모델만 후속 재평가 대상으로 잠갔습니다. 기본 모델은 변경하지 않았습니다.');
$('context').textContent='조건: A보다 FP·FN 각각 악화 없음(하나는 감소), 기존 LoG 재현율 하한 유지, 각 케이스 재현율 ≥ A의 90%.';
$('summary').innerHTML=data.summary.map(r=>`<tr><td>${r.seed}</td><td>${r.eligible?'충족':'미충족 · 진단용'}</td><td>${r.A.localization.fp} / ${r.A.localization.fn}</td><td>${r.C.localization.fp} / ${r.C.localization.fn}</td><td>${fmt(r.A.case_macro_f1)} → ${fmt(r.C.case_macro_f1)}</td><td>${fmt(r.A.case_macro_recall)} → ${fmt(r.C.case_macro_recall)}</td><td>${r.C.tumor_recalls.map(fmt).join(' / ')}</td></tr>`).join('');
data.examples.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${e.seed} · ${e.selection_reason} · ${e.image}`;$('example').append(o)});
$('provenance').textContent=`source ${data.source_commit} · selection SHA256 ${data.selection_lock_sha256}`;
function render(){const version=++renderVersion,e=data.examples[current];$('example').value=current;$('case').textContent=`${e.image} · ${e.case_id} · 같은 224×224px 위치 · epoch ${e.epoch} · 임계값 ${e.config.threshold}, 거리 ${e.config.min_distance}px · ${e.eligible?'조건 충족':'진단용 · 선택 조건 미충족'} · C−A 오류 합 ${e.delta_errors>=0?'+':''}${e.delta_errors}`;$('panels').innerHTML='';for(const key of ['A','B','C0','C']){const p=e.panels[key],section=document.createElement('section');section.className='panel';section.innerHTML=`<div class="title">${names[key]}</div><canvas width="672" height="672" aria-label="${key} 후보 비교"></canvas><div class="counts">후보 ${p.points.length} · TP ${p.counts.tp} · FP ${p.counts.fp} · FN ${p.counts.fn}<br>이 이미지 F1 ${fmt(p.counts.f1)} · 재현율 ${fmt(p.counts.recall)}</div>`;$('panels').append(section);const canvas=section.querySelector('canvas'),ctx=canvas.getContext('2d'),im=new Image();im.onload=()=>{if(version!==renderVersion)return;ctx.drawImage(im,0,0,672,672);if(!$('overlay').checked)return;ctx.scale(3,3);ctx.lineWidth=.7;const matched=new Set(p.matched);p.points.forEach(([x,y],i)=>{ctx.fillStyle=matched.has(i)?'#007bba':'#c62664';ctx.beginPath();ctx.arc(x,y,1.4,0,Math.PI*2);ctx.fill()});const missed=new Set(p.missed);e.gt.forEach(([x,y],i)=>{ctx.strokeStyle='#ffd057';ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.stroke();if(missed.has(i)){ctx.beginPath();ctx.moveTo(x-2,y-2);ctx.lineTo(x+2,y+2);ctx.moveTo(x+2,y-2);ctx.lineTo(x-2,y+2);ctx.stroke()}})};im.src=e.rgb}}
$('example').onchange=()=>{current=Number($('example').value);render()};$('prev').onclick=()=>{current=(current+data.examples.length-1)%data.examples.length;render()};$('next').onclick=()=>{current=(current+1)%data.examples.length;render()};$('overlay').onchange=render;render();</script></html>'''

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--review',type=Path,required=True)
    a=parser.parse_args();export(a.output,a.review)
