import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import crypto from 'node:crypto';
const data=JSON.parse(fs.readFileSync(new URL('../dist/results.json',import.meta.url),'utf8'));
fs.mkdirSync('captures',{recursive:true});
const ready=async(page,id='10_1')=>{await expect(page.locator('body')).toHaveAttribute('data-phase','ready');await expect(page.locator('#status')).toContainText(id);await expect(page.locator('#after')).toHaveAttribute('data-zoom',/\d/);};
const open=async page=>{await page.goto('/');await ready(page);};
const shot=async(page,name)=>page.screenshot({path:`captures/${name}.png`,fullPage:true});
const bitmap=page=>page.locator('#after').evaluate(c=>c.toDataURL());
const metrics=async(page,s,scope='all')=>{
 const expected=['dice','iou','precision','recall'].map(k=>[s.methods.no_overlap.metrics[scope][k].toFixed(3),s.methods.overlap.metrics[scope][k].toFixed(3)]);
 for(let i=0;i<4;i++){const row=page.locator('#imageMetrics tr').nth(i);await expect(row.locator('td').nth(1)).toHaveText(expected[i][0]);await expect(row.locator('td').nth(2)).toHaveText(expected[i][1]);}
 await expect(page.locator('#rawCount')).toHaveText(String(s.methods.overlap.raw_count));await expect(page.locator('#mergedCount')).toHaveText(String(s.methods.overlap.merged_count));
};
const synced=async page=>expect(await page.locator('#before').getAttribute('data-center')).toBe(await page.locator('#after').getAttribute('data-center'));

test('all seven images load immediately and metrics/counts match the real export',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await open(page);await shot(page,'after-desktop');
 const obs=await page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight},bodyHeight:document.body.scrollHeight,before:document.querySelector('#before').getBoundingClientRect().toJSON(),after:document.querySelector('#after').getBoundingClientRect().toJSON(),overflow:document.documentElement.scrollWidth>innerWidth}));
 fs.writeFileSync('captures/after-observations.json',JSON.stringify(obs,null,2));
 expect(obs.after.y).toBeLessThan(270);expect(obs.overflow).toBe(false);
 for(const s of data.samples){await page.locator('#sample').selectOption(s.id);await ready(page,s.id);await expect(page.locator('#activeImage')).toHaveText(`TNBC ${s.id}`);await metrics(page,s);await expect(page.locator(`.sample-item[data-sample="${s.id}"]`)).toHaveAttribute('aria-current','true');}
 await page.locator('#tabExperiment').click();await page.locator('#failure').click();await ready(page,'10_3');await page.locator('#tabImage').click();await expect(page.locator('#delta')).toHaveClass('negative');expect(errors).toEqual([]);
});

test('synchronized zoom, drag, overview navigation, keyboard and fit',async({page})=>{
 await open(page);await page.locator('#jumpBoundary').click();await expect(page.locator('#zoomvalue')).toHaveText('300%');await synced(page);
 const box=await page.locator('#after').boundingBox();const old=await page.locator('#after').getAttribute('data-center');
 await page.mouse.move(box.x+box.width*.5,box.y+box.height*.4);await page.mouse.down();await page.mouse.move(box.x+box.width*.5+65,box.y+box.height*.4+40,{steps:8});await page.mouse.up();
 await expect(page.locator('#after')).not.toHaveAttribute('data-center',old);await synced(page);
 const z=Number(await page.locator('#after').getAttribute('data-zoom'));await page.mouse.wheel(0,-150);await expect.poll(async()=>Number(await page.locator('#after').getAttribute('data-zoom'))).toBeGreaterThan(z);await synced(page);
 const n=await page.locator('#navigator').boundingBox();await page.mouse.click(n.x+n.width*.75,n.y+n.height*.3);await synced(page);await expect(page.locator('#viewportBounds')).not.toHaveText('현재 시야 x 0–512 · y 0–512');
 await page.locator('#after').focus();await page.keyboard.press('ArrowLeft');await synced(page);await shot(page,'after-boundary-zoom');
 await page.keyboard.press('f');await expect(page.locator('#viewportBounds')).toHaveText('현재 시야 x 0–512 · y 0–512');await page.locator('#nativeZoom').click();await expect(page.locator('#zoomvalue')).toHaveText('100%');
});

