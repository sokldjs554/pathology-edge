#!/usr/bin/env python3
"""Portable review of six prespecified external examples; no live inference."""
import argparse
import base64
import json
from pathlib import Path
import numpy as np
from pathology_edge.ki67_experiment import read_json,sha
from pathology_edge.ki67_union_experiment import read_rows,SEEDS
from pathology_edge.ki67_transfer_evaluation import classifier_for_seed,validate_audited
from pathology_edge.ki67_evaluation import match_points


def display_record(row,score,name):
    return dict(points=row['points'],classes=[c%2 for c in row['classes'][name]],
                pairs=match_points(np.asarray(row['points']).reshape(-1,2),np.asarray(row['gt_points']).reshape(-1,2),6),scores=score)


def build(root,output):
    root,output=Path(root),Path(output)
    validate_audited(root)
    summary=read_json(root/'evaluation/deepliif/summary.json')
    if summary['new_inference_images']!=597:raise ValueError('Complete fixed external evaluation required')
    refs=read_rows(root/'evaluation/deepliif/input-audit.json.gz');records={}
    for seed in SEEDS:
        folder=root/'evaluation/deepliif'/str(seed);records[seed]={a:read_rows(folder/(a+'.json.gz')) for a in ('A','B')}
        records[seed]['scores']=read_rows(folder/'scores.json.gz')[0]
    examples=[]
    for index in (0,100,200,300,400,596):
        ref=refs[index];item=dict(index=index,image=ref['image'],rgb='data:image/png;base64,'+base64.b64encode((root/f'external-input-review/{index:03d}.png').read_bytes()).decode(),gt_points=ref['gt_points'],gt_classes=ref['gt_classes'],seeds={})
        for seed in SEEDS:
            item['seeds'][str(seed)]={}
            for arm in ('A','B'):
                row=records[seed][arm][index];scores=records[seed]['scores'][arm]['6']['per_image'][index]
                if row['image']!=ref['image'] or scores['image']!=ref['image']:raise ValueError('Example identity differs')
                item['seeds'][str(seed)][arm]=display_record(row,scores,classifier_for_seed(seed))
        examples.append(item)
    payload=json.dumps(dict(examples=examples,summary=summary,seeds=list(SEEDS),audit_sha256=sha(root/'audit.json')),separators=(',',':')).replace('<','\\u003c')
    html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge — 마지막 외부 비교 검토</title>
