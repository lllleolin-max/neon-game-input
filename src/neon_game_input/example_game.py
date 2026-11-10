"""Small reference game, deliberately separate from the reusable input API."""
import random
from .geometry import Circle, Surface
from .interaction import Dwell


class TargetGame:
    def __init__(self, surface: Surface, duration=30.0):
        if duration <= 0:
            raise ValueError("Duration must be positive")
        self.surface, self.duration = surface, duration
        self.dwell = Dwell()
        self.state, self.score, self.remaining = "ready", 0, duration
        self.target = Circle(surface.width/2, surface.height/2, 62)
        self._rng = random.Random()

    def update(self, frame):
        target_id = "target" if self.target.contains(frame.position) else None
        event = self.dwell.update(target_id, frame)
        if self.state == "playing" and frame.ready and frame.fresh:
            self.remaining = max(0, self.remaining-frame.credit)
            if self.remaining <= 0:
                self.state = "result"
                self.target = Circle(self.surface.width/2, self.surface.height/2, 62)
                self.dwell.reset()
                self.dwell.armed = False
                return
        if event:
            if self.state in {"ready", "result"}:
                self.score, self.remaining, self.state = 0, self.duration, "playing"
            else:
                self.score += 1
            # Keep targets clear of the markers and separate successive targets.
            w, h = self.surface.width, self.surface.height
            old = self.target
            positions = [(w*x, h*y) for x in (.30, .50, .70) for y in (.37, .63)]
            positions = [(x, y) for x, y in positions if not Circle(old.x, old.y, 140).contains((x, y))]
            self.target = Circle(*self._rng.choice(positions), 52)


def status_text(frame, mode):
    if frame.reason == "stabilizing":
        return "Hold steady - input is stabilizing"
    if frame.usable:
        return "Look at the circle. Hold for 0.6s. Look away to rearm."
    if mode == "mouse":
        return "Move the mouse inside the window - no click needed"
    return {
        "no_sample": "Starting Neon...",
        "discovering": "Looking for Neon Companion on the local network...",
        "device_not_found": "Companion not found - check network or use --address",
        "dependency_missing": "Install the neon extra: pip install -e .[neon]",
        "not_worn": "Put on Neon and look at the screen",
        "markers_missing": "Keep all four corner markers visible to the scene camera",
        "surface_not_located": "Connected - waiting for the four screen markers",
        "device_error": "Connection error - retrying; run neon-game-check for diagnostics",
        "window_unfocused": "Paused - return to the game window",
        "stale_sample": "Paused - waiting for fresh gaze samples",
        "stream_timeout": "Stream interrupted - waiting for new data",
    }.get(frame.reason, "Input unavailable: " + frame.reason)
