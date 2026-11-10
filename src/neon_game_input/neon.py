"""Official Neon SDK adapter. Video is mapped in memory and never saved."""
from dataclasses import replace
import math
import threading
import time

from .geometry import Surface
from .input import Sample


class NeonInput:
    source = "neon"

    def __init__(self, surface: Surface | None = None, *, address: str | None = None,
                 port: int = 8080, max_age: float = 0.15, discovery_seconds: float = 3,
                 retry_seconds: float = 2, require_all_markers: bool = True):
        if not 1 <= port <= 65535:
            raise ValueError("Invalid Companion port")
        if not all(math.isfinite(v) and v > 0 for v in (max_age, discovery_seconds, retry_seconds)):
            raise ValueError("Timeouts must be positive and finite")
        self.surface = surface or Surface()
        self.address, self.port = (address or "").strip(), port
        self.max_age, self.discovery_seconds, self.retry_seconds = max_age, discovery_seconds, retry_seconds
        self.require_all_markers = require_all_markers
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._sample = None
        self._sequence = 0
        self._connected = False
        self._error = ""

    @property
    def connected(self):
        with self._lock:
            return self._connected

    @property
    def error(self):
        """Local diagnostic text; do not publish without checking for addresses."""
        with self._lock:
            return self._error

    def start(self):
        if self._stop.is_set():
            raise RuntimeError("A closed NeonInput cannot restart; create a new instance")
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="neon-game-mapper", daemon=True)
            self._thread.start()
        return self

    def poll(self, now=None, *, focused=True):
        now = time.monotonic() if now is None else now
        with self._lock:
            sample = self._sample
        if sample:
            if self._stop.is_set():
                return replace(sample, valid=False, reason="closed")
            if not focused:
                return replace(sample, valid=False, reason="window_unfocused")
            if sample.valid and now-sample.received_at > self.max_age:
                return replace(sample, valid=False, reason="stale_sample")
        return sample

    def _publish(self, *, position=None, valid=False, mapped=False, received=None,
                 timestamp=None, reason="", markers=(), error=""):
        with self._lock:
            self._sequence += 1
            self._sample = Sample(self.source, self._sequence, position, valid, mapped,
                                  time.monotonic() if received is None else received,
                                  timestamp, reason, tuple(markers))
            self._error = error

    def _process_pair(self, mapper, surface_id, pair, previous_timestamp, received):
        frame, gaze = pair
        stamp = float(gaze.timestamp_unix_seconds)
        if not math.isfinite(stamp) or (previous_timestamp is not None and stamp <= previous_timestamp):
            self._publish(reason="duplicate_device_sample", received=received)
            return previous_timestamp
        if not gaze.worn:
            self._publish(reason="not_worn", received=received, timestamp=stamp)
            return stamp
        if not all(math.isfinite(v) for v in (gaze.x, gaze.y)):
            self._publish(reason="invalid_gaze", received=received, timestamp=stamp)
            return stamp
        result = mapper.process_frame(frame, gaze)
        markers = tuple(int(str(m.uid).split(":")[-1]) for m in result.markers) if result else ()
        mapped = result.mapped_gaze.get(surface_id, []) if result else []
        data = dict(received=received, timestamp=stamp, markers=markers)
        if time.monotonic()-received > self.max_age:
            self._publish(reason="processing_too_slow", **data)
        elif self.require_all_markers and not set(self.surface.marker_rects()).issubset(markers):
            self._publish(reason="markers_missing", **data)
        elif not mapped:
            self._publish(reason="surface_not_located", **data)
        else:
            point = mapped[-1]
            position = self.surface.from_normalized(float(point.x), float(point.y))
            valid = all(math.isfinite(v) for v in position)
            self._publish(position=position if valid else None, valid=valid, mapped=True,
                          reason="" if valid else "invalid_gaze", **data)
        return stamp

    def _run(self):
        try:
            from pupil_labs.realtime_api.simple import Device, discover_one_device
            from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper
        except (ImportError, OSError) as exc:
            self._publish(reason="dependency_missing", error=str(exc))
            return
        while not self._stop.is_set():
            device = None
            try:
                self._publish(reason="discovering")
                device = (Device(self.address, self.port) if self.address else
                          discover_one_device(max_search_duration_seconds=self.discovery_seconds))
                if device is None:
                    self._publish(reason="device_not_found")
                    continue
                if self._stop.is_set():
                    break
                if str(device.version_glasses).strip() not in {"2", "2.0"}:
                    self._publish(reason="unsupported_device")
                    continue
                mapper = GazeMapper(device.get_calibration())
                surface = mapper.add_surface(self.surface.marker_vertices(),
                                             (self.surface.width, self.surface.height), name="Game canvas")
                with self._lock:
                    if self._stop.is_set():
                        break
                    self._connected = True
                self._publish(reason="surface_not_located")
                previous, last_pair = None, time.monotonic()
                while not self._stop.is_set():
                    pair = device.receive_matched_scene_video_frame_and_gaze(timeout_seconds=0.25)
                    received = time.monotonic()
                    if pair is None:
                        self._publish(reason="stream_timeout")
                        if received-last_pair > 5:
                            break
                        continue
                    last_pair = received
                    previous = self._process_pair(mapper, surface.uid, pair, previous, received)
            except Exception as exc:
                self._publish(reason="device_error", error=f"{type(exc).__name__}: {exc}")
            finally:
                with self._lock:
                    self._connected = False
                if device is not None:
                    try:
                        device.close()
                    except Exception:
                        pass
                self._stop.wait(self.retry_seconds)

    def close(self, timeout=0.0) -> bool:
        """Signal shutdown; optional bounded join. True means the worker has stopped.

        SDK discovery/calibration/decoder calls can outlive timeout. The daemon
        closes its own device in finally; never block a game loop waiting on it.
        """
        self._stop.set()
        with self._lock:
            self._connected = False
        if self._thread:
            self._thread.join(timeout=max(0, timeout))
            return not self._thread.is_alive()
        return True

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()