<style>body{margin:0;background:#f5f6f7;color:#172a38;font:15px system-ui,sans-serif}header,main{padding:16px 24px}header{background:white;border-bottom:1px solid #c7d0d6}h1{font-size:21px;margin:0 0 8px}p{line-height:1.6;margin:8px 0}.controls{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:14px 0}select{padding:7px;max-width:95vw}button{padding:7px}.panels{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0;min-width:0}figcaption{font-weight:600;padding:8px 0}svg{width:100%;height:auto;background:#ddd;border:1px solid #9baab5}.metrics{font-variant-numeric:tabular-nums;line-height:1.7;margin-top:8px}.note{font-size:13px;color:#415361}.status{font-weight:600}.reference{fill:none;stroke:#b9ff49;stroke-width:1.5}.link{stroke:#fff;stroke-width:1;opacity:.8}.positive{fill:none;stroke:#ff483c;stroke-width:1.5}.negative{fill:none;stroke:#12baff;stroke-width:1.5}code{overflow-wrap:anywhere}@media(max-width:760px){header,main{padding:12px}.panels{grid-template-columns:1fr}h1{font-size:19px}}</style>
<header><h1>PathologyEdge · 마지막 외부 비교</h1><p>공개 DeepLIIF 영상에서 기존 검출기 A와 사전학습 특징을 사용한 검출기 B를 비교합니다. 두 방식은 같은 고정 분류기를 사용합니다.</p><p class="note">사전 계산 결과 · 실제 새 추론과 주석 대조 완료 · 임상 Ki-67 지수 / WSI 전체 검증 아님. B는 내부 채택 기준 미달이어도 공개하는 진단 모델일 수 있습니다.</p></header>
<main><div class="status" id="status"></div><p class="note">모델 결과를 보기 전에 정한 순번 0·100·200·300·400·596의 여섯 예시입니다. 좋은 사례만 고른 화면이 아니며 전체 597장 결과를 대신하지 않습니다.</p>
<div class="controls"><label>예시 <select id="example"></select></label><label>학습 seed <select id="seed"></select></label><label><input id="overlay" type="checkbox" checked> 중심 표시</label><label><input id="reference" type="checkbox"> A/B에 참조 중심 겹치기</label><label><input id="links" type="checkbox"> 6px 내 대응 연결</label></div>
<p id="identity"></p><div class="panels"><figure><figcaption>제공 마스크에서 유도한 참조 중심</figcaption><svg id="GT" viewBox="0 0 512 512"></svg><div class="metrics" id="GTmetrics"></div></figure><figure><figcaption>A · 기존 중심 검출기</figcaption><svg id="A" viewBox="0 0 512 512"></svg><div class="metrics" id="Ametrics"></div></figure><figure><figcaption>B · 사전학습 특징 + 학습한 decoder</figcaption><svg id="B" viewBox="0 0 512 512"></svg><div class="metrics" id="Bmetrics"></div></figure></div>
<p class="note">빨강: Ki-67 양성 · 파랑: 음성 · 연두 십자: 참조 중심. 흰 선은 6px 이내 일대일 위치 대응이며, 선이 연결되어도 양음성 분류가 맞았다는 뜻은 아닙니다. FP는 대응하지 않는 예측, FN은 놓친 참조입니다.</p>
<p class="note">이 화면의 양성률은 종양 여부를 구분하지 않은 전체 예측 세포 중 양성 세포 비율입니다. 원래 네 클래스의 종양·비종양 예측을 양음성 두 클래스로 합쳤습니다. 점수는 높을수록 좋지만 양성률 자체는 높다고 좋은 것이 아닙니다. 참조 중심은 분할 마스크의 무게중심으로 유도했으며 전문가 중심점 주석과 같다고 가정하지 않습니다.</p>
<p class="note">기관·환자 독립성과 물리 해상도(MPP)는 확인되지 않았습니다. 좌표는 원본 512×512 픽셀 기준입니다. 확대된 화면으로 정답 주석의 완전성이나 임상적 정확도를 확정할 수 없습니다.</p>
<p class="note">출처: Ghahremani et al., DeepLIIF, Nature Machine Intelligence (2022), DOI 10.1038/s42256-022-00471-x · Zenodo 4751737 · CC BY 4.0. 원영상 픽셀은 변경하지 않았습니다.</p><p class="note">지표 감사 SHA-256: <code id="audit"></code></p></main>
<script id="data" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent),byId=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
for(let i=0;i<data.examples.length;i++){const o=new Option(data.examples[i].index+' · '+data.examples[i].image.split('/').pop(),i);byId('example').add(o)}
for(const seed of data.seeds)byId('seed').add(new Option(seed,seed));
byId('status').textContent=`전체 597장 · 3개 seed · 내부 채택 ${data.summary.adopted_seeds}/3 · 사전 고정한 외부 종합 기준 통과 ${data.summary.passes}/3`;
byId('audit').textContent=data.audit_sha256;
function node(tag,attrs){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n}
function circle(svg,p,c){svg.append(node('circle',{cx:p[0],cy:p[1],r:4,class:c===0?'positive':'negative'}))}
function percent(v){return v===null||!Number.isFinite(v)?'— (분모 없음)':(100*v).toFixed(2)+'%'}
function render(){const e=data.examples[Number(byId('example').value)],seed=byId('seed').value,eligible=data.summary.seeds.find(r=>String(r.seed)===seed).eligible;byId('identity').textContent=e.image+' · 동일한 원영상 위치 · seed '+seed+' · '+(eligible?'내부 채택 기준 통과':'내부 채택 미달: 진단 모델');
for(const arm of ['GT','A','B']){const svg=byId(arm);svg.replaceChildren(node('image',{href:e.rgb,x:0,y:0,width:512,height:512}));
if(arm==='GT'){if(byId('overlay').checked)e.gt_points.forEach((p,i)=>circle(svg,p,e.gt_classes[i]));byId('GTmetrics').textContent=`참조 세포 ${e.gt_points.length}개 · 양성률 ${percent(e.gt_classes.filter(c=>c===0).length/e.gt_classes.length)}`;continue}
const r=e.seeds[seed][arm],s=r.scores;if(byId('links').checked)for(const [i,j] of r.pairs)svg.append(node('line',{x1:r.points[i][0],y1:r.points[i][1],x2:e.gt_points[j][0],y2:e.gt_points[j][1],class:'link'}));
if(byId('reference').checked)for(const [x,y] of e.gt_points)svg.append(node('path',{d:`M${x-3} ${y}h6 M${x} ${y-3}v6`,class:'reference'}));
if(byId('overlay').checked)r.points.forEach((p,i)=>circle(svg,p,r.classes[i]));
byId(arm+'metrics').textContent=`검출 ${s.pred_cells}개 · TP ${s.localization.tp} / FP ${s.localization.fp} / FN ${s.localization.fn} · 검출 F1 ${s.localization.f1.toFixed(3)} · 검출+양음성 F1 ${s.two_class_macro_f1.toFixed(3)} · 예측 양성률 ${percent(s.pred_fraction)}`;
}}
for(const id of ['example','seed','overlay','reference','links'])byId(id).addEventListener('change',render);render();
</script></html>'''.replace('PAYLOAD',payload)
    with output.open('x') as f:f.write(html)
    print(json.dumps(dict(path=str(output),bytes=output.stat().st_size,sha256=sha(output))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.run,a.output)
