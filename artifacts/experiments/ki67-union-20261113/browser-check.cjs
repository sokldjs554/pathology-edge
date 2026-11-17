const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const url=process.argv[2];const out=process.argv[3];fs.mkdirSync(out,{recursive:true});
 await page.goto(url);await page.waitForFunction(()=>document.querySelectorAll('canvas').length===4&&document.querySelector('canvas').getContext('2d').getImageData(0,0,1,1).data[3]===255);
 const cases=await page.locator('#example option').count();const report={url,examples:cases,desktop:{width:1440,height:1000},mobile:{width:390,height:844},checks:[],errors};
 for(let i=0;i<cases;i++){
  await page.selectOption('#example',String(i));await page.waitForTimeout(100);
  const check=await page.evaluate(()=>({image:data.examples[current].image,panels:document.querySelectorAll('canvas').length,metrics:[...document.querySelectorAll('.counts')].every((el,j)=>{const key=['A','B','C0','C'][j],r=data.examples[current].panels[key];return el.textContent.includes(`후보 ${r.points.length}`)&&el.textContent.includes(`FP ${r.counts.fp}`)&&el.textContent.includes(`FN ${r.counts.fn}`)}),state:document.querySelector('#case').textContent}));
  if(check.panels!==4||!check.metrics)throw Error('Missing panels or incorrect counts');
  await page.uncheck('#overlay');await page.waitForTimeout(80);
  const same=await page.evaluate(()=>new Set([...document.querySelectorAll('canvas')].map(c=>c.toDataURL())).size===1);
  if(!same)throw Error('The four image coordinates do not match');check.same_image_without_overlay=same;
  await page.check('#overlay');await page.waitForTimeout(80);report.checks.push(check);
 }
 await page.selectOption('#example','0');await page.waitForTimeout(100);await page.screenshot({path:out+'/desktop.png',fullPage:true});
 const first=await page.locator('#case').textContent();await page.click('#next');const next=await page.locator('#case').textContent();await page.click('#prev');if(first===next||await page.locator('#case').textContent()!==first)throw Error('Next/previous navigation broken');
 await page.setViewportSize({width:390,height:844});await page.selectOption('#example','1');await page.waitForTimeout(100);
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);if(overflow)throw Error('Body overflows mobile viewport');
 await page.locator('#overlay').scrollIntoViewIfNeeded();await page.uncheck('#overlay');await page.check('#overlay');await page.waitForTimeout(80);await page.screenshot({path:out+'/mobile.png',fullPage:true});
 report.body_overflow_mobile=overflow;report.navigation_passed=true;report.all_passed=errors.length===0;
 fs.writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();if(errors.length)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
