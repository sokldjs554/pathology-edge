import fs from 'node:fs';
const root='/workspace/pathology-edge-auto-ki67/work/candidate-filter-20261113';
const page=await (await fetch('http://127.0.0.1:9338/json/new?about:blank',{method:'PUT'})).json();
const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const pending=new Map(),errors=[];
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params)});
function c(method,params={}){return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});ws.send(JSON.stringify({id:key,method,params}));setTimeout(()=>{if(pending.has(key)){pending.delete(key);reject(new Error('CDP timeout '+method))}},10000).unref()})}
async function e(expression){const r=await c('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
await c('Runtime.enable');await c('Page.enable');await c('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await c('Page.navigate',{url:'http://127.0.0.1:8914/review.html'});
for(let i=0;i<50;i++){if(await e("document.getElementById('status')?.textContent.includes('표시 완료')"))break;await new Promise(r=>setTimeout(r,100));}
const checks=[];
for(let i=0;i<3;i++)for(const arm of ['lr','cnn-20261113','cnn-20261114','cnn-20261115']){
 const value=await e(`(async()=>{$('example').value='${i}';$('model').value='${arm}';await render();const e=examples[${i}],a='${arm}';return {image:e.image,arm:a,before:$('beforeMetric').textContent===metric(e.metrics.baseline[a],e.points.length),after:$('afterMetric').textContent===metric(e.metrics.filtered[a],e.keep_indices.length)+'\\n제거 '+(e.points.length-e.keep_indices.length)+'개',gt:$('truthMetric').textContent.includes('주석 세포 '+e.gt_points.length+'개')}})()`);
 if(!value.before||!value.after||!value.gt)throw Error('Viewer mismatch '+JSON.stringify(value));checks.push(value);
}
const toggles=await e("(async()=>{$('example').value='0';$('model').value='cnn-20261113';$('overlay').checked=true;$('removed').checked=true;await render();const a=$('after').toDataURL();$('removed').checked=false;await render();const b=$('after').toDataURL();$('overlay').checked=false;await render();const c=$('after').toDataURL();$('overlay').checked=true;$('removed').checked=true;await render();return a!==b&&b!==c})()");if(!toggles)throw Error('Toggles fail');
let shot=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(root+'/desktop.png',Buffer.from(shot.data,'base64'));
await c('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await e('render()');
const mobile=await e("({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,selectorsVisible:[...document.querySelectorAll('select')].every(s=>s.getBoundingClientRect().right<=innerWidth)})");
if(mobile.scrollWidth>390||!mobile.selectorsVisible)throw Error('Mobile overflow '+JSON.stringify(mobile));
await e("document.querySelector('details').open=true");const expandedWidth=await e('document.documentElement.scrollWidth');if(expandedWidth>390)throw Error('Expanded overflow');await e("document.querySelector('details').open=false");
const layout=await c('Page.getLayoutMetrics');shot=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:390,height:layout.cssContentSize.height,scale:1}});fs.writeFileSync(root+'/mobile.png',Buffer.from(shot.data,'base64'));
const result={passed:errors.length===0,example_model_combinations:checks,overlays_change_pixels:toggles,mobile,expandedWidth,errors};fs.writeFileSync(root+'/browser-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));await c('Page.close');ws.close();