test('overlay switches change real pixels and scope metrics correspond to highlighted regions',async({page})=>{
 await open(page);const initial=await bitmap(page);await page.locator('#segmentation').uncheck();expect(await bitmap(page)).not.toBe(initial);
 const plain=await bitmap(page);await page.locator('#truth').check();expect(await bitmap(page)).not.toBe(plain);await page.locator('#truth').uncheck();await page.locator('#segmentation').check();await page.locator('#grid').uncheck();expect(await bitmap(page)).not.toBe(initial);
 await page.locator('#grid').check();await page.locator('#scopeBoundary').click();await metrics(page,data.samples[0],'boundary');await expect(page.locator('#scopeExplanation')).toContainText('현재 시야 점수가 아닙니다');expect(await bitmap(page)).not.toBe(initial);await shot(page,'after-boundary-scope');
 await page.locator('#scopeInterior').click();await metrics(page,data.samples[0],'interior');await page.locator('#scopeAll').click();await metrics(page,data.samples[0]);
});

test('NMS raw-to-kept pair and image click resolve actual exported objects',async({page})=>{
 await open(page);await page.locator('#sample').selectOption('11_2');await ready(page,'11_2');const s=data.samples.find(s=>s.id==='11_2'),m=s.methods.overlap,p=m.suppressed[0];
 await page.locator('#inspectMerge').click();await page.locator('#jumpDuplicate').click();await expect(page.locator('#modeMerge')).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('#pairInfo')).toContainText(`raw #${p.suppressed_index+1} (patch ${m.raw[p.suppressed_index].patch_id}) → 유지 raw #${p.kept_index+1}`);
 await expect(page.locator('#countBefore')).toHaveText(`${m.raw_count} 후보`);await expect(page.locator('#countAfter')).toHaveText(`${m.merged_count} 후보`);await expect(page.locator('#selectedInfo')).toContainText(String(m.raw[p.kept_index].patch_id));await shot(page,'after-merge');
 await page.locator('#componentSelect').selectOption('0');const o=m.objects[0];
 const b=await page.locator('#after').boundingBox(),center=(await page.locator('#after').getAttribute('data-center')).split(',').map(Number),zoom=Number(await page.locator('#after').getAttribute('data-zoom'));
 await page.mouse.click(b.x+b.width/2+(o.x-center[0])*zoom,b.y+b.height/2+(o.y-center[1])*zoom);
 await expect(page.locator('#selectionText')).toHaveText('B · 병합 후 #1');await expect(page.locator('#selectedInfo')).toContainText(o.bbox.join(', '));
 await page.locator('#visibleOnly').check();expect(await page.locator('#componentSelect option').count()).toBeLessThan(m.objects.length+1);
 await page.locator('#sample').selectOption('10_1');await ready(page);await expect(page.locator('#selectionEmpty')).toBeVisible();await expect(page.locator('#pairInfo')).not.toContainText(`raw #${p.suppressed_index+1}`);
});

test('single image, focus panels and help are usable',async({page})=>{
 await open(page);await page.locator('#modeSingle').click();await expect(page.locator('#before')).toBeHidden();expect((await page.locator('#after').boundingBox()).width).toBeGreaterThan(1000);
 await page.locator('#focusMode').click();await expect(page.locator('#tray')).toBeHidden();await expect(page.locator('#inspector')).toBeHidden();await page.locator('#focusMode').click();await expect(page.locator('#tray')).toBeVisible();await expect(page.locator('#inspector')).toBeVisible();
 await page.locator('#help').click();await expect(page.locator('#helpDialog')).toBeVisible();await expect(page.locator('#helpDialog')).toContainText('실시간 분석'); // explicit live-inference limitation follows
 await page.keyboard.press('Escape');await expect(page.locator('#helpDialog')).toBeHidden();
});

