import test from 'node:test';
import assert from 'node:assert/strict';
import {assess,summarize,csv} from './analysis.js';
test('zero load and zero error',()=>assert.equal(assess({load:0,solar:0,solar_prediction:0}).score,0));
test('full dependence and saturated error',()=>{const a=assess({load:1,solar:0,solar_prediction:2},.5);assert.equal(a.score,100);assert.equal(a.flagged,true)});
test('solar export does not give negative dependence',()=>assert.equal(assess({load:1,solar:3,solar_prediction:3}).score,0));
test('threshold equality does not flag',()=>{const a=assess({load:2,solar:1,solar_prediction:.5},.5);assert.equal(a.score,65);assert.equal(a.flagged,false)});
test('totals do not interpolate missing intervals',()=>assert.deepEqual(summarize([{timestamp:3600,solar:3,load:1,grid:-2},{timestamp:14400,solar:0,load:1,grid:1}]),{solar:3,load:2,imports:1,exports:2,coverage:50}));
test('CSV retains UTC and predictions',()=>assert.match(csv([{timestamp:0,solar:1,load:2,grid:1,solar_prediction:.8,load_prediction:1.9}]),/1970-01-01T00:00:00.000Z,1,2,1,0.8,1.9/));
