import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const evidence=JSON.parse(fs.readFileSync(new URL('../dist/cases.json',import.meta.url)));
const ready=async page=>{await page.goto('/');await expect(page.locator('#showImproved')).toBeEnabled();};

test('first visit prioritizes comparison and defers advanced choices',async({page})=>{
 await page.setViewportSize({width:1366,height:768});await ready(page);
 await expect(page.locator('#detailTools summary')).toBeVisible();
 await expect(page.locator('#detailTools')).not.toHaveAttribute('open','');
 await expect(page.locator('.studio-rail')).toHaveCount(0);
 for(const id of ['modeMerge','compareFour','toggleDock','opacity','grid','showResults'])await expect(page.locator('#'+id)).toBeHidden();
 for(const id of ['before','after','showImproved','showWorsened','zoomin','zoomout','fit'])await expect(page.locator('#'+id)).toBeVisible();
 const box=await page.locator('#after').boundingBox();expect(box.y).toBeLessThan(250);expect(box.height).toBeGreaterThan(440);
 await expect(page.locator('#inspector')).toBeHidden();await expect(page.locator('#tray')).toBeHidden();
 await page.screenshot({path:'captures/simple-entry.png',fullPage:true});
 for(const direction of ['improved','worsened']){
  await page.locator(direction==='improved'?'#showImproved':'#showWorsened').click();
  const c=evidence.cases.find(c=>c.id===evidence.recommended[direction]);
  await expect(page.locator('#after')).toHaveAttribute('data-case',c.id);
  await expect(page.locator('#outcomeScore')).toHaveText(`${c.before.dice.toFixed(3)} → ${c.after.dice.toFixed(3)}`);
  await expect(page.locator('#outcomePixels')).toContainText(`정답 일치로 변경 ${c.corrected}px`);
  await expect(page.locator('#outcomePixels')).toContainText(`불일치로 변경 ${c.regressed}px`);
  await expect(page.locator('#inspector')).toBeHidden();
  await expect(page.locator('#before')).toHaveAttribute('data-center',await page.locator('#after').getAttribute('data-center'));
  await page.screenshot({path:`captures/simple-${direction}.png`,fullPage:true});
 }
 await page.locator('#caseEvidence').click();await expect(page.locator('#caseScores')).toBeVisible();
 const score=await page.locator('#caseScores').boundingBox(), identity=await page.locator('#activeImage').boundingBox();expect(score.y).toBeLessThan(identity.y);
 await page.locator('#closeInspector').click();await page.locator('#sample').selectOption('10_2');
 await expect(page.locator('#outcomeScore')).toHaveText('');
 await expect(page.locator('#caseEvidence')).toBeHidden();
});

test('advanced controls open on request and keyboard can return to comparison',async({page})=>{
 await ready(page);await page.locator('#detailTools summary').click();
 await expect(page.locator('#grid')).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.locator('#detailTools')).not.toHaveAttribute('open','');
 await expect(page.locator('#detailTools summary')).toBeFocused();
 await page.locator('#detailTools summary').click();await page.locator('#compareFour').click();
 await expect(page.locator('#referenceTruth')).toBeVisible();await expect(page.locator('#detailTools')).not.toHaveAttribute('open','');
 await expect(page.locator('#returnComparison')).toBeVisible();
 await page.screenshot({path:'captures/simple-four.png',fullPage:true});
 await page.locator('#returnComparison').click();await expect(page.locator('#referenceTruth')).toBeHidden();
 await page.locator('#detailTools summary').click();await page.locator('#modeMerge').click();
 await expect(page.locator('#outcomeLabel')).toContainText('중복 후보');
 await page.locator('#showImproved').click();await expect(page.locator('#outcomeLabel')).toContainText('선택 상자 경계 Dice');
 await page.locator('#detailTools summary').click();await page.locator('#toggleDock').click();
 await expect(page.locator('#candidateDock')).toBeVisible();
 expect((await page.locator('#after').boundingBox()).width).toBeGreaterThan(500);
 await expect(page.locator('#outcomeScore')).toHaveText('');
 await page.locator('#showWorsened').click();
 await expect(page.locator('#candidateDock')).toBeHidden();await expect(page.locator('#before')).toBeVisible();
});

for(const width of [375,1024])test(`progressive menu and scoped outcome remain usable at ${width}`,async({page})=>{
 await page.setViewportSize({width,height:768});await ready(page);await page.locator('#showImproved').click();
 await expect(page.locator('#outcomeScore')).toBeVisible();
 await expect(page.locator('#inspector')).toBeHidden();
 const box=await page.locator('#after').boundingBox();expect(box.height).toBeGreaterThan(240);
 await page.locator('#detailTools summary').click();await page.locator('#opacity').scrollIntoViewIfNeeded();
 const knob=await page.locator('#opacity').boundingBox();expect(knob.y).toBeGreaterThan(0);expect(knob.y+knob.height).toBeLessThan(768);
 await page.keyboard.press('Escape');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
 await page.screenshot({path:`captures/simple-${width}.png`,fullPage:true});
});


test('result-table case restores both images from B-only and candidate views',async({page})=>{
 await ready(page);
 for(const mode of ['modeSingle','toggleDock']){
  await page.locator('#detailTools summary').click();await page.locator('#'+mode).click();
  await page.locator('#detailTools summary').click();await page.locator('#showResults').click();
  await expect(page.locator('#closeInspector')).toBeFocused();
  await page.locator('#perImageRows button').first().click();
  await expect(page.locator('#before')).toBeVisible();await expect(page.locator('#after')).toBeVisible();
  await expect(page.locator('#after')).toHaveAttribute('data-case','10_1-worsened');
  await expect(page.locator('#outcomeScore')).toHaveText('0.546 → 0.433');
 }
});


test('tablet candidate details share a column without shrinking the image',async({page})=>{
 await page.setViewportSize({width:1024,height:768});await ready(page);
 await page.locator('#detailTools summary').click();await page.locator('#toggleDock').click();
 expect((await page.locator('#after').boundingBox()).width).toBeGreaterThan(500);
 await page.locator('#candidateRows button').first().click();
 expect((await page.locator('#after').boundingBox()).width).toBeGreaterThan(500);
 await expect(page.locator('#selectedInfo')).toBeVisible();
 await page.locator('#detailTools summary').click();await expect(page.locator('#grid')).toBeVisible();
 await page.keyboard.press('Escape');
 await page.screenshot({path:'captures/simple-tablet-candidates.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
});


test('case loading preserves a later four-pane choice',async({page})=>{
 let release;
 const gate=new Promise(resolve=>{release=resolve;});
 await page.route('**/assets/10_3.png',async route=>{await gate;await route.continue();});
 await ready(page);
 try {
  await page.locator('#showWorsened').click();
  await expect(page.locator('body')).toHaveAttribute('data-phase','loading');
  await page.locator('#detailTools summary').click();await page.locator('#compareFour').click();
  await expect(page.locator('body')).toHaveAttribute('data-comparison','four');
 } finally {release();}
 await expect(page.locator('#after')).toHaveAttribute('data-case','10_3-worsened');
 await expect(page.locator('body')).toHaveAttribute('data-comparison','four');
 await expect(page.locator('#referenceTruth')).toBeVisible();
 await expect(page.locator('#referenceTruth')).toHaveAttribute('data-center',await page.locator('#after').getAttribute('data-center'));
});
