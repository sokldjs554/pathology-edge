const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

// Exercise real button binding and availability; only DOM event registration
// and the final navigation boundary are replaced in this Node-only test.
function reviewAt(sampleId){
  const elements=new Map();
  const element=id=>{
    if(!elements.has(id))elements.set(id,{disabled:false,events:{},addEventListener(type,fn){this.events[type]=fn;}});
    return elements.get(id);
  };
  const state={phase:'ready',sample:{id:sampleId}};
  const context=vm.createContext({state,$:element,draw(){},document:{querySelectorAll(){return [];}}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../dist/review-ui.js'),'utf8')+'\nglobalThis.review=Review;',context);
  const review=context.review;
  review.data=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/cases.json'),'utf8'));
  const destinations=[];
  review.open=id=>destinations.push(id);
  review.bind();review.refresh();
  return {review,state,element,destinations};
}

test('both case buttons navigate within the selected image instead of global recommendations',()=>{
  const app=reviewAt('11_1');
  for(const image of ['11_1','10_1','10_3','11_3']){
    app.state.sample.id=image;app.review.refresh();
    app.element('showImproved').events.click();app.element('showWorsened').events.click();
  }
  assert.deepEqual(app.destinations,[
    '11_1-improved','11_1-worsened','10_1-improved','10_1-worsened',
    '10_3-improved','10_3-worsened','11_3-improved','11_3-worsened',
  ]);
});

test('a missing saved direction disables its button and never navigates to another image',()=>{
  for(const [image,missing,available,want] of [
    ['10_2','showImproved','showWorsened','10_2-worsened'],
    ['10_4','showImproved','showWorsened','10_4-worsened'],
    ['11_2','showWorsened','showImproved','11_2-improved'],
  ]){
    const app=reviewAt(image);
    assert.equal(app.element(missing).disabled,true,image);
    assert.match(app.element(missing).textContent,/저장 사례 없음/);
    app.element(missing).events.click();assert.deepEqual(app.destinations,[]);
    assert.equal(app.element(available).disabled,false);
    app.element(available).events.click();assert.deepEqual(app.destinations,[want]);
  }
});
