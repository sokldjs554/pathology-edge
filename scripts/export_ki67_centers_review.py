"""Actual native-coordinate center predictions and heatmaps, with fixed-seed case selection."""
import argparse
import base64
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from pathology_edge.ki67_center_experiment import checked,loaded_detectors
from pathology_edge.ki67_centers import predict_centers


def export(run,output):
    run,p=checked(run);detectors=loaded_detectors(run);torch.set_num_threads(p['torch_threads'])
    read=lambda f:json.loads(Path(f).read_text())
    old=read(Path(p['parent'])/'results.json')['arms']
    baseline={r['image']:r for r in read(Path(p['parent'])/'predictions.json')}
    basemetrics={a:{r['image']:r for r in v['per_image']} for a,v in old.items()}
    records={};reports={};external={}
    for seed in detectors:
        folder=run/f'seed-{seed}'
        records[str(seed)]={r['image']:r for r in read(folder/'internal/predictions.json')}
        reports[str(seed)]=read(folder/'internal/results.json')['arms']
        external[str(seed)]=read(folder/'external/results.json')['arms']
    metrics={seed:{a:{r['image']:r for r in v['per_image']} for a,v in arms.items()} for seed,arms in reports.items()}
    first=str(p['seeds'][0]);arm='cnn-20261113'
    delta=lambda n:metrics[first][arm][n]['localization']['f1']-basemetrics[arm][n]['localization']['f1']
    ordered=sorted(baseline,key=lambda n:(delta(n),n))
    examples=[];replays=[]
    for name,reason in [('case_0011_region_0_patch_1_O.png','앞서 확인한107개 후보 사례'),(ordered[0],'첫 검출 seed의 검출F1 최대 하락'),(ordered[-1],'첫 검출 seed의 검출F1 최대 상승')]:
        image_path=Path(p['data_dir'])/'images'/name;rgb=np.asarray(Image.open(image_path).convert('RGB'))
        row=baseline[name];models={}
        for seed,(model,config) in detectors.items():
            actual=predict_centers(rgb,model,config);saved=records[str(seed)][name]
            if actual['points_xy'].tolist()!=saved['points'] or not np.array_equal(actual['scores'],np.asarray(saved['scores'])):
                raise ValueError('Heatmap replay differs from stored center predictions')
            heat=actual['probability_map'];rgba=np.zeros((*heat.shape,4),dtype=np.uint8)
            rgba[:,:,0]=255;rgba[:,:,1]=70;rgba[:,:,2]=20
            rgba[:,:,3]=np.rint(np.where(heat>=.05,heat*.7,0)*255).astype(np.uint8)
            buffer=io.BytesIO();Image.fromarray(rgba).save(buffer,format='PNG')
            models[str(seed)]=dict(points=saved['points'],classes=saved['classes'],config=config,
                heatmap_url='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),
                metrics={a:v[name] for a,v in metrics[str(seed)].items()})
            replays.append(dict(image=name,seed=seed,coordinates_and_scores_exact=True))
        examples.append(dict(image=name,reason=reason,delta_f1=delta(name),
            image_url='data:image/png;base64,'+base64.b64encode(image_path.read_bytes()).decode(),
            gt_points=row['gt_points'],gt_classes=row['gt_classes'],baseline=dict(points=row['points'],classes=row['classes'],metrics={a:v[name] for a,v in basemetrics.items()}),models=models))
    def concise(reports,ext=False):
        keys=('localization','two_class_macro_f1','image_ratio_mae_pp','image_ratio_valid') if ext else ('localization','macro_f1','case_ratio_mae_pp','case_ratio_valid')
        return {a:{k:v[k] for k in keys} for a,v in reports.items()}
    totals=dict(internal={'baseline':concise(old),**{s:concise(v) for s,v in reports.items()}},
                external={'baseline':concise(read(Path(p['external'])/'results.json')['arms'],True),**{s:concise(v,True) for s,v in external.items()}})
    template='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PathologyEdge · 학습한 세포 중심</title>
