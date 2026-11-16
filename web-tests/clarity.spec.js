import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import {tool} from './controls.js';
const cases=JSON.parse(fs.readFileSync(new URL('../dist/cases.json',import.meta.url)));
const results=JSON.parse(fs.readFileSync(new URL('../dist/results.json',import.meta.url)));
const selected=cases.cases.find(c=>c.id===cases.recommended.improved);
async function entry(page){await page.goto('/');await expect(page.locator('#after')).toHaveAttribute('data-case',selected.id);}

test('entry immediately explains the method and shows a labeled actual difference',async({page})=>{
 await page.setViewportSize({width:1366,height:768});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await entry(page);
 for(const selector of ['.app-header','.brand','.experiment-nav']){const b=await page.locator(selector).boundingBox();expect(b.y,selector).toBeGreaterThanOrEqual(0);expect(b.y+b.height,selector).toBeLessThanOrEqual(54);}
 await expect(page.locator('#workspaceName')).toHaveText('나눠 본 영상, 핵 예측도 같을까요?');
 await expect(page.locator('.workflow')).toContainText('경계에 걸린 핵');
 await expect(page.locator('#beforeTitle')).toHaveText('겹치지 않게 잘라 분석');
 await expect(page.locator('#afterTitle')).toHaveText('겹쳐 분석한 뒤 결과 결합');
 await expect(page.locator('#sample')).toHaveValue(selected.sample_id);
 await expect(page.locator('#caseHighlight')).not.toBeChecked();
 await expect(page.locator('#maskReading')).toBeVisible();
 await expect(page.locator('#outcomeLabel')).toContainText('개선 사례');
 await expect(page.locator('#outcomeMeaning')).toBeVisible();
 await expect(page.locator('#outcomeScore')).toHaveText(`${selected.before.dice.toFixed(3)} → ${selected.after.dice.toFixed(3)}`);
 await expect(page.locator('#outcomePixels')).toContainText(`정답 일치로 변경 ${selected.corrected}px`);
 await expect(page.locator('#before')).toHaveAttribute('data-center',await page.locator('#after').getAttribute('data-center'));
 const sidebar=await page.locator('.review-guide').boundingBox(), image=await page.locator('#before').boundingBox();
 expect(sidebar.x+sidebar.width).toBeLessThanOrEqual(image.x);expect(image.height).toBeGreaterThan(440);
 expect((await page.locator('#maskReading p').boundingBox()).y+(await page.locator('#maskReading p').boundingBox()).height).toBeLessThan(744);
 expect(await page.locator('#maskBefore').evaluate(c=>c.toDataURL())).not.toEqual(await page.locator('#maskAfter').evaluate(c=>c.toDataURL()));
 await page.screenshot({path:'captures/clarity-first.png',fullPage:true});
 await page.locator('#showWorsened').click();
 await expect(page.locator('#after')).toHaveAttribute('data-case',cases.recommended.worsened);
 await expect(page.locator('#outcomeLabel')).toContainText('악화 사례');
 await expect(page.locator('#caseHighlight')).not.toBeChecked();
 await page.screenshot({path:'captures/clarity-worsened.png',fullPage:true});
 expect(errors).toEqual([]);
});

test('all miniature mask pixels and displayed contours come from the saved masks',async({page})=>{
 await entry(page);
 for(const direction of ['improved','worsened']){
  await page.locator(direction==='improved'?'#showImproved':'#showWorsened').click();
  const c=cases.cases.find(c=>c.id===cases.recommended[direction]);
  await expect(page.locator('#maskBefore')).toHaveAttribute('data-case',c.id);
  const sample=results.samples.find(s=>s.id===c.sample_id);
  const actual=await page.evaluate(async({c,sample})=>{
   const checks=[];
   for(const [id,path,truth] of [['maskBefore',sample.methods.no_overlap.overlay,false],['maskAfter',sample.methods.overlap.overlay,false],['maskTruth',sample.gt,true]]){
    const im=new Image();im.src=path;await im.decode();
    const source=document.createElement('canvas');source.width=source.height=512;source.getContext('2d').drawImage(im,0,0);
    const src=source.getContext('2d').getImageData(c.bbox[0],c.bbox[1],64,64).data;
    const mini=document.getElementById(id).getContext('2d').getImageData(0,0,64,64).data;
    let different=0;
    for(let i=0;i<src.length;i+=4){
     const on=truth?src[i]>127:src[i+3]>0,color=on?(truth?[170,109,224]:[235,178,77]):[37,42,46];
     for(let j=0;j<3;j++)if(mini[i+j]!==color[j])different++;
    }
    checks.push({id,different});
   }
   // Independently check the visible outline bitmap against 4-neighbor foreground.
   for(const [key,path] of [['no_overlap',sample.methods.no_overlap.overlay],['overlap',sample.methods.overlap.overlay]]){
    const im=new Image();im.src=path;await im.decode();const source=document.createElement('canvas');source.width=source.height=512;source.getContext('2d').drawImage(im,0,0);
    const src=source.getContext('2d').getImageData(0,0,512,512).data;
    const out=state.images[key+'_outline'].getContext('2d').getImageData(0,0,512,512).data;let different=0;
    for(let y=0;y<512;y++)for(let x=0;x<512;x++){const i=(y*512+x)*4;const expected=src[i+3]>0&&(x===0||y===0||x===511||y===511||!src[i-1]||!src[i+7]||!src[i-2045]||!src[i+2051]);if(Boolean(out[i+3])!==Boolean(expected))different++;}
    checks.push({id:key,different});
   }
   return checks;
  },{c,sample});
  for(const item of actual)expect(item.different,item.id).toBe(0);
 }
});

