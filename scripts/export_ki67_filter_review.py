"""Export actual Patherea before/after points; no BCData raw data redistributed."""
import argparse
import base64
import json
from pathlib import Path


def export(run,output):
    run=Path(run)
    read=lambda p:json.loads(p.read_text())
    p=read(run/'protocol.json'); result=read(run/'patherea-results.json')
    rows={r['image']:r for r in read(Path(p['parent'])/'predictions.json')}
    retained={r['image']:r for r in read(run/'patherea-retention.json')}
    metrics={variant:{a:{r['image']:r for r in v['per_image']} for a,v in result[variant].items()}
             for variant in ('baseline','filtered')}
    first='case_0011_region_0_patch_1_O.png'
    delta=lambda n:metrics['filtered']['cnn-20261113'][n]['macro_f1']-metrics['baseline']['cnn-20261113'][n]['macro_f1']
    order=sorted(rows,key=lambda n:(delta(n),n))
    selected=[(first,'앞서 확인한 107개 후보 사례'),(order[0],'첫 CNN seed의 F1 최대 하락'),(order[-1],'첫 CNN seed의 F1 최대 상승')]
    examples=[]
    for name,reason in selected:
        row=rows[name]
        image=Path(p['data_dir'])/'images'/name
        examples.append(dict(**{k:v for k,v in row.items() if k!='pipeline_seconds'},
            reason=reason,keep_indices=retained[name]['keep_indices'],
            image_url='data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode(),
            metrics={variant:{a:m[name] for a,m in v.items()} for variant,v in metrics.items()}))
    totals={variant:{a:{k:v[k] for k in ('localization','macro_f1','case_ratio_mae_pp','case_ratio_valid','image_ratio_valid')}
                     for a,v in result[variant].items()} for variant in ('baseline','filtered')}
    template='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PathologyEdge · 후보 제거 검토</title>
