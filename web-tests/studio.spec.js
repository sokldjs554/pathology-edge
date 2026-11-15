import { tool, openTools, closeTools } from './controls.js';
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
fs.mkdirSync('captures',{recursive:true});
test('studio has three distinct working layouts at laptop size with linked real references',async({page})=>{
 await page.setViewportSize({width:1366,height:768});
 await page.goto('/');
 await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await expect(page.locator('#modeSingle')).toBeHidden();
 await tool(page,'modeSingle','click');await tool(page,'toggleTray');await tool(page,'nativeZoom','click');
 await expect(page.locator('body')).toHaveAttribute('data-layout','image');
 await expect(page.locator('#beforePane')).toBeHidden();
 const stage=await page.locator('#after').boundingBox();
 const strip=await page.locator('#tray').boundingBox();
 expect(strip.y).toBeGreaterThan(stage.y+stage.height);
 expect(await page.locator('.sample-item').first().evaluate(el=>el.getBoundingClientRect().width)).toBeLessThan(160);
 await expect(page.locator('#after')).toHaveAttribute('data-zoom','1.00000');
 expect(stage.width).toBeGreaterThan(1000);
 await page.screenshot({path:'captures/studio-image-laptop.png',fullPage:true});
 await tool(page,'modeBoundary','click');await tool(page,'compareFour','click');
 for(const id of ['before','after','referenceSource','referenceTruth'])await expect(page.locator('#'+id)).toBeVisible();
 await page.locator('#zoomin').click();
 const center=await page.locator('#after').getAttribute('data-center');
 await expect(page.locator('#referenceSource')).toHaveAttribute('data-center',center);
 await expect(page.locator('#referenceTruth')).toHaveAttribute('data-center',center);
 await page.screenshot({path:'captures/studio-compare-laptop.png',fullPage:true});
 await tool(page,'toggleDock','click');
 await page.locator('#candidateQuery').fill('#12');
 await page.locator('#candidateRows button').click();
 await expect(page.locator('#selectionText')).toContainText('#12');
 await expect(page.locator('#selectionPreview')).toBeVisible();
 await page.screenshot({path:'captures/studio-data-laptop.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
});
test('studio mobile data view stays visible after selecting A; IHC case strip closes',async({page})=>{
 await page.setViewportSize({width:390,height:667});
 await page.goto('/');await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await page.locator('#mobileBefore').click();await expect(page.locator('#before')).toBeVisible();
 await tool(page,'toggleDock','click');await expect(page.locator('#after')).toBeVisible();
 await expect(page.locator('#candidateDock')).toBeVisible();
 await expect.poll(async()=> (await page.locator('#after').boundingBox()).height).toBeGreaterThan(170);
 await expect.poll(async()=> Number(await page.locator('#after').getAttribute('data-zoom'))).toBeGreaterThan(.25);
 await page.screenshot({path:'captures/studio-mobile.png',fullPage:true});
 await page.goto('/ihc.html');await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await expect(page.locator('#examplePanel')).toBeHidden();
 await page.locator('#toggleCases').click();await expect(page.locator('#examplePanel')).toBeVisible();
 await page.locator('#toggleCases').click();await expect(page.locator('#examplePanel')).toBeHidden();
});

test('review entry shows A/B, offers taller two/four views and readable controls',async({page})=>{
 await page.setViewportSize({width:1366,height:768});await page.goto('/');
 await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await expect(page.locator('body')).toHaveAttribute('data-layout','compare');
 await expect(page.locator('#modeBoundary')).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('#before')).toBeVisible();await expect(page.locator('#referenceSource')).toBeHidden();
 const two=await page.locator('#after').boundingBox();expect(two.height).toBeGreaterThan(260);
 const font=await page.locator('#showImproved').evaluate(el=>parseFloat(getComputedStyle(el).fontSize));expect(font).toBeGreaterThanOrEqual(13);
 await page.screenshot({path:'captures/readability-entry.png',fullPage:true});
 await page.locator('#showWorsened').click();await expect(page.locator('#after')).toHaveAttribute('data-case',/worsened$/);const center=await page.locator('#after').getAttribute('data-center');
 await tool(page,'compareFour','click');await expect(page.locator('#referenceSource')).toBeVisible();
 expect((await page.locator('#referenceSource').boundingBox()).height).toBeGreaterThan(170);
 await page.screenshot({path:'captures/readability-four.png',fullPage:true});
 for(const [id,canvas] of [['maximizeSource','referenceSource'],['maximizeTruth','referenceTruth'],['maximizeBefore','before'],['maximizeAfter','after']]){
  const currentCenter=await page.locator('#after').getAttribute('data-center');
  await expect(page.locator('#'+id)).toHaveText('크게 보기');await page.locator('#'+id).click();
  expect((await page.locator('#'+canvas).boundingBox()).height).toBeGreaterThan(350);
  await expect(page.locator('#'+canvas)).toHaveAttribute('data-center',currentCenter);
  await page.locator('#fit').click();await page.locator('#'+id).click();
 }
 await page.setViewportSize({width:390,height:667});await page.setViewportSize({width:1366,height:768});
 await tool(page,'modeBoundary','click');await expect(page.locator('#referenceTruth')).toBeHidden();await expect(page.locator('#tray')).toBeHidden();
 await tool(page,'modeSingle','click');await expect(page.locator('#viewState')).toContainText('B 결과 탐색');
 await tool(page,'toggleDock','click');expect(await page.locator('.candidate-table td').first().evaluate(el=>parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(13);
});
test('shared navigation is consistent and WSI provenance opens only on request',async({page})=>{
 for(const path of ['/','/wsi.html','/ihc.html']){
  await page.goto(path);await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
  await expect(page.locator('header nav a')).toHaveText(['WSI 탐색','경계 비교','IHC 세포 분류']);
 }
 await page.goto('/wsi.html');await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
 await expect(page.locator('#provenance')).toBeHidden();await page.getByText('슬라이드·모델·분석 범위',{exact:true}).click();await expect(page.locator('#provenance')).toBeVisible();
});
