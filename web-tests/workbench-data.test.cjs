const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const D = require('../dist/workbench-data.js');
const data = JSON.parse(fs.readFileSync(new URL('../dist/results.json', `file://${__filename}`)));
const objects = data.samples[0].methods.overlap.objects;
test('candidate rows preserve indexes and references in the saved export', () => {
 const rows = D.rows(objects);
 assert.equal(rows.length, objects.length);
 rows.forEach((r,i) => { assert.equal(r.index,i); assert.equal(r.object,objects[i]); });
});
test('exact candidate ID query cannot silently select another row', () => {
 assert.deepEqual(D.rows(objects,{query:'#12'}).map(r=>r.index),[11]);
 assert.deepEqual(D.rows(objects,{query:'999999'}),[]);
 assert.deepEqual(D.rows(objects,{query:'<script>'}),[]);
});
test('viewport and boundary filters retain the source index together', () => {
 const bounds={x0:100,y0:100,x1:300,y1:300};
 const expected=objects.map((object,index)=>({object,index})).filter(({object:o})=>o.touches_edge&&o.x>=100&&o.x<=300&&o.y>=100&&o.y<=300);
 assert.deepEqual(D.rows(objects,{bounds,edgeOnly:true}),expected);
});
test('empty inputs and blank search are valid without modifying source', () => {
 const before=JSON.stringify(objects);
 assert.deepEqual(D.rows([]),[]);
 assert.equal(D.rows(objects,{query:'  '}).length,objects.length);
 assert.equal(JSON.stringify(objects),before);
});
test('source-image crop includes the selected box and clips at image edges', () => {
 assert.deepEqual(D.cropBox({bbox:[0,0,8,10]},512,512),{x:0,y:0,width:64,height:64});
 const b=D.cropBox({bbox:[500,498,512,512]},512,512);
 assert.deepEqual(b,{x:448,y:448,width:64,height:64});
});
test('large candidate and small image crops remain inside original image', () => {
 const b=D.cropBox({bbox:[10,20,150,180]},200,200);
 assert.ok(b.x<=10&&b.y<=20&&b.x+b.width>=150&&b.y+b.height>=180);
 assert.ok(b.x+b.width<=200&&b.y+b.height<=200);
 assert.deepEqual(D.cropBox({bbox:[0,0,20,20]},30,23),{x:0,y:0,width:30,height:23});
});

test('viewport upper bounds match the existing viewer half-open filter', () => {
 const list=[{x:10,y:10},{x:20,y:10},{x:10,y:20}];
 assert.deepEqual(D.rows(list,{bounds:{x0:10,y0:10,x1:20,y1:20}}).map(r=>r.index),[0]);
});
