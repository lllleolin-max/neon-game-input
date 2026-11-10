from dataclasses import dataclass
from math import isfinite
import time

from .geometry import Point


@dataclass(frozen=True)
class Sample:
    source: str
    sequence: int
    position: Point | None
    valid: bool
    mapped: bool
    received_at: float
    device_timestamp: float | None = None
    reason: str = ""
    markers: tuple[int, ...] = ()


@dataclass(frozen=True)
class InputFrame:
    position: Point | None = None
    usable: bool = False
    fresh: bool = False
    ready: bool = False
    credit: float = 0.0
    age: float = 0.0
    reason: str = "no_sample"


class InputMonitor:
    """Validate latest samples and credit only newly observed time intervals.

    A fresh cursor may appear during stabilization, but ready gates interaction.
    Device Unix timestamps are never subtracted from the local monotonic clock.
    """
    def __init__(self, max_age=0.15, max_gap=0.10, recovery_seconds=0.20):
        if (not all(isfinite(v) for v in (max_age, max_gap, recovery_seconds))
                or min(max_age, max_gap) <= 0 or recovery_seconds < 0):
            raise ValueError("Age/gap must be positive and recovery must be nonnegative")
        self.max_age, self.max_gap, self.recovery_seconds = max_age, max_gap, recovery_seconds
        self.reset()

    def reset(self):
        self._key = None
        self._last = None
        self._stable_since = None

    def step(self, sample: Sample | None, now: float | None = None) -> InputFrame:
        now = time.monotonic() if now is None else now
        reason, age = "no_sample", 0.0
        if sample:
            age = now - sample.received_at
            reason = sample.reason or "invalid_sample"
            if not sample.valid or not sample.mapped:
                reason = sample.reason or ("invalid_sample" if not sample.valid else "surface_not_located")
            elif not isfinite(age) or age < -0.01:
                reason = "invalid_local_timestamp"
            elif age > self.max_age:
                reason = "stale_sample"
            elif (sample.valid and sample.mapped and sample.position is not None
                  and len(sample.position) == 2 and all(isfinite(v) for v in sample.position)):
                key = (sample.source, sample.sequence)
                fresh = key != self._key
                credit = 0.0
                if fresh:
                    gap = sample.received_at - self._last if self._last is not None else None
                    if gap is not None and gap <= 0:
                        self._last = self._stable_since = None
                        return InputFrame(reason="nonmonotonic_sample")
                    if gap is None or gap > self.max_gap:
                        self._stable_since = sample.received_at
                    else:
                        credit = gap
                    self._last, self._key = sample.received_at, key
                ready = (self._stable_since is not None
                         and sample.received_at-self._stable_since + 1e-9 >= self.recovery_seconds)
                return InputFrame(sample.position, True, fresh, ready,
                                  credit if ready else 0.0, max(0, age),
                                  "" if ready else "stabilizing")
        self._last = self._stable_since = None
        return InputFrame(age=max(0, age) if isfinite(age) else 0.0, reason=reason)


class MouseInput:
    """Explicit simulation source for demos, never a fallback from real Neon."""
    source = "mouse-simulation"

    def __init__(self):
        self._sequence = 0

    def poll(self, position: Point | None, *, focused=True, now=None) -> Sample:
        self._sequence += 1
        return Sample(self.source, self._sequence, position, focused and position is not None,
                      True, time.monotonic() if now is None else now,
                      reason="" if focused else "window_unfocused")
