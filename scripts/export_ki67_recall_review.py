"""Saved-result comparison: one feasible seed, all classifiers, explicit tradeoffs."""
import argparse
import base64
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_centers import decode_candidates
from pathology_edge.ki67_evaluation import evaluate_cells,match_points
from pathology_edge.ki67_experiment import read_json,load_sample,sha


def readgz(path):
    with gzip.open(path,'rt') as f:return json.load(f)


def export(root,output):
    root=Path(root);p=read_json(root/'protocol.json');prior=Path(p['prior'])
    selection=read_json(root/'selection.json');feasible=[m for m in selection['models'] if m['selected'] is not None]
    if len(feasible)!=1 or feasible[0]['seed']!=20261117:raise ValueError('This review template requires the recorded single feasible seed')
    seed=20261117;model=feasible[0];arms=['lr','cnn-20261113','cnn-20261114','cnn-20261115']
    new=readgz(root/f'seed-{seed}/internal/predictions.json.gz')
    old=read_json(prior/f'seed-{seed}/internal/predictions.json')
    oldmap={r['image']:r for r in old};newmap={r['image']:r for r in new}
    oldreport=read_json(prior/f'seed-{seed}/internal/results.json');newreport=read_json(root/f'seed-{seed}/internal/results.json')
    om={r['image']:r for r in oldreport['arms']['lr']['per_image']};nm={r['image']:r for r in newreport['arms']['lr']['per_image']}
    gain=max(nm,key=lambda n:(nm[n]['localization']['tp']-om[n]['localization']['tp'],n))
    fp=max(nm,key=lambda n:(nm[n]['localization']['fp']-om[n]['localization']['fp'],n))
    entries=[('test',gain,'테스트 · 찾은 정답 증가가 가장 큰 영상'),('test',fp,'테스트 · FP 증가가 가장 큰 영상')]
    val=readgz(root/f'validation-peaks-{seed}.json.gz');vm={r['image']:r for r in val}
    for stage,label in [('below_threshold','낮은 점수 누락 최다'),('no_peak','근처 피크 없음 최다')]:
        name=max(vm,key=lambda n:(vm[n]['diagnosis']['counts'][stage],n));entries.append(('validation',name,'검증 · '+label))
    manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json')};examples=[]
    for split,name,label in entries:
        rgb,gt,gc=load_sample(p['data_dir'],manifest[name]);buffer=io.BytesIO();Image.fromarray(rgb).save(buffer,format='PNG')
        if split=='test':a,b=oldmap[name],newmap[name];diagnosis=None
        else:
            row=vm[name];diagnosis=row['diagnosis']['counts']
            a=dict(points=decode_candidates(np.asarray(row['points']).reshape(-1,2),np.asarray(row['scores']),**model['old_config'])['points_xy'].tolist(),classes={})
            b=dict(points=decode_candidates(np.asarray(row['points']).reshape(-1,2),np.asarray(row['scores']),**model['selected']['config'])['points_xy'].tolist(),classes={})
        sides=[]
        for r in (a,b):
            pairs=match_points(np.asarray(r['points']).reshape(-1,2),gt,6);hit={j for _,j in pairs}
            metrics={arm:evaluate_cells(np.asarray(r['points']).reshape(-1,2),r['classes'].get(arm,[0]*len(r['points'])),gt,gc) for arm in arms}
            sides.append(dict(points=r['points'],classes=r['classes'],missed=[gt[j].tolist() for j in range(len(gt)) if j not in hit],metrics=metrics))
        examples.append(dict(image=name,split=split,label=label,case_id=manifest[name]['case_id'],image_url='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),gt_points=gt.tolist(),gt_classes=gc.tolist(),diagnosis=diagnosis,a=sides[0],b=sides[1]))
    totals={scope:{side:read_json(base/f'seed-{seed}'/scope/'results.json')['arms'] for side,base in [('a',prior),('b',root)]} for scope in ('internal','external')}
    stages=[]
    for m in selection['models']:
        counts=Counter()
        for row in readgz(root/f"validation-peaks-{m['seed']}.json.gz"):counts.update(row['diagnosis']['counts'])
        stages.append(dict(seed=m['seed'],counts=dict(counts),feasible=m['feasible_trials'],config=None if m['selected'] is None else m['selected']['config']))
    payload=dict(examples=examples,totals=totals,stages=stages,selection=model['selected']['config'])
    template='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge · 누락과 오검출 비교</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f1f4f6;color:#21323d;font:14px system-ui,sans-serif}header,nav,footer,#status,#detail{padding:12px 18px}header{background:#fff;border-bottom:1px solid #b8c7cf}h1{font-size:20px;margin:0 0 7px}p{margin:7px 0;line-height:1.65}small{color:#516675}nav{display:flex;gap:12px;flex-wrap:wrap;align-items:center}select,button{max-width:100%;padding:7px;background:#fff;border:1px solid #9eafb9;border-radius:3px}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:2px;background:#8b9aa4}article{background:#fff;min-width:0}h2{font-size:14px;padding:10px;margin:0}canvas{display:block;width:100%;height:auto;background:#23323c}.metric{min-height:118px;padding:10px;white-space:pre-line;font-variant-numeric:tabular-nums;line-height:1.6}#status{background:#e2ebef}#detail{background:#fff}.scroll{overflow:auto}table{border-collapse:collapse;font-variant-numeric:tabular-nums;white-space:nowrap}td,th{text-align:right;padding:7px 10px;border-bottom:1px solid #c6d1d8}td:first-child,th:first-child{text-align:left}.note{border-left:3px solid #be7636;padding-left:10px}details{margin:12px 0}summary{cursor:pointer;font-weight:600}@media(max-width:760px){main{grid-template-columns:1fr}nav{align-items:stretch}nav label{width:100%}nav select{width:100%}h1{font-size:18px}.metric{min-height:0}}</style>
<header><h1>놓친 세포를 더 찾으면, 오검출은 얼마나 늘어날까요?</h1><p>같은 학습 모델의 점수 기준과 최소 간격만 바꿔 비교합니다. 재현율과 F1·양성률을 함께 확인하세요.</p><small>저장된 연구 결과 · seed20261117 · 재학습 없음 · 검증 자료로 설정 선택 · 기존 테스트/BCData 재평가 · 임상 및 전체 WSI 검증 아님</small></header>
<nav><label>비교 영상 <select id="example"></select></label><label>고정 분류기 <select id="classifier"><option value="cnn-20261113">CNN seed20261113</option><option value="cnn-20261114">CNN seed20261114</option><option value="cnn-20261115">CNN seed20261115</option><option value="lr">색상 통계+LR</option></select></label><label><input id="overlay" type="checkbox" checked> 예측 중심</label><label><input id="missed" type="checkbox" checked> 놓친 정답 ×</label></nav>
<div id="status" role="status">이미지 준비 중</div><main><article><h2>정답 주석 · 원본 좌표</h2><canvas id="truth" width="672" height="672"></canvas><div id="tm" class="metric"></div></article><article><h2>A · 현재 설정 0.10 / 8px</h2><canvas id="before" width="672" height="672"></canvas><div id="am" class="metric"></div></article><article><h2>B · 재현율 조건 선택 0.03 / 4px</h2><canvas id="after" width="672" height="672"></canvas><div id="bm" class="metric"></div></article></main>
<div id="detail"></div><footer><p>중심점: <span style="background:#25333b;color:#ffe600">● 양성 종양</span> · <span style="background:#25333b;color:#00e5ff">● 음성 종양</span> · <span style="background:#25333b;color:#ff43dd">● 양성 비종양</span> · <span style="background:#25333b;color:#5dff54">● 음성 비종양</span>. 빨간 ×는 6px 이내 일대일 대응에서 놓친 정답입니다. 검증 영상의 예측은 위치만 평가했으며 회색 원으로 표시합니다.</p>
<p class="note">B는 기본 모델을 대체하지 않습니다. 세 seed 중 하나만 정해 둔 검증 재현율 조건을 만족했습니다. 재현율은 높아졌지만 FP 증가와 F1 하락을 함께 확인해야 합니다. 양성률 오차 감소만으로 세포 분석 전체가 개선됐다고 판단하지 마세요.</p>
<details><summary>검증 227장 · 누락 원인과 세 seed의 선택 결과</summary><div class="scroll" id="stages"></div><p>피크 없음은 정답 6px 안에 국소 최대점이 없다는 뜻이며 생물학적 원인을 확정하지 않습니다. 점수 미달·거리 억제·일대일 대응 경쟁을 순서대로 구분했습니다. 검증 조건은 기존 LoG의 케이스 평균 재현율과 양성·음성 종양별 위치 재현율 이상입니다. 테스트 조건을 보장하지 않습니다.</p></details>
<details open><summary>전체 결과 · 개별 영상과 구분</summary><div id="totals" class="scroll"></div></details>
<p>F1·재현율은 높을수록, MAE는 낮을수록 좋습니다. 양성률=양성 종양/(양성+음성 종양); 종양 분모0은 계산 불가입니다. 검출 점수는 보정된 확률이 아닙니다. BCData는 종양 주석만 있어 종양 예측만 평가합니다.</p>
<small>영상: <a href="https://huggingface.co/datasets/ds2268/patherea">Patherea Breast-P1 v1.1, Dejan Štepec et al.</a> · <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC4.0</a>. 예측과 주석 표시를 추가한 연구용 파생 자료. 주석 영역 마스크 부재·재사용 데이터·세포 중심 평가라는 한계가 있습니다.</small></footer>
<script>const data=__DATA__,$=x=>document.getElementById(x),colors=['#ffe600','#00e5ff','#ff43dd','#5dff54'];data.examples.forEach((e,i)=>$('example').add(new Option(e.label,i)));
function frac(f){return f.fraction===null?'계산 불가':(f.fraction*100).toFixed(2)+'% ('+f.positive_tumor_cells+'/'+f.tumor_cells+')'}
function metric(side,arm,test){const m=side.metrics[arm],l=m.localization;return '후보 '+side.points.length+' · TP '+l.tp+' / FP '+l.fp+' / FN '+l.fn+'\\n검출 F1 '+l.f1.toFixed(4)+' · 재현율 '+l.recall.toFixed(4)+(test?'\\n세포4-class F1 '+m.macro_f1.toFixed(4)+'\\n예측 양성률 '+frac(m.predicted_fraction):'\\n위치만 평가 · 세포 분류/양성률 미실행')}
function totals(arm){let h='';for(const [scope,sides] of Object.entries(data.totals)){const ext=scope==='external';h+='<p><b>'+(ext?'BCData 기존133장 · 종양 예측만':'내부 테스트407장·10케이스 · 전체 주석')+'</b></p><table><tr><th>방식</th><th>검출F1</th><th>재현율</th><th>세포'+(ext?'2':'4')+'-class F1</th><th>'+(ext?'이미지':'케이스')+' 양성률MAE</th><th>계산 가능</th></tr>';for(const [side,sets] of Object.entries(sides)){const m=sets[arm],key=ext?'image':'case';h+='<tr><td>'+side.toUpperCase()+'</td><td>'+m.localization.f1.toFixed(4)+'</td><td>'+m.localization.recall.toFixed(4)+'</td><td>'+m[ext?'two_class_macro_f1':'macro_f1'].toFixed(4)+'</td><td>'+(m[key+'_ratio_mae_pp']===null?'계산 불가':m[key+'_ratio_mae_pp'].toFixed(2)+'%p')+'</td><td>'+m[key+'_ratio_valid']+'/'+(ext?133:10)+'</td></tr>'}h+='</table>'}return h}
let rev=0;async function render(){const id=++rev,e=data.examples[+$('example').value],arm=$('classifier').value,img=new Image();img.src=e.image_url;await img.decode();if(id!==rev)return;
for(const [canvas,pts,classes,missed] of [['truth',e.gt_points,e.gt_classes,[]],['before',e.a.points,e.a.classes[arm],e.a.missed],['after',e.b.points,e.b.classes[arm],e.b.missed]]){const c=$(canvas).getContext('2d');c.drawImage(img,0,0,672,672);if(canvas==='truth'||$('overlay').checked)pts.forEach(([x,y],i)=>{c.beginPath();c.arc((x+.5)*3,(y+.5)*3,8,0,2*Math.PI);c.strokeStyle=classes?colors[classes[i]]:'#e6edf3';c.lineWidth=2.3;c.stroke()});if($('missed').checked)missed.forEach(([x,y])=>{x=(x+.5)*3;y=(y+.5)*3;c.strokeStyle='#ff3636';c.lineWidth=3;c.beginPath();c.moveTo(x-6,y-6);c.lineTo(x+6,y+6);c.moveTo(x+6,y-6);c.lineTo(x-6,y+6);c.stroke()})}
$('tm').textContent='주석 '+e.gt_points.length+'개\\n정답 양성률 '+frac(e.a.metrics[arm].target_fraction);$('am').textContent=metric(e.a,arm,e.split==='test');$('bm').textContent=metric(e.b,arm,e.split==='test');$('status').textContent='표시 완료 · '+(e.split==='test'?'기존 테스트':'설정 선택에 사용한 검증')+' · '+e.image+' · 같은 원본 좌표';$('classifier').disabled=e.split!=='test';$('detail').textContent=e.diagnosis?'A의 누락: 근처 피크 없음 '+e.diagnosis.no_peak+' / 점수 미달 '+e.diagnosis.below_threshold+' / 거리 억제 '+e.diagnosis.distance_suppressed+' / 대응 경쟁 '+e.diagnosis.assignment_competition:'이 영상은 저장된 비교 결과에서 선택했습니다. 아래 전체 평균과 구분하세요.';$('totals').innerHTML=totals(arm);}
$('stages').innerHTML='<table><tr><th>seed</th><th>찾음</th><th>피크 없음</th><th>점수 미달</th><th>거리 억제</th><th>대응 경쟁</th><th>조건 충족 설정</th></tr>'+data.stages.map(s=>'<tr><td>'+s.seed+'</td>'+['matched','no_peak','below_threshold','distance_suppressed','assignment_competition'].map(k=>'<td>'+s.counts[k]+'</td>').join('')+'<td>'+(s.config?s.config.threshold+' / '+s.config.min_distance+'px':'없음 (27개 모두 미충족)')+'</td></tr>').join('')+'</table>';
for(const id of ['example','classifier','overlay','missed'])$(id).onchange=()=>render().catch(e=>$('status').textContent='오류: '+e.message);render().catch(e=>$('status').textContent='오류: '+e.message);</script></html>'''
    with Path(output).open('x') as f:f.write(template.replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('</','<\\/')))
    metadata=dict(examples=[{k:e[k] for k in ('image','split','label')} for e in examples],selection=payload['selection'],seed=seed,inference_run=False,sha256=sha(output))
    with Path(output).with_suffix('.json').open('x') as f:json.dump(metadata,f,ensure_ascii=False,indent=2)
    return metadata


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(export(a.run,a.output),ensure_ascii=False))
