"""Export a small offline research viewer from stored predictions, not new inference."""
import argparse
import base64
import json
from pathlib import Path


def export(run, output):
    run,output=Path(run),Path(output)
    protocol=json.loads((run/'protocol.json').read_text())
    results=json.loads((run/'results.json').read_text())
    rows=json.loads((run/'predictions.json').read_text())
    arm='cnn-20261113'  # Predeclared first seed, not the best test seed.
    lr=results['arms']['lr']['per_image']; cnn=results['arms'][arm]['per_image']
    delta=[b['macro_f1']-a['macro_f1'] for a,b in zip(lr,cnn)]
    ordered=sorted(range(len(rows)),key=lambda i:(delta[i],rows[i]['image']))
    choices=[('가장 큰 F1 하락',ordered[0]),('F1 차이 중앙 사례',ordered[len(ordered)//2]),('가장 큰 F1 상승',ordered[-1])]
    examples=[]
    for label,i in choices:
        r=rows[i]
        raw=(Path(protocol['data_dir'])/'images'/r['image']).read_bytes()
        examples.append({**r,'reason':label,'delta':delta[i],'image_url':'data:image/png;base64,'+base64.b64encode(raw).decode(),
                         'metrics':{a:v['per_image'][i] for a,v in results['arms'].items()}})
    data=json.dumps(examples,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PathologyEdge 자동 Ki-67 패치 검토</title><style>
body{margin:0;background:#15202a;color:#edf3f8;font:15px system-ui,sans-serif}header,nav,footer{padding:12px 20px;border-bottom:1px solid #41515f}h1{font-size:20px;margin:0 0 8px}p{margin:6px 0;line-height:1.6}select,button{font:inherit;padding:7px;background:#eff5f8;color:#15202a;max-width:100%}nav{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.panels{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:#41515f}.panel{background:#15202a;padding:12px;min-width:0}nav label{min-width:0;max-width:100%}canvas{display:block;width:100%;aspect-ratio:1;image-rendering:auto;background:white}.title{margin-bottom:8px;font-weight:600}.metric{overflow-wrap:anywhere;white-space:pre-line;line-height:1.6;margin-top:10px}.legend span{margin-right:14px}details{margin:10px 0}table{border-collapse:collapse}td,th{padding:6px 14px;border-bottom:1px solid #41515f;text-align:right}th:first-child,td:first-child{text-align:left}@media(max-width:750px){.panels{grid-template-columns:1fr}.panel canvas{max-width:560px;margin:auto}}
</style><header><h1>자동 Ki-67 패치 분석 · 영상에서 위치 찾기 → 분류 → 양성률</h1>
<p>정답 중심점을 입력하지 않은 저장 결과입니다. 같은 검출 위치에서 색상 분류기와 CNN을 비교합니다. 연구용이며 임상 Ki-67 검사나 WSI 전체 분석이 아닙니다.</p>
</header><nav><label>사례 <select id="example"></select></label><label>예측 모델 <select id="model"></select></label><label><input id="overlay" type="checkbox" checked> 중심점 표시</label></nav>
<div class="panels"><div class="panel"><div class="title">1. 원영상 · 224×224 px</div><canvas id="original" width="672" height="672"></canvas><div id="source" class="metric"></div></div>
<div class="panel"><div class="title">2. 제공된 정답 중심점</div><canvas id="truth" width="672" height="672"></canvas><div id="truthMetric" class="metric"></div></div>
<div class="panel"><div class="title">3. 영상만 입력한 자동 예측</div><canvas id="prediction" width="672" height="672"></canvas><div id="predMetric" class="metric"></div></div></div>
<footer><p class="legend"><span style="color:#ffe600">● 양성 종양</span><span style="color:#00e5ff">● 음성 종양</span><span style="color:#ff43dd">● 양성 비종양</span><span style="color:#5dff54">● 음성 비종양</span></p><p id="status"></p>
<details><summary>전체 테스트 결과와 해석 범위</summary><div id="totals"></div><p>기존 테스트 407장·10케이스를 재사용했습니다. 점 대응 반경은 원본 6px이고, 검출되지 않은 정답도 FN에 포함합니다. F1은 높을수록 좋습니다. 양성률은 양성 종양 / 전체 종양 세포이며 분모 0이면 계산하지 않습니다. CNN 세 seed는 모두 공개하며 좋은 seed만 고르지 않았습니다.</p></details>
<p>예시는 고정 첫 seed 20261113의 영상별 4-class F1 차이로 고른 하락·중앙·상승 사례입니다. 대표 성능은 전체 집계를 확인해야 합니다.</p>
<p>원영상·정답: <a style="color:#8fd2ff" href="https://huggingface.co/datasets/ds2268/patherea">Patherea Breast P1 v1.1</a>, CC BY-NC 4.0. 예측 중심점과 색상 표시는 추가했습니다. 병리 전문가의 독립 재판독은 수행하지 않았습니다.</p></footer>
<script>const examples=__DATA__;const totals=__TOTALS__;const colors=['#ffe600','#00e5ff','#ff43dd','#5dff54'];
const $=id=>document.getElementById(id);const names={lr:'색상 통계 + 로지스틱 회귀','cnn-20261113':'CNN · seed 20261113','cnn-20261114':'CNN · seed 20261114','cnn-20261115':'CNN · seed 20261115'};
examples.forEach((e,i)=>$('example').add(new Option(e.reason+' · '+e.image,i)));Object.entries(names).forEach(([v,t])=>$('model').add(new Option(t,v)));$('model').value='cnn-20261113';
function fraction(f){return f.fraction===null?'계산 불가 (종양 분모 0)':(100*f.fraction).toFixed(2)+'% ('+f.positive_tumor_cells+' / '+f.tumor_cells+')'}
let revision=0;async function render(){const rev=++revision;const e=examples[+$('example').value],a=$('model').value,m=e.metrics[a];const image=new Image();image.src=e.image_url;await image.decode();if(rev!==revision)return;
for(const [id,points,classes] of [['original',[],[]],['truth',e.gt_points,e.gt_classes],['prediction',e.points,e.classes[a]]]){const c=$(id).getContext('2d');c.clearRect(0,0,672,672);c.drawImage(image,0,0,672,672);if($('overlay').checked){points.forEach(([x,y],i)=>{c.beginPath();c.arc(x*3,y*3,9,0,Math.PI*2);c.strokeStyle=colors[classes[i]];c.lineWidth=2;c.stroke()})}}
$('source').textContent=e.image+'\\n'+e.reason+' · 첫 seed F1 차이 '+(e.delta>=0?'+':'')+e.delta.toFixed(4);
$('truthMetric').textContent='주석 세포 '+e.gt_classes.length+'개\\n정답 양성률 '+fraction(m.target_fraction);
$('predMetric').textContent='자동 검출 '+e.points.length+'개\\n예측 양성률 '+fraction(m.predicted_fraction)+'\\n검출 F1 '+m.localization.f1.toFixed(4)+' · 4-class F1 '+m.macro_f1.toFixed(4)+'\\n대응 '+m.localization.tp+' / 추가 후보 '+m.localization.fp+' / 놓친 정답 '+m.localization.fn;
$('status').textContent='표시 완료 · 원본 픽셀 좌표를 3배 표시 · 모델 점수의 확률 보정 없음';}
$('example').onchange=$('model').onchange=$('overlay').onchange=()=>render().catch(e=>$('status').textContent='표시 오류: '+e.message);
$('totals').innerHTML='<table><thead><tr><th>모델</th><th>검출 F1</th><th>4-class F1</th><th>케이스 양성률 MAE</th></tr></thead><tbody>'+Object.entries(totals).map(([a,r])=>'<tr><td>'+names[a]+'</td><td>'+r.localization.f1.toFixed(4)+'</td><td>'+r.macro_f1.toFixed(4)+'</td><td>'+(r.case_ratio_mae_pp===null?'—':r.case_ratio_mae_pp.toFixed(2)+'%p')+'</td></tr>').join('')+'</tbody></table>';render().catch(e=>$('status').textContent='표시 오류: '+e.message);</script></html>'''
    summary={a:{k:v[k] for k in ('localization','macro_f1','case_ratio_mae_pp')} for a,v in results['arms'].items()}
    with output.open('x') as f:f.write(template.replace('__DATA__',data).replace('__TOTALS__',json.dumps(summary)))
    return {'example_count':len(examples),'criterion_seed':20261113,'new_inference_run':False,'examples':[{'image':e['image'],'criterion':e['reason'],'delta_f1':e['delta']} for e in examples]}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(export(a.run,a.output),ensure_ascii=False))
