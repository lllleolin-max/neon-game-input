from math import isfinite
from .input import InputFrame


class Dwell:
    """One event per dwell. Rearm only after valid gaze leaves all targets."""
    def __init__(self, seconds=0.6, release_seconds=0.18):
        if not all(isfinite(v) and v > 0 for v in (seconds, release_seconds)):
            raise ValueError("Dwell and release durations must be positive")
        self.seconds, self.release_seconds = seconds, release_seconds
        self.reset()

    def reset(self):
        self.focus = None
        self.elapsed = 0.0
        self.armed = True
        self._outside = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed/self.seconds)

    def update(self, target: str | None, frame: InputFrame) -> str | None:
        if not frame.usable or not frame.ready:
            self.focus, self.elapsed, self._outside = None, 0.0, 0.0
            return None  # An unknown gaze must not rearm a fired control.
        if not frame.fresh:
            return None
        if target is None:
            self.focus, self.elapsed = None, 0.0
            self._outside += frame.credit
            if self._outside + 1e-9 >= self.release_seconds:
                self.armed = True
            return None
        self._outside = 0.0
        if not self.armed:
            return None
        if self.focus != target:
            self.focus, self.elapsed = target, 0.0
            return None  # The preceding interval belongs to the previous target.
        self.elapsed += frame.credit
        if self.elapsed + 1e-9 >= self.seconds:
            self.armed = False
            self.focus, self.elapsed = None, 0.0
            return target
        return None
