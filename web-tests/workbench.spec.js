import { tool, openTools, closeTools } from './controls.js';
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('../dist/results.json',import.meta.url)));
const cases=JSON.parse(fs.readFileSync(new URL('../dist/cases.json',import.meta.url)));
const open=async(page)=>{await page.goto('/?sample=10_1');await expect(page.locator('body')).toHaveAttribute('data-phase','ready');if(page.viewportSize().width>760)await tool(page,'toggleDock','click');};
test('candidate table navigates to original exported candidate and links its detail',async({page})=>{
 await open(page);
 await page.screenshot({path:'captures/linked-workbench-desktop.png',fullPage:true});
 await page.locator('#candidateQuery').fill('#12');
 await expect(page.locator('#candidateRows tr')).toHaveCount(1);
 await page.locator('#candidateRows button').click();
 const o=data.samples[0].methods.overlap.objects[11];
 await expect(page.locator('#selectionText')).toContainText('#12');
 await expect(page.locator('#selectedInfo')).toContainText(`${o.x.toFixed(1)}, ${o.y.toFixed(1)} px`);
 await expect(page.locator('#selectionPreview')).toBeVisible();
 await page.screenshot({path:'captures/linked-workbench-selection.png',fullPage:true});
 await expect(page.locator('#before')).toHaveAttribute('data-center',await page.locator('#after').getAttribute('data-center'));
});
test('image changes clear the object crop and restore the full candidate list',async({page})=>{
 await open(page);await page.locator('#candidateQuery').fill('#12');await page.locator('#candidateRows button').click();
 await page.locator('#sample').selectOption('10_2');
 await expect(page.locator('#activeImage')).toHaveText('TNBC 10_2');
 await expect(page.locator('#candidateQuery')).toHaveValue('');
 await expect(page.locator('#selectionPreview')).toBeHidden();
 await expect(page.locator('#candidateRows tr')).toHaveCount(data.samples[1].methods.overlap.objects.length);
});
test('pane maximize restores synchronized comparison without changing selected case',async({page})=>{
 await open(page);await tool(page,'modeBoundary','click');await page.locator('#showWorsened').click();
 const selected=cases.cases.find(c=>c.id===cases.recommended.worsened);
 const center=selected.center.map(v=>v.toFixed(3)).join(',');
 await expect(page.locator('#after')).toHaveAttribute('data-case',selected.id);
 await expect(page.locator('#after')).toHaveAttribute('data-center',center);
 await page.locator('#maximizeBefore').click();
 await expect(page.locator('#afterPane')).toBeHidden();
 await expect(page.locator('#before')).toHaveAttribute('data-center',center);
 await page.locator('#maximizeBefore').click();
 await expect(page.locator('#afterPane')).toBeVisible();
 await expect(page.locator('#before')).toHaveAttribute('data-center',await page.locator('#after').getAttribute('data-center'));
});
test('small screen keeps candidate and result controls available without page overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await open(page);
 await expect(page.locator('#toggleDock')).toBeHidden();
 await tool(page,'toggleDock','click');await expect(page.locator('#candidateDock')).toBeVisible();
 await page.locator('#candidateRows button').first().click();await expect(page.locator('#selectedInfo')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
});

test('short mobile workbench scrolls to the candidate dock without clipping controls',async({page})=>{
 await page.setViewportSize({width:390,height:667});await open(page);
 await tool(page,'toggleDock','click');
 await page.locator('#candidateQuery').scrollIntoViewIfNeeded();
 const box=await page.locator('#candidateQuery').boundingBox();
 expect(box.y).toBeGreaterThanOrEqual(0);expect(box.y+box.height).toBeLessThan(667);
 await page.locator('#candidateQuery').fill('#12');
 await page.locator('#candidateRows button').click();
 await expect(page.locator('#selectedInfo')).toContainText('중심 x, y');
 await page.locator('#closeInspector').click();
 await page.locator('#closeDock').scrollIntoViewIfNeeded();
 await page.locator('#closeDock').click();await expect(page.locator('#candidateDock')).toBeHidden();
 await page.screenshot({path:'captures/linked-workbench-short-mobile.png',fullPage:true});
});