for(const [width,height]of [[1024,768],[390,844],[375,667]])test(`responsive controls ${width}x${height}`,async({page})=>{
 await page.setViewportSize({width,height});await open(page);await expect(page.locator('#inspector')).toBeHidden();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.body.scrollHeight<=innerHeight)).toBe(true);
 const box=await page.locator('#after').boundingBox();expect(box.y).toBeLessThan(width<=760?330:270);expect(box.width).toBeGreaterThan(width<=760?width-5:400);
 if(width<=760){await page.locator('#mobileBefore').click();await expect(page.locator('#before')).toBeVisible();await expect(page.locator('#after')).toBeHidden();await page.locator('#mobileAfter').click();}
 await page.locator('#jumpBoundary').click();await expect(page.locator('#zoomvalue')).toHaveText('300%');await page.locator('#fit').click();await shot(page,`after-${width}`);
 await page.locator('#toggleInspector').click();await expect(page.locator('#inspector')).toBeVisible();await page.locator('#scopeBoundary').click();await metrics(page,data.samples[0],'boundary');await page.locator('#closeInspector').click();await expect(page.locator('#inspector')).toBeHidden();
 await page.locator('#sample').selectOption('11_2');await ready(page,'11_2');
});

test('loading, HTTP error, retry and empty states never imply a new analysis',async({page})=>{
 let release;const gate=new Promise(r=>release=r);let failed=true;
 await page.route('**/results.json',async route=>{await gate;if(failed)await route.fulfill({status:503,body:'unavailable'});else await route.fulfill({json:data});});
 await page.goto('/');await expect(page.locator('body')).toHaveAttribute('data-phase','loading');await expect(page.locator('#stateDetail')).toContainText('실시간 추론이 아니라');await expect(page.locator('#zoomin')).toBeDisabled();await shot(page,'state-loading-injected');
 release();await expect(page.locator('body')).toHaveAttribute('data-phase','error');await expect(page.locator('#stateDetail')).toContainText('503');await shot(page,'state-error-injected');failed=false;await page.locator('#retry').click();await ready(page);
 await page.unroute('**/results.json');await page.route('**/results.json',route=>route.fulfill({json:{...data,samples:[]}}));await page.reload();await expect(page.locator('body')).toHaveAttribute('data-phase','empty');await expect(page.locator('#sample')).toBeDisabled();await expect(page.locator('#stateTitle')).toHaveText('표시할 예제가 없습니다');await shot(page,'state-empty-injected');
});

test('failed image clears old numbers; rapid sample changes cannot leave mismatched results',async({page})=>{
 await open(page);const fail=data.samples.find(s=>s.id==='11_2');await page.route(`**/${fail.image}`,route=>route.fulfill({status:404,body:'missing'}));
 await page.locator('#sample').selectOption('11_2');await expect(page.locator('body')).toHaveAttribute('data-phase','error');await expect(page.locator('#rawCount')).toHaveText('—');await expect(page.locator('#imageMetrics tr')).toHaveCount(0);
 await page.unroute(`**/${fail.image}`);await page.locator('#retry').click();await ready(page,'11_2');
 await page.locator('#sample').selectOption('10_1');await page.locator('#sample').selectOption('10_2');await page.locator('#sample').selectOption('11_2');await ready(page,'11_2');await metrics(page,fail);
});

test('served UI and result bytes match this repository commit',async({request})=>{
 const rows=[];for(const name of ['index.html','app.js','style.css','viewer-math.js','results.json']){const response=await request.get('/'+name);expect(response.ok()).toBe(true);const actual=await response.body(),local=fs.readFileSync(new URL('../dist/'+name,import.meta.url));const digest=b=>crypto.createHash('sha256').update(b).digest('hex');expect(digest(actual)).toBe(digest(local));rows.push({file:name,sha256:digest(actual)});}
 fs.writeFileSync('captures/served-source-parity.json',JSON.stringify({baseURL:process.env.UI_BASE_URL||'checkout localhost',commit:process.env.GITHUB_SHA||null,files:rows},null,2));
});