<style>*{box-sizing:border-box}body{margin:0;background:#172128;color:#edf3f6;font:15px/1.55 system-ui}header,nav,footer{padding:12px 18px;border-bottom:1px solid #52616a}h1{margin:0;font-size:19px}p{margin:7px 0}small{color:#bdccd4}nav{display:flex;gap:12px;flex-wrap:wrap}label{min-width:0}select{padding:7px;max-width:100%;background:#263943;color:white}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:#52616a}article{min-width:0;background:#20303a;padding:12px}h2{font-size:16px;margin:0 0 8px}canvas{width:100%;height:auto;display:block}.metric{white-space:pre-line;overflow-wrap:anywhere;padding-top:8px;min-height:110px}#status,#source{padding:5px 18px;overflow-wrap:anywhere}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:8px;border-bottom:1px solid #52616a;text-align:left}summary{cursor:pointer}a{color:#9ddcff}@media(max-width:720px){main{grid-template-columns:1fr}nav>*{max-width:100%}header,nav,footer{padding:12px}.metric{min-height:0}}</style>
<header><h1>PathologyEdge · 세포 중심을 직접 학습하면 무엇이 달라질까요?</h1><p>같은 영상과 고정 분류기로 비교합니다. 작은 CNN이 중심 위치 지도를 예측하고 새 후보 좌표를 찾습니다.</p><small>저장된 연구 결과 · 기존 평가 자료의 재평가 · 임상/WSI 전체 검증 아님</small></header>
<nav><label>사례 <select id="example"></select></label><label>검출 seed <select id="detector"></select></label><label>고정 분류기 <select id="classifier"></select></label><label><input id="overlay" type="checkbox" checked> 중심점 표시</label><label><input id="heat" type="checkbox"> 학습 위치 지도</label></nav>
<div id="source"></div><main><article><h2>정답 주석</h2><canvas id="truth" width="672" height="672"></canvas><div id="truthMetric" class="metric"></div></article><article><h2>기존 색상 기반 검출</h2><canvas id="before" width="672" height="672"></canvas><div id="beforeMetric" class="metric"></div></article><article><h2>학습한 중심 검출</h2><canvas id="after" width="672" height="672"></canvas><div id="afterMetric" class="metric"></div></article></main>
<div id="status" role="status">이미지 준비 중</div><footer><p><span style="color:#ffe600">● 양성 종양</span> · <span style="color:#00e5ff">● 음성 종양</span> · <span style="color:#ff43dd">● 양성 비종양</span> · <span style="color:#5dff54">● 음성 비종양</span></p>
<p>위치 지도는 핵 윤곽이나 개수 지도가 아닙니다. 주황 표시의 불투명도는 실제 점수×0.7이며 0.05 미만은 숨깁니다. 점수는 보정된 임상 확률이 아니며, 합계가 핵 개수가 되지 않습니다. 분류기는 새로 검출한 위치에서 다시 예측했습니다.</p>
<details><summary>전체407장·10케이스 / 외부133장 결과 보기</summary><div id="totals" class="scroll"></div><p>위 영상은 Patherea의 한 사례입니다. 전체 집계와 구분하세요. BCData는 종양 중심만 주석되어 종양 예측만 평가합니다. 환자·슬라이드 독립성 및 MPP는 검증하지 않았습니다.</p><p>정답과 중심 거리 ≤6px로 일대일 대응합니다. FP는 대응하지 못한 후보, FN은 놓친 주석입니다. F1·재현율은 높을수록 좋습니다. 양성률=양성 종양/전체 종양이며 MAE는 낮을수록 좋고 분모0은 계산 불가로 표시합니다.</p></details>
<p>사례 선택: 기존107개 사례 + 고정 첫 검출 seed20261117의 검출F1 최대 하락/상승. 모든 seed를 전환해 확인할 수 있습니다. 원래 주석 영역 마스크가 없어 주석 지원 범위의 한계가 남아 있습니다.</p>
<small>Dejan Štepec et al., <a href="https://huggingface.co/datasets/ds2268/patherea">Patherea Breast-P1 v1.1</a>, <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC4.0</a>. 예측 위치·지도 표시를 추가했습니다.</small></footer>
<script>const examples=__DATA__,totals=__TOTALS__;const $=id=>document.getElementById(id);const colors=['#ffe600','#00e5ff','#ff43dd','#5dff54'];const names={lr:'색상 통계+LR','cnn-20261113':'CNN seed20261113','cnn-20261114':'CNN seed20261114','cnn-20261115':'CNN seed20261115'};
examples.forEach((v,i)=>$('example').add(new Option(v.reason,i)));Object.keys(examples[0].models).forEach(s=>$('detector').add(new Option(s,s)));Object.entries(names).forEach(([a,n])=>$('classifier').add(new Option(n,a)));$('classifier').value='cnn-20261113';
function fraction(f){return f.fraction===null?'계산 불가 (종양 분모0)':(100*f.fraction).toFixed(2)+'% ('+f.positive_tumor_cells+'/'+f.tumor_cells+')'}
function metric(m,n){const l=m.localization;return '후보 '+n+'개 · TP '+l.tp+' / FP '+l.fp+' / FN '+l.fn+'\\n검출F1 '+l.f1.toFixed(4)+' · 재현율 '+l.recall.toFixed(4)+'\\n4-class F1 '+m.macro_f1.toFixed(4)+'\\n예측 양성률 '+fraction(m.predicted_fraction)}
function table(arm){let html='';for(const [scope,sets] of Object.entries(totals)){const ext=scope==='external';html+='<h3>'+(ext?'BCData 기존133장 · 종양만':'Patherea 기존407장·10케이스')+'</h3><table><tr><th>검출 방식</th><th>검출F1</th><th>'+(ext?'종양2-class':'4-class')+' F1</th><th>'+(ext?'영상':'케이스')+' 양성률 MAE</th><th>계산 가능</th></tr>';for(const [s,v] of Object.entries(sets)){const m=v[arm],mae=m[ext?'image_ratio_mae_pp':'case_ratio_mae_pp'];html+='<tr><td>'+(s==='baseline'?'기존LoG':'학습seed'+s)+'</td><td>'+m.localization.f1.toFixed(4)+'</td><td>'+m[ext?'two_class_macro_f1':'macro_f1'].toFixed(4)+'</td><td>'+(mae===null?'—':mae.toFixed(2)+'%p')+'</td><td>'+m[ext?'image_ratio_valid':'case_ratio_valid']+'/'+(ext?'133':'10')+'</td></tr>'}html+='</table>'}return html}
let revision=0;async function render(){const rev=++revision,e=examples[+$('example').value],seed=$('detector').value,arm=$('classifier').value,learned=e.models[seed];const image=new Image();image.src=e.image_url;const heat=new Image();heat.src=learned.heatmap_url;await Promise.all([image.decode(),heat.decode()]);if(rev!==revision)return;
for(const [id,ps,cs] of [['truth',e.gt_points,e.gt_classes],['before',e.baseline.points,e.baseline.classes[arm]],['after',learned.points,learned.classes[arm]]]){const ctx=$(id).getContext('2d');ctx.clearRect(0,0,672,672);ctx.drawImage(image,0,0,672,672);if(id==='after'&&$('heat').checked)ctx.drawImage(heat,0,0,672,672);if($('overlay').checked)ps.forEach(([x,y],i)=>{ctx.beginPath();ctx.arc(x*3,y*3,9,0,Math.PI*2);ctx.strokeStyle=colors[cs[i]];ctx.lineWidth=2.3;ctx.stroke()})}
$('source').textContent=e.image+' · '+e.reason;$('truthMetric').textContent='주석 세포 '+e.gt_points.length+'개\\n정답 양성률 '+fraction(e.baseline.metrics[arm].target_fraction);$('beforeMetric').textContent=metric(e.baseline.metrics[arm],e.baseline.points.length);$('afterMetric').textContent=metric(learned.metrics[arm],learned.points.length);$('totals').innerHTML=table(arm);$('status').textContent='표시 완료 · 동일 원본 좌표 · 새 중심 좌표에서 분류 · 기준 '+learned.config.threshold+' / 최소 간격 '+learned.config.min_distance+'px';}
for(const id of ['example','detector','classifier','overlay','heat'])$(id).onchange=()=>render().catch(e=>$('status').textContent='표시 오류: '+e.message);render().catch(e=>$('status').textContent='표시 오류: '+e.message);</script></html>'''
    encode=lambda v:json.dumps(v,ensure_ascii=False).replace('</','<\\/')
    with Path(output).open('x') as f:f.write(template.replace('__DATA__',encode(examples)).replace('__TOTALS__',encode(totals)))
    return dict(examples=[{'image':e['image'],'criterion':e['reason'],'delta_detection_f1':e['delta_f1']} for e in examples],heatmap_replays=replays,all_replays_exact=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=export(a.run,a.output)
    with (a.output.parent/'review-export.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False))
