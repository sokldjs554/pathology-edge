import fs from 'node:fs';
const root='/workspace/pathology-edge-auto-ki67/work/learned-centers-20261113';
const run='/workspace/pathology-edge-auto-ki67/work/learned-centers-leaky-run-20261113';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const selection=read(run+'/selection.json').models;
const reports=Object.fromEntries(selection.map(m=>[m.seed,read(`${run}/seed-${m.seed}/internal/results.json`).arms]));
const baseline=read('/workspace/pathology-edge-auto-ki67/work/auto-ki67-run-20261113/results.json').arms;
const page=await (await fetch('http://127.0.0.1:9339/json/new?about:blank',{method:'PUT'})).json();
const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const pending=new Map(),errors=[];
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params)});
function c(method,params={}){return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});ws.send(JSON.stringify({id:key,method,params}));setTimeout(()=>{if(pending.has(key)){pending.delete(key);reject(new Error('CDP timeout '+method))}},10000).unref()})}
async function e(expression){const r=await c('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
await c('Runtime.enable');await c('Page.enable');await c('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await c('Page.navigate',{url:'http://127.0.0.1:8915/review.html'});
for(let i=0;i<50;i++){if(await e("document.getElementById('status')?.textContent.includes('표시 완료')"))break;await new Promise(r=>setTimeout(r,100));}
const checks=[];
for(let i=0;i<3;i++)for(const m of selection)for(const arm of ['lr','cnn-20261113','cnn-20261114','cnn-20261115']){
 const value=await e(`(async()=>{$('example').value='${i}';$('detector').value='${m.seed}';$('classifier').value='${arm}';await render();return {image:examples[${i}].image,seed:${m.seed},arm:'${arm}',before:$('beforeMetric').textContent,after:$('afterMetric').textContent,gt:$('truthMetric').textContent}})()`);
 const verify=(text,v)=>{const l=v.localization;return text.includes(`후보 ${l.tp+l.fp}개 · TP ${l.tp} / FP ${l.fp} / FN ${l.fn}`)&&text.includes(`검출F1 ${l.f1.toFixed(4)} · 재현율 ${l.recall.toFixed(4)}`)&&text.includes(`4-class F1 ${v.macro_f1.toFixed(4)}`)};
 const a=reports[m.seed][arm].per_image.find(r=>r.image===value.image),b=baseline[arm].per_image.find(r=>r.image===value.image);
 if(!verify(value.after,a)||!verify(value.before,b)||!value.gt.includes('주석 세포 '+(a.localization.tp+a.localization.fn)+'개'))throw Error('Saved-results mismatch '+JSON.stringify(value));
 checks.push({...value,numbers_match_saved_json:true});
}
const toggles=await e("(async()=>{$('example').value='0';$('detector').value='20261117';$('classifier').value='cnn-20261113';$('overlay').checked=true;$('heat').checked=false;await render();const a=$('after').toDataURL();$('heat').checked=true;await render();const b=$('after').toDataURL();$('overlay').checked=false;await render();const c=$('after').toDataURL();$('overlay').checked=true;$('heat').checked=false;await render();return {heatmap_changes_pixels:a!==b,centers_change_pixels:b!==c}})()");
if(!toggles.heatmap_changes_pixels||!toggles.centers_change_pixels)throw Error('Toggles fail');
let shot=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(root+'/desktop.png',Buffer.from(shot.data,'base64'));
await e("$('heat').checked=true;render()");shot=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(root+'/heatmap.png',Buffer.from(shot.data,'base64'));
await c('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await e("$('heat').checked=false;render()");
const mobile=await e("({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,selectorsVisible:[...document.querySelectorAll('select')].every(s=>s.getBoundingClientRect().right<=innerWidth)})");
if(mobile.scrollWidth>390||!mobile.selectorsVisible)throw Error('Mobile overflow '+JSON.stringify(mobile));
await e("document.querySelector('details').open=true");const expandedWidth=await e('document.documentElement.scrollWidth');if(expandedWidth>390)throw Error('Expanded overflow');await e("document.querySelector('details').open=false");
const layout=await c('Page.getLayoutMetrics');shot=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:390,height:layout.cssContentSize.height,scale:1}});fs.writeFileSync(root+'/mobile.png',Buffer.from(shot.data,'base64'));
const result={passed:errors.length===0,combinations:checks.length,example_seed_classifier_combinations:checks,...toggles,mobile,expandedWidth,errors};fs.writeFileSync(root+'/browser-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify({passed:result.passed,combinations:result.combinations,...toggles,mobile,errors}));await c('Page.close');ws.close();