test('explicit sample and case links are preserved and selecting another image clears the story',async({page})=>{
 await page.goto('/?sample=10_1');await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await expect(page.locator('#sample')).toHaveValue('10_1');await expect(page.locator('#maskReading')).toBeHidden();
 await page.goto('/?case=10_1-worsened');await expect(page.locator('#after')).toHaveAttribute('data-case','10_1-worsened');
 await page.locator('#sample').selectOption('10_2');await expect(page.locator('#activeImage')).toHaveText('TNBC 10_2');
 await expect(page.locator('#maskReading')).toBeHidden();await expect(page.locator('#outcomeScore')).toHaveText('');
 await expect(page.locator('#predictionLegend')).not.toContainText('흰 상자');
 await page.locator('#showImproved').click();await expect(page.locator('#after')).toHaveAttribute('data-case',selected.id);
 await tool(page,'modeMerge','click');await expect(page.locator('#maskReading')).toBeHidden();
 await expect(page.locator('#beforeTitle')).toHaveText('중복 후보 억제 전');await expect(page.locator('.method-explainer')).toBeHidden();await expect(page.locator('.workflow')).toContainText('한 번의 결과');await expect(page.locator('#predictionLegend')).toContainText('동일한 겹침 추론');
 await page.screenshot({path:'captures/clarity-merge.png',fullPage:true});
});

for(const width of [375,1024])test(`first comparison and masks remain available at ${width}`,async({page})=>{
 await page.setViewportSize({width,height:844});await entry(page);
 await expect(page.locator('#showWorsened')).toBeVisible();await expect(page.locator('#after')).toBeVisible();
 const masks=page.locator('#maskReading');if(width<760){await expect(masks).not.toHaveAttribute('open','');await masks.locator('summary').click();await expect(page.locator('#maskTruth')).toBeVisible();await expect(masks.locator('p')).toBeVisible();await expect(masks.locator('p')).toContainText('경계 띠');await masks.locator('summary').click();}
 await page.locator('#after').scrollIntoViewIfNeeded();await page.screenshot({path:`captures/clarity-${width}.png`,fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
});

for(const choice of ['compareFour','toggleDock'])test(`later ${choice} wins over automatic entry while images load`,async({page})=>{
 const sample=results.samples.find(s=>s.id===selected.sample_id);
 let release,paused=false;const gate=new Promise(r=>release=r);
 await page.route('**/'+sample.methods.overlap.overlay,async route=>{paused=true;await gate;await route.continue();});
 try{
  await page.goto('/',{waitUntil:'domcontentloaded'});await expect.poll(()=>paused).toBe(true);
  await page.locator('#detailTools summary').click();await page.locator('#'+choice).click();
  await expect(page.locator('body')).toHaveAttribute(choice==='compareFour'?'data-comparison':'data-layout',choice==='compareFour'?'four':'data');
 }finally{release();}
 await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await expect(page.locator('body')).toHaveAttribute(choice==='compareFour'?'data-comparison':'data-layout',choice==='compareFour'?'four':'data');
 await expect(page.locator(choice==='compareFour'?'#referenceTruth':'#candidateDock')).toBeVisible();
 await expect(page.locator('#after')).not.toHaveAttribute('data-case',/./);
});
