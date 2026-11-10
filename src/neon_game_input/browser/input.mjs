// Browser counterpart of InputMonitor and Dwell. No framework or network imports.
export class InputMonitor {
  constructor({maxAge = .15, maxGap = .10, recovery = .20} = {}) {
    this.maxAge = maxAge; this.maxGap = maxGap; this.recovery = recovery;
    this.reset();
  }
  reset() { this.key = null; this.last = null; this.stableSince = null; }
  step(sample, now) {
    let age = 0, reason = 'no_sample';
    if (sample) {
      age = now - sample.received_at;
      reason = sample.reason || 'invalid_sample';
      if (!sample.valid || !sample.mapped) reason = sample.reason || (!sample.valid ? 'invalid_sample' : 'surface_not_located');
      else if (!Number.isFinite(age) || age < -.01) reason = 'invalid_local_timestamp';
      else if (age > this.maxAge) reason = 'stale_sample';
      else if (sample.valid && sample.mapped && Array.isArray(sample.position)
          && sample.position.length === 2 && sample.position.every(Number.isFinite)) {
        const key = `${sample.source}:${sample.sequence}`, fresh = key !== this.key;
        let credit = 0;
        if (fresh) {
          const gap = this.last === null ? null : sample.received_at - this.last;
          if (gap !== null && gap <= 0) {
            this.last = this.stableSince = null;
            return {usable: false, fresh: false, ready: false, credit: 0, reason: 'nonmonotonic_sample'};
          }
          if (gap === null || gap > this.maxGap) this.stableSince = sample.received_at;
          else credit = gap;
          this.last = sample.received_at; this.key = key;
        }
        const ready = this.stableSince !== null && sample.received_at - this.stableSince + 1e-9 >= this.recovery;
        return {position: sample.position, usable: true, fresh, ready,
          credit: ready ? credit : 0, age: Math.max(0, age), reason: ready ? '' : 'stabilizing'};
      }
    }
    this.last = this.stableSince = null;
    return {position: null, usable: false, fresh: false, ready: false, credit: 0,
      age: Number.isFinite(age) ? Math.max(0, age) : 0, reason};
  }
}

export class Dwell {
  constructor(seconds = .6, releaseSeconds = .18) {
    this.seconds = seconds; this.releaseSeconds = releaseSeconds; this.reset();
  }
  reset() { this.focus = null; this.elapsed = 0; this.armed = true; this.outside = 0; }
  get progress() { return Math.min(1, this.elapsed / this.seconds); }
  update(target, frame) {
    if (!frame.usable || !frame.ready) {
      this.focus = null; this.elapsed = this.outside = 0; return null;
    }
    if (!frame.fresh) return null;
    if (target === null) {
      this.focus = null; this.elapsed = 0; this.outside += frame.credit;
      if (this.outside + 1e-9 >= this.releaseSeconds) this.armed = true;
      return null;
    }
    this.outside = 0;
    if (!this.armed) return null;
    if (this.focus !== target) { this.focus = target; this.elapsed = 0; return null; }
    this.elapsed += frame.credit;
    if (this.elapsed + 1e-9 >= this.seconds) {
      this.armed = false; this.focus = null; this.elapsed = 0; return target;
    }
    return null;
  }
}

export function canvasPoint(clientX, clientY, rect, width, height) {
  const x = (clientX - rect.left) * width / rect.width;
  const y = (clientY - rect.top) * height / rect.height;
  return x >= 0 && x < width && y >= 0 && y < height ? [x, y] : null;
}
