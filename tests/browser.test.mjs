import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {InputMonitor, Dwell, canvasPoint} from '../src/neon_game_input/browser/input.mjs';

test('Python and browser input contract use the same vectors', () => {
  const monitor = new InputMonitor({recovery: .1});
  const vectors = JSON.parse(readFileSync(new URL('./input_vectors.json', import.meta.url)));
  for (const row of vectors) {
    const result = monitor.step({source:'synthetic-test', sequence:row.seq, received_at:row.at,
      position:[640,360], valid: row.valid ?? true, mapped:true}, row.now);
    for (const [key, expected] of Object.entries(row.expect)) {
      if (key === 'credit') assert.ok(Math.abs(result[key]-expected) < 1e-9);
      else assert.equal(result[key], expected, JSON.stringify(row));
    }
  }
});
test('Dwell fires once, loss never rearms, valid outside gaze rearms', () => {
  const dwell = new Dwell(.1, .1), frame = {usable:true, ready:true, fresh:true, credit:.05};
  assert.equal(dwell.update('start', frame), null);
  assert.equal(dwell.update('start', frame), null);
  assert.equal(dwell.update('start', frame), 'start');
  for (let i=0; i<30; i++) assert.equal(dwell.update('start', frame), null);
  dwell.update(null, {usable:false});
  assert.equal(dwell.armed, false);
  dwell.update(null, frame); dwell.update(null, frame);
  assert.equal(dwell.armed, true);
});
test('Repeated frames do not advance dwell', () => {
  const dwell = new Dwell(.1);
  for (let i=0; i<100; i++) dwell.update('start', {usable:true, ready:true, fresh:false, credit:0});
  assert.equal(dwell.progress, 0);
});
test('CSS viewport maps into canvas and rejects outside points', () => {
  const rect = {left:20, top:30, width:640, height:360};
  assert.deepEqual(canvasPoint(340,210,rect,1280,720), [640,360]);
  assert.equal(canvasPoint(19,210,rect,1280,720), null);
});
test('Invalid coordinates and timestamps never become usable', () => {
  const monitor = new InputMonitor();
  for (const [position, received_at] of [[[NaN,0],1], [[1,2],NaN], [[1,2],2]]) {
    assert.equal(monitor.step({source:'synthetic',sequence:1,valid:true,mapped:true,position,received_at},1).usable,false);
  }
});
