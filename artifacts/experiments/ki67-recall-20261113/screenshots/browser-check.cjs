const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('assert/strict');
(async()=>{
const root=process.cwd()+'/work/recall-decoder-20261113';
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const records=[];
for(const width of [1440,390]){
 const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:8127/review.html');
 await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('표시 완료'));
 for(let i=0;i<4;i++){
  await page.selectOption('#example',String(i));
  await page.waitForFunction(i=>document.querySelector('#status').textContent.includes(data.examples[i].image),i);
  const arms=i<2?['cnn-20261113','cnn-20261114','cnn-20261115','lr']:['lr'];
  for(const arm of arms){
   if(i<2)await page.selectOption('#classifier',arm);
   await page.waitForFunction(({i,arm})=>document.querySelector('#am').textContent===metric(data.examples[i].a,arm,i<2),{i,arm});
   const actual=await page.evaluate(()=>({a:$('am').textContent,b:$('bm').textContent,overflow:document.documentElement.scrollWidth>innerWidth,disabled:$('classifier').disabled,coords:[...document.querySelectorAll('canvas')].map(c=>[c.width,c.height])}));
   assert(!actual.overflow);assert.equal(actual.disabled,i>=2);assert.deepEqual(actual.coords,[[672,672],[672,672],[672,672]]);
   const before=await page.locator('#after').evaluate(c=>c.toDataURL());
   await page.uncheck('#overlay');await page.uncheck('#missed');
   await page.waitForFunction(()=>!$('overlay').checked&&!$('missed').checked);
   const raw=await page.locator('#after').evaluate(c=>c.toDataURL());
   assert.notEqual(before,raw);
   await page.check('#overlay');await page.check('#missed');
   records.push({width,example:i,arm,...actual});
  }
 }
 await page.selectOption('#example','0');await page.selectOption('#classifier','cnn-20261113');
 await page.waitForFunction(()=>$('status').textContent.includes(data.examples[0].image)&&$('am').textContent===metric(data.examples[0].a,'cnn-20261113',true));
 await page.screenshot({path:root+'/review-'+width+'.png',fullPage:true});
 assert.deepEqual(errors,[]);await page.close();
}
await browser.close();fs.writeFileSync(root+'/browser-check.json',JSON.stringify({all_checks_passed:true,views:records.length,records},null,2));console.log(JSON.stringify({all_checks_passed:true,views:records.length}));
})().catch(e=>{console.error(e);process.exit(1)});
