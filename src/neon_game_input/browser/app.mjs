import {InputMonitor, Dwell, canvasPoint} from './input.mjs';
const canvas = document.querySelector('#game'), ctx = canvas.getContext('2d');
const label = document.querySelector('#status');
const config = await fetch('/config').then(r => { if (!r.ok) throw new Error('Config unavailable'); return r.json(); });
const mouseMode = config.mode === 'mouse';
document.querySelector('#mode').textContent = mouseMode ? 'MOUSE SIMULATION · No Neon connected' : 'REAL NEON · Local Companion bridge';
const tags = await Promise.all([0, 1, 2, 3].map(id => new Promise((resolve, reject) => {
  const image = new Image(); image.onload = () => resolve(image); image.onerror = reject;
  image.src = `/tag36h11_${id}.png`;
})));
let mouse = null, sequence = 0, latest = null, ws = null, rtt = Infinity;
let pingId = 0, pendingPing = null, reconnectTimer = null;
const monitor = new InputMonitor(), dwell = new Dwell();
let state = 'ready', score = 0, remaining = 30, target = [640, 360, 62], trail = [];
canvas.addEventListener('pointermove', e => {
  mouse = canvasPoint(e.clientX, e.clientY, canvas.getBoundingClientRect(), canvas.width, canvas.height);
});
canvas.addEventListener('pointerleave', () => { mouse = null; });
window.addEventListener('blur', () => { latest = null; mouse = null; monitor.reset(); });
document.querySelector('#fullscreen').onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch { label.textContent = 'Fullscreen unavailable in this browser'; }
};
document.addEventListener('fullscreenchange', () => { latest = null; monitor.reset(); });

function ping() {
  if (ws?.readyState !== WebSocket.OPEN) return;
  pendingPing = {id: ++pingId, at: performance.now()/1000};
  ws.send(JSON.stringify({type: 'ping', id: pendingPing.id}));
}
function connect() {
  ws = new WebSocket(`ws://${location.host}/samples`);
  rtt = Infinity;
  ws.onopen = ping;
  ws.onmessage = event => {
    const value = JSON.parse(event.data), now = performance.now()/1000;
    if (value.type === 'pong' && pendingPing?.id === value.id) {
      rtt = Math.max(0, now-pendingPing.at); pendingPing = null;
    } else if (value.type === 'sample') {
      // Account conservatively for local bridge transit without mixing clocks.
      latest = {...value, received_at: now - value.age - rtt};
    }
  };
  ws.onclose = () => { latest = null; monitor.reset(); reconnectTimer = setTimeout(connect, 1000); };
}
if (!mouseMode) connect();
const pingTimer = setInterval(ping, 1000);
window.addEventListener('pagehide', () => {
  clearTimeout(reconnectTimer); clearInterval(pingTimer);
  if (ws) { ws.onclose = null; ws.close(); }
});

function text(value, x, y, size = 24, color = '#adbdbe') {
  ctx.fillStyle = color; ctx.font = `${size}px system-ui`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(value, x, y);
}
function circle(x, y, radius, fill, stroke = null, width = 2) {
  ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI*2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
function newTarget() {
  const candidates = [.3, .5, .7].flatMap(x => [.37, .63].map(y => [1280*x, 720*y, 52]))
    .filter(p => Math.hypot(p[0]-target[0], p[1]-target[1]) > 140);
  target = candidates[Math.floor(Math.random()*candidates.length)];
}
function tick(ms) {
  const now = ms/1000;
  const sample = document.hasFocus() && !document.hidden ? (mouseMode
    ? {source: 'mouse-simulation', sequence: ++sequence, position: mouse, valid: !!mouse, mapped: true, received_at: now}
    : latest) : null;
  const frame = monitor.step(sample, now);
  const inside = frame.position && Math.hypot(frame.position[0]-target[0], frame.position[1]-target[1]) <= target[2];
  const fired = dwell.update(inside ? 'target' : null, frame);
  let ended = false;
  if (state === 'playing' && frame.ready && frame.fresh) {
    remaining = Math.max(0, remaining-frame.credit);
    if (!remaining) { state = 'result'; target = [640, 360, 62]; dwell.reset(); dwell.armed = false; ended = true; }
  }
  if (fired && !ended) {
    if (state !== 'playing') { state = 'playing'; score = 0; remaining = 30; }
    else score++;
    newTarget();
  }
  ctx.fillStyle = '#0d191f'; ctx.fillRect(0, 0, 1280, 720);
  for (let x = 40; x < 1280; x += 40) for (let y = 40; y < 720; y += 40) circle(x, y, 1, '#18282d');
  text('NEON / GAME INPUT', 640, 66, 24, '#89efd2');
  text(mouseMode ? 'MOUSE SIMULATION - NO NEON CONNECTED' : 'REAL NEON - COMPANION REQUIRED', 640, 101, 16);
  text(state === 'ready' ? 'Look. Hold. Collect.' : state === 'result' ? `Round complete - ${score} collected` : `${String(score).padStart(2, '0')} collected`, 640, 163, 44, '#ebf6f1');
  circle(...target, '#1e4c48', '#89efd2');
  text(state === 'ready' ? 'START' : state === 'result' ? 'AGAIN' : '+1', target[0], target[1], 22, '#ebf6f1');
  if (dwell.progress) {
    ctx.beginPath(); ctx.arc(target[0], target[1], target[2]+10, -Math.PI/2, -Math.PI/2 + 2*Math.PI*dwell.progress);
    ctx.strokeStyle = '#f2d386'; ctx.lineWidth = 5; ctx.stroke();
  }
  text(`${Math.ceil(remaining)}s active time`, 640, 580, 26);
  text(dwell.armed ? 'Look at the circle and hold for 0.6 seconds' : 'Look away from the target to rearm', 640, 625, 20, '#f2d386');
  label.textContent = mouseMode ? 'Mouse simulation · Game runs locally in this browser'
    : frame.usable ? (frame.ready ? 'Real mapped gaze · Local browser game' : 'Stabilizing gaze…')
    : `Waiting for real Neon gaze · ${frame.reason}`;
  const p = frame.usable ? frame.position : null;
  if (p && p[0] >= 0 && p[0] < 1280 && p[1] >= 0 && p[1] < 720) {
    trail = trail.filter(t => now-t[2] < .25);
    if (!trail.length || Math.hypot(p[0]-trail.at(-1)[0], p[1]-trail.at(-1)[1]) > 2) trail.push([...p, now]);
    trail = trail.slice(-40);
    for (const [x, y, at] of trail) circle(x, y, Math.max(1, 5*(1-(now-at)/.25)), '#3caa96');
    circle(...p, 7, null, '#effff9'); circle(...p, 2, '#8bf4d5');
  } else trail = [];
  if (!mouseMode) {
    const s = config.marker_size, m = config.margin;
    ctx.imageSmoothingEnabled = false;
    [[m, m], [1280-m-s, m], [1280-m-s, 720-m-s], [m, 720-m-s]].forEach(([x, y], i) => ctx.drawImage(tags[i], x, y, s, s));
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
