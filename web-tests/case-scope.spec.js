import {test,expect} from '@playwright/test';
import fs from 'node:fs';
const cases=JSON.parse(fs.readFileSync(new URL('../dist/cases.json',import.meta.url)));

for(const width of [1440,375])test(`case direction buttons keep the current image and disclose absent evidence at ${width}`,async({page})=>{
  await page.setViewportSize({width,height:900});await page.goto('/');
  await expect(page.locator('#after')).toHaveAttribute('data-case','11_1-improved');
  for(const image of ['11_1','10_1','10_2','10_3','10_4','11_2','11_3']){
    await page.locator('#sample').selectOption(image);
    await expect(page.locator('body')).toHaveAttribute('data-phase','ready');
    await expect(page.locator('.guide-step')).toContainText(image);
    for(const [direction,button] of [['improved','showImproved'],['worsened','showWorsened']]){
      const c=cases.cases.find(c=>c.sample_id===image&&c.direction===direction);
      const control=page.locator('#'+button);
      if(!c){
        await expect(control).toBeDisabled();await expect(control).toContainText('저장 사례 없음');
        await expect(control).toHaveAttribute('title',new RegExp(image));
      }else{
        await expect(control).toBeEnabled();await control.click();
        await expect(page.locator('#after')).toHaveAttribute('data-case',c.id);
        for(const side of ['before','after'])await expect(page.locator('#'+side)).toHaveAttribute('data-center',c.center.map(v=>v.toFixed(3)).join(','));
        await expect(control).toHaveAttribute('aria-pressed','true');
        await expect(page.locator('#outcomeScore')).toHaveText(`${c.before.dice.toFixed(3)} → ${c.after.dice.toFixed(3)}`);
        await expect(page.locator('#outcomeLabel')).toContainText(image);
        await expect(page.locator('#maskBefore')).toHaveAttribute('data-case',c.id);
        await expect(page).toHaveURL(new RegExp(`sample=${image}&case=${c.id}`));
        if(image==='11_1')await page.screenshot({path:`captures/same-image-${direction}-${width}.png`,fullPage:true});
      }
      await expect(page.locator('#sample')).toHaveValue(image);
    }
    if(image==='10_2')await page.screenshot({path:`captures/same-image-absent-${width}.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  }
});
