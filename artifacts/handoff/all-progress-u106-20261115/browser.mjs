import fs from 'node:fs';
import crypto from 'node:crypto';
const dir='work/all-progress-handoff-20261115';
const target=await fetch('http://127.0.0.1:9245/json/new?about:blank',{method:'PUT'}).then(r=>r.json());
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
let seq=0;const pending=new Map();const errors=[];
ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text)});
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
function check(x,msg){if(!x)throw Error(msg)}
await send('Page.enable');await send('Runtime.enable');
async function go(path){await send('Page.navigate',{url:'http://127.0.0.1:8145/'+path});for(let i=0;i<150;i++){if(await evaluate(`document.readyState==='complete'&&location.pathname===${JSON.stringify('/'+path)}`))return;await new Promise(r=>setTimeout(r,100))}throw Error('Navigation timeout '+path)}
const screens=[];const rows=[];
for(const width of [1440,390]){
 await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<600});
 await go('START_HERE.html');
 const status=await evaluate(`({title:document.title,rows:document.querySelectorAll('tbody tr').length,overflow:document.documentElement.scrollWidth>innerWidth,links:[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))})`);
 check(status.rows===23,'Missing phase rows');check(!status.overflow,'Index overflow');
 const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
 const name='index-'+width+'.png';fs.writeFileSync(dir+'/'+name,Buffer.from(shot.data,'base64'));screens.push(name);
 rows.push({width,index_rows:status.rows,horizontal_overflow:status.overflow});
 await go('PERSONAL_RECORDS.html');check(await evaluate("document.querySelectorAll('tr').length===108"),'Personal records missing');
 await go('artifacts/experiments/user-cnn-vit-errors-20261112/index.html');
 check(await evaluate("[...document.images].every(i=>i.complete&&i.naturalWidth>0)"),'CNN/ViT images failed');
 await go('artifacts/experiments/ki67-normalized-20261114/review/index.html');
 // This archived viewer uses two Canvas panels, not the final viewer's SVG panels.
 let rendered=false;
 for(let attempt=0;attempt<100;attempt++){
  rendered=await evaluate("document.querySelectorAll('#panels canvas').length===2&&[...document.querySelectorAll('#panels canvas')].every(c=>c.getContext('2d').getImageData(112,112,1,1).data[3]===255)");
  if(rendered)break;
  await new Promise(r=>setTimeout(r,100));
 }
 check(rendered,'Normalized Canvas panels did not render');
 await go('review/final-transfer/review.html');
 check(await evaluate("!!document.getElementById('Ametrics')?.textContent"),'Final viewer did not render');
 const matched=await evaluate(`(()=>{const before=['A','B'].map(a=>byId(a+'metrics').textContent);const initial=byId('identity').textContent;byId('example').selectedIndex=1;byId('example').dispatchEvent(new Event('change'));const changed=initial!==byId('identity').textContent;const newMetrics=['A','B'].map(a=>byId(a+'metrics').textContent);byId('overlay').click();const invariant=newMetrics.every((v,i)=>v===byId(['A','B'][i]+'metrics').textContent);return {changed,invariant,sameRgb:['GT','A','B'].map(a=>byId(a).querySelector('image').getAttribute('href')).every((v,i,x)=>v===x[0])}})()`);
 check(matched.changed&&matched.invariant&&matched.sameRgb,'Final viewer controls mismatch');rows.push({width,final_viewer:matched});
}
check(errors.length===0,'Browser exceptions '+JSON.stringify(errors));
const version=await send('Browser.getVersion');
const report={all_checks_passed:true,browser:version.product,scope:'Actual Chromium reading the ZIP over localhost; package navigation and representative viewer checks, not new model inference or user-performed tests.',rows,errors,screenshots:screens.map(path=>({path,sha256:crypto.createHash('sha256').update(fs.readFileSync(dir+'/'+path)).digest('hex')}))};
fs.writeFileSync(dir+'/browser.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
await send('Browser.close');ws.close();
