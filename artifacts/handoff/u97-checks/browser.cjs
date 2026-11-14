const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
 const browser = await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const errors = [], rows=[];
 for (const width of [1440,390]) {
  const page=await browser.newPage({viewport:{width,height:950}});
  page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400&&!r.url().includes('favicon'))errors.push(r.status()+' '+r.url())});
  await page.goto('http://127.0.0.1:8138/START_HERE.html');
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  if (overflow) throw Error('Navigation overflow at '+width);
  const links=await page.locator('a').evaluateAll(as=>as.map(a=>a.href));
  for(const href of links.filter(h=>h.startsWith('http://127.0.0.1'))) { const r=await page.request.get(href);if(r.status()!=200)throw Error(href); }
  await page.getByRole('link',{name:'이번 확인: CNN–ViT 09_1'}).click();
  await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
  const heading=page.getByRole('heading',{name:'09_1 · 전체 Dice 최대 하락'});
  await heading.scrollIntoViewIfNeeded();
  const text=await page.locator('body').innerText();
  for(const expected of ['0.402373','0.344220','0.5875','0.3907','1068px'])if(!text.includes(expected))throw Error(expected);
  if(await page.locator('img').count()!==4)throw Error('expected four comparison figures');
  await page.locator('.figure').last().screenshot({path:`work/u97-handoff/cnn-vit-09_1-${width}.png`});
  rows.push({width,task_page_reached:true,all_four_figures_loaded:true,expected_global_and_crop_scores:true,navigation_local_links:links.filter(h=>h.startsWith('http://127.0.0.1')).length,navigation_overflow:false});
  await page.close();
 }
 for(const path of ['evidence/automatic/viewer.html','evidence/filter/review.html','evidence/centers/review.html','evidence/recall/review.html']){
  const page=await browser.newPage({viewport:{width:1440,height:950}});
  page.on('pageerror',e=>errors.push(e.message));
  const r=await page.goto('http://127.0.0.1:8138/'+path);
  await page.waitForTimeout(200);
  if(r.status()!=200||await page.locator('body').innerText()==='')throw Error(path);
  rows.push({path,status:r.status(),title:await page.title(),scope:'load smoke check, not full experiment/browser retest'});
  await page.close();
 }
 await browser.close();
 if(errors.length)throw Error(JSON.stringify(errors));
 const report={all_passed:true,engine:'Chromium',widths:[1440,390],rows,errors,new_inference_run:false,user_review_performed:false};
 fs.writeFileSync('work/u97-handoff/browser-check.json',JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exit(1)});
