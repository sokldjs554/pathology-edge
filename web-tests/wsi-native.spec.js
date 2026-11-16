import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const data = JSON.parse(fs.readFileSync(new URL('../dist/wsi.json', import.meta.url)));
fs.mkdirSync('captures', { recursive: true });
const ready = async page => {
  await expect(page.locator('body')).toHaveAttribute('data-phase', 'ready', {timeout:25000});
};
const select = async (page, id='R1') => {
  if (!(await page.locator(`.roi-item[data-roi="${id}"]`).isVisible())) await page.locator('#toggleRegions').click();
  await page.locator(`.roi-item[data-roi="${id}"]`).click();
};
const paintReady = page => page.waitForFunction(() => WSI.viewers.B.getFullyLoaded());
const sourceLayer = (page, pane, id) => page.locator(`#overlay${pane} [data-native-rgb="${id}"]`);

test('WSI native RGB uses original level-0 pixels in both panes and survives display changes', async ({page}) => {
  await page.goto('/wsi.html'); await ready(page);
  for (const roi of data.rois) {
    await select(page, roi.id);
    for (const pane of ['A','B']) {
      const layer=sourceLayer(page,pane,roi.id);
      await expect(layer).toHaveAttribute('href',roi.image);
      await expect(layer).toHaveAttribute('x',String(roi.origin[0]));
      await expect(layer).toHaveAttribute('y',String(roi.origin[1]));
      await expect(layer).toHaveAttribute('width',String(roi.width));
      await expect(layer).toHaveAttribute('height',String(roi.height));
    }
  }
  await select(page); await page.locator('#native').click();
  await expect(page.locator('#zoomReadout')).toHaveText('100%');
  await page.locator('#displayTools summary').click();
  for(const id of ['showMask','showGrid','showBounds','showDifference','showCandidates']) await page.locator('#'+id).uncheck();
  await page.locator('#displayTools summary').click();
  await expect(sourceLayer(page,'B','R1')).toBeVisible();
  await paintReady(page);
  const screenshot=await page.screenshot();
  // Compare the actually composited screen to a browser render of the same
  // source PNG at the layer's screen transform, away from labels/scale bars.
  const result=await page.evaluate(async ({screen,roi})=>{
    const load=async src=>{const i=new Image();i.src=src;await i.decode();return i;};
    const original=await load(roi.image), actual=await load('data:image/png;base64,'+screen);
    const box=document.querySelector('#overlayB [data-native-rgb="R1"]').getBoundingClientRect();
    const viewer=document.querySelector('#viewerB').getBoundingClientRect();
    const dpr=actual.width/innerWidth;
    const expected=document.createElement('canvas');expected.width=actual.width;expected.height=actual.height;
    const ctx=expected.getContext('2d');ctx.drawImage(original,box.x*dpr,box.y*dpr,box.width*dpr,box.height*dpr);
    const rendered=document.createElement('canvas');rendered.width=actual.width;rendered.height=actual.height;
    const rc=rendered.getContext('2d');rc.drawImage(actual,0,0);
    const x=Math.round((viewer.x+viewer.width/2-32)*dpr),y=Math.round((viewer.y+viewer.height/2-32)*dpr),n=Math.round(64*dpr);
    const a=ctx.getImageData(x,y,n,n).data,b=rc.getImageData(x,y,n,n).data;
    let error=0;for(let i=0;i<a.length;i++)if(i%4!==3)error+=Math.abs(a[i]-b[i]);
    return {meanAbsoluteError:error/(n*n*3),source:[original.naturalWidth,original.naturalHeight]};
  },{screen:screenshot.toString('base64'),roi:data.rois[0]});
  expect(result.source).toEqual([1024,1024]);
  expect(result.meanAbsoluteError).toBeLessThan(1);
  fs.writeFileSync('captures/wsi-native-pixel-check.json',JSON.stringify(result,null,2));
  await page.locator('#displayTools summary').click();
  await page.locator('#showMask').check();await page.locator('#overlayOpacity').fill('20');await page.locator('#overlayOpacity').dispatchEvent('input');
  await page.locator('#displayTools summary').click();
  await expect(sourceLayer(page,'B','R1')).not.toHaveAttribute('opacity');
});

for(const [width,height] of [[1440,1000],[375,667]]) test(`WSI native automatic zoom preserves boundary center and manual inspection at ${width}`,async({page})=>{
  await page.setViewportSize({width,height});await page.goto('/wsi.html');await ready(page);await select(page);
  await expect(sourceLayer(page,'B','R1')).toBeVisible();
  await page.locator('#jumpDifference').click();
  const target=data.rois[0].difference.cases[0].center_level0.map(x=>x.toFixed(4)).join(',');
  for(const pane of ['A','B']) {
    await expect(page.locator('#viewer'+pane)).toHaveAttribute('data-center',target);
    expect(Number(await page.locator('#viewer'+pane).getAttribute('data-zoom'))).toBeLessThanOrEqual(1.00001);
  }
  await expect(page.locator('#native')).toBeVisible();
  await page.locator('#native').click();await expect(page.locator('#zoomReadout')).toHaveText('100%');
  await expect(page.locator('#position')).toContainText('원본 PNG');
  await page.locator('#zoomIn').click();await expect(page.locator('#position')).toContainText('확대 표시');
  await expect(page.locator('#viewerB')).toHaveAttribute('data-center',target);
  await page.locator('#native').click();await expect(page.locator('#zoomReadout')).toHaveText('100%');
  const center=await page.locator('#viewerB').getAttribute('data-center');
  await page.locator('#toggleResults').click();await page.locator('#toggleResults').click();
  await expect(page.locator('#viewerB')).toHaveAttribute('data-center',center);
  await expect(page.locator('#zoomReadout')).toHaveText('100%');
  await paintReady(page);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.body.scrollHeight<=innerHeight)).toBe(true);
  await page.screenshot({path:`captures/wsi-native-boundary-${width}.png`,fullPage:true});
});

test('WSI native PNG failures retain JPEG and predictions; retry restores the original image',async({page})=>{
  const r=data.rois[0];await page.route('**/'+r.image,route=>route.fulfill({status:404,body:'missing'}));
  await page.goto('/wsi.html');await ready(page);await select(page);
  await expect(page.locator('#tileWarning')).toContainText('원본 PNG');
  await expect(sourceLayer(page,'B',r.id)).toHaveCount(0);
  await expect(page.locator('#position')).toContainText('JPEG 타일');
  await expect(page.locator('#overlayB [data-mask="R1-overlap"]')).toHaveAttribute('href',r.methods.overlap.overlay);
  await paintReady(page);
  await page.unroute('**/'+r.image);await page.locator('#retryTiles').click();await ready(page);await select(page);
  await expect(sourceLayer(page,'B',r.id)).toBeVisible();
  await expect(page.locator('#tileWarning')).toBeHidden();
  await expect(page.locator('#position')).toContainText('원본 PNG');
});
