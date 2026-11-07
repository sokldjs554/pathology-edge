'use strict';
const $ = id => document.getElementById(id);
const state={data:null,sample:null,images:{},zoom:1,cx:256,cy:256,selected:null,loading:0};
const names={classical:'OpenCV 기준',no_overlap:'무겹침',overlap:'겹침 + 병합',full:'512px 전체 입력'};
const modes=['no_overlap','overlap'];
const canvases=[$('before'),$('after')];
const fmt=v=>v.toFixed(3), ms=v=>`${Math.round(v*1000)}ms`;
const imageLoad=src=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(new Error(`이미지를 읽지 못했습니다: ${src}`));im.src=src;});
function geometry(canvas){const fit=canvas.width/512;return {scale:fit*state.zoom,ox:canvas.width/2-state.cx*fit*state.zoom,oy:canvas.height/2-state.cy*fit*state.zoom};}
function draw(){
 if(!state.sample)return;
 canvases.forEach((canvas,i)=>{
  const ctx=canvas.getContext('2d'),{scale,ox,oy}=geometry(canvas),result=state.sample.methods[modes[i]];
  ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#0c1115';ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.save();ctx.translate(ox,oy);ctx.scale(scale,scale);ctx.drawImage(state.images.base,0,0);
  if($('segmentation').checked)ctx.drawImage(state.images[modes[i]],0,0);
  if($('truth').checked)ctx.drawImage(state.images.truth,0,0);
  if($('grid').checked){ctx.strokeStyle='#ffc56b';ctx.lineWidth=1/scale;ctx.setLineDash([5/scale,4/scale]);ctx.beginPath();for(let p=128;p<512;p+=128){ctx.moveTo(p,0);ctx.lineTo(p,512);ctx.moveTo(0,p);ctx.lineTo(512,p);}ctx.stroke();ctx.setLineDash([]);}
  function circles(items,color){ctx.strokeStyle=color;ctx.lineWidth=1/scale;ctx.beginPath();for(const o of items){ctx.moveTo(o.x+4,o.y);ctx.arc(o.x,o.y,4,0,Math.PI*2);}ctx.stroke();}
  if(i===1&&$('raw').checked)circles(result.raw,'#ff6d98');
  if($('objects').checked)circles(result.objects,'#8be0ff');
  if(state.selected){const o=state.selected;ctx.strokeStyle='#ffffff';ctx.lineWidth=1.5/scale;ctx.strokeRect(o.bbox[0]-3,o.bbox[1]-3,o.bbox[2]-o.bbox[0]+6,o.bbox[3]-o.bbox[1]+6);ctx.beginPath();ctx.moveTo(o.x-14,o.y);ctx.lineTo(o.x+14,o.y);ctx.moveTo(o.x,o.y-14);ctx.lineTo(o.x,o.y+14);ctx.stroke();}
  ctx.restore();
 });
 $('zoomvalue').textContent=`${Math.round(state.zoom*100)}%`;
}
function selectObject(o,index,move=false,mode='overlap'){
 state.selected=o;
 $('selectionText').textContent=`${names[mode]} 결과 #${index+1} · 원본 PNG 위치`;
 const data=[['중심 (x, y)',`${o.x.toFixed(1)}, ${o.y.toFixed(1)} px`],['경계 상자',o.bbox.join(', ')],['출처 패치',String(o.patch_id)],['성분 면적',`${o.area} px²`],['확률 평균',o.score.toFixed(3)],['패치 경계 접촉',o.touches_edge?'있음':'없음']];
 $('selectedInfo').replaceChildren();for(const [key,value]of data){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;$('selectedInfo').append(dt,dd);}
 $('componentSelect').value=mode==='overlap'?String(index):'';
 if(move){state.cx=o.x;state.cy=o.y;state.zoom=Math.max(2,state.zoom);}
 draw();
}
async function loadSample(id){
 const token=++state.loading;
 $('status').textContent='저장된 실제 결과를 읽는 중…';$('load').disabled=true;
 try{
  const sample=state.data.samples.find(s=>s.id===id);
  if(!sample)throw new Error('존재하지 않는 이미지입니다.');
  const [base,before,after,gt]=await Promise.all([imageLoad(sample.image),imageLoad(sample.methods.no_overlap.overlay),imageLoad(sample.methods.overlap.overlay),imageLoad(sample.gt)]);
  if(token!==state.loading)return;
  const truth=document.createElement('canvas');truth.width=512;truth.height=512;const tc=truth.getContext('2d');tc.drawImage(gt,0,0);const pixels=tc.getImageData(0,0,512,512);for(let i=0;i<pixels.data.length;i+=4){const fg=pixels.data[i]>127;pixels.data[i]=213;pixels.data[i+1]=166;pixels.data[i+2]=255;pixels.data[i+3]=fg?110:0;}tc.putImageData(pixels,0,0);
  state.sample=sample;state.images={base,no_overlap:before,overlap:after,truth};state.zoom=1;state.cx=256;state.cy=256;state.selected=null;
  const a=sample.methods.no_overlap,b=sample.methods.overlap,d=b.metrics.all.dice-a.metrics.all.dice;
  $('imageTitle').textContent=`TNBC / ${id} · 512 × 512`;
  $('delta').textContent=`${d>=0?'+':''}${d.toFixed(3)}`;$('delta').style.color=d>=0?'#7be1c0':'#ff9aab';
  $('boundaryStat').textContent=`${fmt(a.metrics.boundary.dice)} → ${fmt(b.metrics.boundary.dice)}`;
  $('removed').textContent=`${b.raw_count} → ${b.merged_count}`;
  $('timing').textContent=`${ms(a.median_seconds)} → ${ms(b.median_seconds)}`;
  $('countBefore').textContent=`${a.merged_count} 성분`;$('countAfter').textContent=`${b.merged_count} 성분`;
  $('diceBefore').textContent=`Dice ${fmt(a.metrics.all.dice)}`;$('diceAfter').textContent=`Dice ${fmt(b.metrics.all.dice)}`;
  $('selectionText').textContent='화면의 원을 선택하거나 아래 목록에서 선택하세요.';$('selectedInfo').replaceChildren();
  const placeholder=new Option('연결 성분 선택…','');placeholder.disabled=true;placeholder.selected=true;
  $('componentSelect').replaceChildren(placeholder,...b.objects.map((o,i)=>new Option(`#${i+1} · (${o.x.toFixed(0)}, ${o.y.toFixed(0)})`,String(i))));
  $('sample').value=id;$('status').textContent=`불러옴 · ${id} · 학습에 쓰지 않은 테스트 이미지`;
  draw();
 }catch(error){$('status').textContent=`오류: ${error.message}`;}finally{if(token===state.loading)$('load').disabled=false;}
}
function zoom(factor){state.zoom=Math.max(.75,Math.min(8,state.zoom*factor));draw();}
function canvasPoint(event,canvas){const rect=canvas.getBoundingClientRect();return{x:(event.clientX-rect.left)*canvas.width/rect.width,y:(event.clientY-rect.top)*canvas.height/rect.height};}
for(const [canvasIndex,canvas] of canvases.entries()){
 let drag=null;
 canvas.addEventListener('wheel',event=>{event.preventDefault();if(!state.sample)return;const p=canvasPoint(event,canvas),g=geometry(canvas),ix=(p.x-g.ox)/g.scale,iy=(p.y-g.oy)/g.scale;zoom(event.deltaY<0?1.15:1/1.15);const n=geometry(canvas);state.cx=ix-(p.x-canvas.width/2)/n.scale;state.cy=iy-(p.y-canvas.height/2)/n.scale;draw();},{passive:false});
 canvas.addEventListener('pointerdown',event=>{const p=canvasPoint(event,canvas);drag={x:p.x,y:p.y,cx:state.cx,cy:state.cy,moved:false};canvas.setPointerCapture(event.pointerId);});
 canvas.addEventListener('pointermove',event=>{if(!drag)return;const p=canvasPoint(event,canvas),s=geometry(canvas).scale;if(Math.abs(p.x-drag.x)+Math.abs(p.y-drag.y)>5)drag.moved=true;state.cx=drag.cx-(p.x-drag.x)/s;state.cy=drag.cy-(p.y-drag.y)/s;draw();});
 canvas.addEventListener('pointerup',event=>{if(!drag||!state.sample){drag=null;return;}if(!drag.moved){const p=canvasPoint(event,canvas),g=geometry(canvas),x=(p.x-g.ox)/g.scale,y=(p.y-g.oy)/g.scale;const mode=modes[canvasIndex],list=state.sample.methods[mode].objects;let nearest=-1,best=Infinity;list.forEach((o,i)=>{const d=(o.x-x)**2+(o.y-y)**2;if(d<best){best=d;nearest=i;}});if(nearest>=0&&best<(14/state.zoom)**2)selectObject(list[nearest],nearest,false,mode);}drag=null;});
 canvas.addEventListener('pointercancel',()=>{drag=null;});
 canvas.addEventListener('keydown',e=>{if(e.key==='+'||e.key==='='){e.preventDefault();zoom(1.25);}if(e.key==='-'){e.preventDefault();zoom(.8);}if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();state.cx+=(e.key==='ArrowRight'?20:e.key==='ArrowLeft'?-20:0)/state.zoom;state.cy+=(e.key==='ArrowDown'?20:e.key==='ArrowUp'?-20:0)/state.zoom;draw();}});
}
$('load').addEventListener('click',()=>loadSample($('sample').value));
$('sample').addEventListener('change',()=>{$('status').textContent='선택한 이미지의 저장된 분석을 불러오세요.';});
for(const id of ['segmentation','objects','grid','raw','truth'])$(id).addEventListener('change',draw);
$('zoomin').addEventListener('click',()=>zoom(1.25));$('zoomout').addEventListener('click',()=>zoom(.8));
$('reset').addEventListener('click',()=>{state.zoom=1;state.cx=256;state.cy=256;draw();});
$('failure').addEventListener('click',()=>{if(state.data)loadSample(state.data.worst_delta_sample);});
$('componentSelect').addEventListener('change',()=>{const i=Number($('componentSelect').value);if(state.sample)selectObject(state.sample.methods.overlap.objects[i],i,true);});
async function init(){
 try{
  const response=await fetch('results.json');if(!response.ok)throw new Error(`HTTP ${response.status}`);
  const data=await response.json();state.data=data;
  $('sample').replaceChildren(...data.samples.map(s=>new Option(`TNBC ${s.id} · case ${s.group_id}`,s.id)));$('sample').disabled=false;
  for(const text of data.limits){const li=document.createElement('li');li.textContent=text;$('limits').append(li);}
  for(const [mode,r]of Object.entries(data.summary)){const tr=document.createElement('tr');if(mode==='overlap')tr.className='highlight';for(const v of [names[mode],fmt(r.macro_dice.all),fmt(r.macro_dice.boundary),ms(r.median_image_seconds)]){const td=document.createElement('td');td.textContent=v;tr.append(td);}$('summaryRows').append(tr);}
  const lines=[`${data.dataset} / train 33 · validation 10 · test 7 / case 그룹 분리`,`${data.model} / seed ${data.seed} / threshold ${data.threshold} / 학습 ${data.training_seconds.toFixed(1)}초`,`모델 SHA-256: ${data.model_sha256}`,`좌표: ${data.unit}. WSI 배율·물리 해상도는 제공되지 않았습니다.`,`픽셀 마스크: 겹친 확률을 가중 평균한 뒤 임계값 적용. 성분 목록: 패치별 연결 성분을 별도 NMS 병합. 두 경로는 수가 다를 수 있습니다.`,`메모리: 무겹침 ${data.summary.no_overlap.peak_process_rss_mib.toFixed(1)} MiB / 겹침 ${data.summary.overlap.peak_process_rss_mib.toFixed(1)} MiB (각 독립 프로세스 전체 peak RSS).`];
  for(const text of lines){const p=document.createElement('p');p.textContent=text;$('provenanceBody').append(p);}
  await loadSample(data.samples[0].id);
 }catch(error){$('status').textContent=`결과 로딩 실패: ${error.message}. 파일을 직접 열었다면 README의 로컬 서버 명령을 사용하세요.`;}
}
init();