<style>*{box-sizing:border-box}body{margin:0;background:#171f25;color:#e8eef1;font:15px/1.55 system-ui}header,nav,footer{padding:12px 20px;border-bottom:1px solid #495861}h1{font-size:19px;margin:0}p{margin:7px 0}small{color:#bfccd4}nav{display:flex;gap:12px;flex-wrap:wrap}label{min-width:0}select{max-width:100%;padding:8px;background:#26363f;color:white}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:#495861}article{min-width:0;background:#1d2a32;padding:12px}h2{font-size:16px;margin:0 0 8px}canvas{width:100%;height:auto;background:white;display:block}.metric{white-space:pre-line;overflow-wrap:anywhere;min-height:120px;padding-top:8px}#status,#source{padding:5px 20px;overflow-wrap:anywhere}a{color:#9bdcff}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:8px;border-bottom:1px solid #52616b;text-align:left}.scroll{overflow:auto}summary{cursor:pointer}@media(max-width:720px){main{grid-template-columns:1fr}nav>*{max-width:100%}header,nav,footer{padding:12px}.metric{min-height:0}}</style>
<header><h1>PathologyEdge · 자동 후보를 얼마나 걸러도 될까요?</h1>
<p>같은 검출기·같은 분류기에 후보 필터만 추가했습니다. 추가 후보(FP)와 놓친 정답(FN)을 함께 비교하세요.</p>
<small>저장된 실험 결과 · 연구·교육용 · 임상/WSI 전체 검증 아님</small></header>
<nav><label>사례 <select id="example"></select></label><label>고정 분류기 <select id="model"></select></label>
<label><input type="checkbox" id="overlay" checked> 중심점 표시</label><label><input type="checkbox" id="removed" checked> 제거 후보를 회색으로 표시</label></nav>
<div id="source"></div><main>
<article><h2>정답 주석</h2><canvas id="truth" width="672" height="672"></canvas><div class="metric" id="truthMetric"></div></article>
<article><h2>필터 적용 전</h2><canvas id="before" width="672" height="672"></canvas><div class="metric" id="beforeMetric"></div></article>
<article><h2>필터 적용 후</h2><canvas id="after" width="672" height="672"></canvas><div class="metric" id="afterMetric"></div></article>
</main><div id="status" role="status">이미지 준비 중</div><footer>
<p><span style="color:#ffe600">● 양성 종양</span> · <span style="color:#00e5ff">● 음성 종양</span> · <span style="color:#ff43dd">● 양성 비종양</span> · <span style="color:#5dff54">● 음성 비종양</span></p>
<p>필터 점수 ≥ __THRESHOLD__인 후보를 유지합니다. 학습은 696장·15케이스, 기준 선택은 검증 227장·4케이스에서 수행했습니다. 점수는 보정된 임상적 정답 확률이 아닙니다.</p>
<details><summary>전체 테스트 407장·10케이스 결과와 해석 범위</summary><div id="totals" class="scroll"></div>
<p>기존에 확인했던 테스트 자료의 재평가입니다. 일대일 중심 거리 ≤6px로 다시 대응하며, 4-class F1은 검출과 분류 오류를 모두 포함합니다. F1·재현율은 높을수록, MAE는 낮을수록 좋습니다. 양성률은 양성 종양 / 전체 종양 세포이며 분모가 0이면 계산 불가입니다.</p>
<p>검증 자료에서는 케이스별 기존 재현율의 90% 이상을 유지하도록 선택했습니다. 이 조건은 새 자료에서 보장되지 않습니다. 기존에 검출하지 못한 핵을 이 제거 필터가 찾아내지는 못합니다.</p>
<p>‘제거’는 실제 세포가 아님이 전문가에 의해 확정됐다는 뜻이 아닙니다. 학습 라벨은 공개 중심 주석으로 만든 대응/비대응 대리 라벨이며, 원래 주석 영역 다각형 마스크는 제공되지 않았습니다.</p></details>
<p>사례 선택: 기존 107개 사례 + 고정 첫 seed 20261113의 F1 최대 하락/상승. 모든 seed 결과를 전환해 볼 수 있습니다.</p>
<small>원영상·주석: <a href="https://huggingface.co/datasets/ds2268/patherea">Patherea Breast-P1 v1.1</a>, CC BY-NC 4.0. 예측·제거 표시를 추가했습니다. 전문가의 추가 판독은 수행하지 않았습니다.</small></footer>
<script>const examples=__DATA__, totals=__TOTALS__;const colors=['#ffe600','#00e5ff','#ff43dd','#5dff54'];const $=id=>document.getElementById(id);
const names={lr:'색상 통계 + LR','cnn-20261113':'CNN seed 20261113','cnn-20261114':'CNN seed 20261114','cnn-20261115':'CNN seed 20261115'};
examples.forEach((e,i)=>$('example').add(new Option(e.reason,i)));Object.entries(names).forEach(([a,n])=>$('model').add(new Option(n,a)));$('model').value='cnn-20261113';
function fraction(f){return f.fraction===null?'계산 불가 (종양 분모 0)':(100*f.fraction).toFixed(2)+'% ('+f.positive_tumor_cells+'/'+f.tumor_cells+')'}
function metric(m,count){const l=m.localization;return '후보 '+count+'개 · TP '+l.tp+' / FP '+l.fp+' / FN '+l.fn+'\\n검출 F1 '+l.f1.toFixed(4)+' · 재현율 '+l.recall.toFixed(4)+'\\n4-class F1 '+m.macro_f1.toFixed(4)+'\\n예측 양성률 '+fraction(m.predicted_fraction)}
let revision=0;async function render(){const rev=++revision,e=examples[+$('example').value],arm=$('model').value,image=new Image();image.src=e.image_url;await image.decode();if(rev!==revision)return;const keep=new Set(e.keep_indices);
for(const id of ['truth','before','after']){const ctx=$(id).getContext('2d');ctx.clearRect(0,0,672,672);ctx.drawImage(image,0,0,672,672);if(!$('overlay').checked)continue;
const ps=id==='truth'?e.gt_points:e.points,cs=id==='truth'?e.gt_classes:e.classes[arm];ps.forEach(([x,y],i)=>{const removed=id==='after'&&!keep.has(i);if(removed&&!$('removed').checked)return;ctx.beginPath();ctx.arc(x*3,y*3,9,0,Math.PI*2);ctx.strokeStyle=removed?'#a8adb2':colors[cs[i]];ctx.lineWidth=removed?1.5:2.3;ctx.setLineDash(removed?[4,4]:[]);ctx.stroke()});ctx.setLineDash([])}
$('source').textContent=e.image+' · '+e.reason;$('truthMetric').textContent='주석 세포 '+e.gt_points.length+'개\\n정답 양성률 '+fraction(e.metrics.baseline[arm].target_fraction);
$('beforeMetric').textContent=metric(e.metrics.baseline[arm],e.points.length);$('afterMetric').textContent=metric(e.metrics.filtered[arm],e.keep_indices.length)+'\\n제거 '+(e.points.length-e.keep_indices.length)+'개';
$('status').textContent='표시 완료 · 동일한 원본 좌표 · 화면 폭에 맞춤 · 회색 점선은 제거 후보';}
for(const id of ['example','model','overlay','removed'])$(id).onchange=()=>render().catch(e=>$('status').textContent='표시 오류: '+e.message);
$('totals').innerHTML='<table><tr><th>분류기 / 필터</th><th>검출 F1</th><th>4-class F1</th><th>케이스 양성률 MAE</th><th>계산 가능 케이스</th></tr>'+Object.entries(names).flatMap(([a,n])=>['baseline','filtered'].map(v=>{const m=totals[v][a];return '<tr><td>'+n+' / '+(v==='baseline'?'전':'후')+'</td><td>'+m.localization.f1.toFixed(4)+'</td><td>'+m.macro_f1.toFixed(4)+'</td><td>'+m.case_ratio_mae_pp.toFixed(2)+'%p</td><td>'+m.case_ratio_valid+'/10</td></tr>'})).join('')+'</table>';
render().catch(e=>$('status').textContent='표시 오류: '+e.message);</script></html>'''
    encode=lambda x:json.dumps(x,ensure_ascii=False).replace('</','<\\/')
    with Path(output).open('x') as f:
        f.write(template.replace('__DATA__',encode(examples)).replace('__TOTALS__',encode(totals)).replace('__THRESHOLD__',str(result['threshold'])))
    return dict(examples=[dict(image=e['image'],reason=e['reason']) for e in examples],new_inference_run=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(export(a.run,a.output),ensure_ascii=False))
