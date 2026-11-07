import {test,expect} from '@playwright/test';
import fs from 'node:fs';
const url='https://pathology-edge-lab.ykh13571.chatgpt.site';
test('capture and inspect existing published UI',async({page})=>{
  fs.mkdirSync('captures',{recursive:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await expect(page.locator('#status')).toContainText('불러옴');
  await page.screenshot({path:'captures/before-desktop.png',fullPage:true});
  const layout=await page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight},bodyHeight:document.body.scrollHeight,
    before:document.querySelector('#before').getBoundingClientRect().toJSON(),
    after:document.querySelector('#after').getBoundingClientRect().toJSON(),
    selected:document.querySelector('#selectedInfo').getBoundingClientRect().toJSON(),
    initialImage:document.querySelector('#imageTitle').textContent}));
  await page.locator('#sample').selectOption('11_2');
  const beforeLoad=await page.locator('#imageTitle').textContent();
  await page.locator('#load').click();await expect(page.locator('#imageTitle')).toContainText('11_2');
  await page.locator('#zoomin').click();await expect(page.locator('#zoomvalue')).toHaveText('125%');
  await page.locator('#raw').check();await page.locator('#truth').check();
  await page.locator('#componentSelect').selectOption('0');await expect(page.locator('#selectedInfo')).toContainText('중심');
  await page.screenshot({path:'captures/before-selected.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.reload();await expect(page.locator('#status')).toContainText('불러옴');
  await page.screenshot({path:'captures/before-mobile.png',fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyHeight:document.body.scrollHeight,canvas:document.querySelector('#before').getBoundingClientRect().toJSON()}));
  fs.writeFileSync('captures/baseline-observations.json',JSON.stringify({url,layout,mobile,beforeLoad,errors},null,2));
  expect(errors).toEqual([]);
});
