const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source=fs.readFileSync('dist/wsi.js','utf8');
const fitSource=source.slice(source.indexOf('function fit('),source.indexOf('function selectROI('));
function camera(width,height) {
  let scale=0,center;
  const viewport={
    imageToViewportRectangle:(x,y,width,height)=>({x,y,width,height}),
    fitBounds:r=>{scale=Math.min(width/r.width,height/r.height);center={x:r.x+r.width/2,y:r.y+r.height/2};},
    viewportToImageZoom:z=>z,imageToViewportZoom:z=>z,
    getZoom:()=>scale,getCenter:()=>({...center}),
    zoomTo:z=>{scale=z;},panTo:c=>{center={...c};},
  };
  const context={WSI:{viewers:{B:{viewport}}},requestAnimationFrame:fn=>fn(),resizeViewers:()=>{},synchronize:()=>{},updateView:()=>{}};
  vm.createContext(context);vm.runInContext(fitSource,context);
  return {fit:(box,margin)=>context.fit(box,margin),zoom:()=>scale,center:()=>center};
}
test('WSI automatic boundary fit does not enlarge source pixels and retains its target',()=>{
 const v=camera(600,700);v.fit([6496,21232,6560,21296],96);
 assert.equal(v.zoom(),1);assert.deepEqual(v.center(),{x:6528,y:21264});
});
test('WSI small viewport fit preserves context without forcing enlargement',()=>{
 const v=camera(200,180);v.fit([6496,21232,6560,21296],96);
 assert.equal(v.zoom(),180/256);assert.deepEqual(v.center(),{x:6528,y:21264});
});
test('WSI large display ROI fit stays at native scale',()=>{
 const v=camera(2000,1800);v.fit([5888,20608,6912,21632],70);
 assert.equal(v.zoom(),1);assert.deepEqual(v.center(),{x:6400,y:21120});
});
