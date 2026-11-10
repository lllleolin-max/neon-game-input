import importlib.abc
import json
from pathlib import Path
import subprocess
import sys
import unittest

from neon_game_input import Circle, Dwell, InputFrame, InputMonitor, MouseInput, Sample, Surface
from neon_game_input.example_game import TargetGame


def sample(seq=1, at=1.0, **kwargs):
    values = dict(source="synthetic-test", sequence=seq, position=(640, 360), valid=True, mapped=True, received_at=at)
    values.update(kwargs)
    return Sample(**values)


class InputTests(unittest.TestCase):
    def test_core_does_not_import_optional_dependencies(self):
        result = subprocess.run([sys.executable, "-c", """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'pygame','numpy','cv2','aiohttp','pupil_labs'}:
            raise ImportError('optional dependency blocked')
sys.meta_path.insert(0, Block())
from neon_game_input import Surface, InputMonitor, NeonInput
assert Surface().width == 1280
"""], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_sample_cannot_earn_time(self):
        monitor = InputMonitor(recovery_seconds=0)
        monitor.step(sample(1, 1), 1)
        fresh = monitor.step(sample(2, 1.05), 1.05)
        repeated = monitor.step(sample(2, 1.05), 1.09)
        self.assertAlmostEqual(fresh.credit, .05)
        self.assertFalse(repeated.fresh)
        self.assertEqual(repeated.credit, 0)

    def test_stale_unmapped_nan_and_future_samples_are_rejected(self):
        for value in (sample(at=0), sample(mapped=False), sample(valid=False),
                      sample(position=(float('nan'), 0)), sample(at=2), sample(at=float('nan'))):
            with self.subTest(sample=value):
                frame = InputMonitor().step(value, 1)
                self.assertFalse(frame.usable)
                self.assertEqual(frame.credit, 0)

    def test_long_gap_requires_stabilization_and_no_catchup_credit(self):
        monitor = InputMonitor(recovery_seconds=.1)
        for seq in range(4):
            frame = monitor.step(sample(seq, seq*.05), seq*.05)
        self.assertTrue(frame.ready)
        recovered = monitor.step(sample(10, 1), 1)
        self.assertFalse(recovered.ready)
        self.assertEqual(recovered.credit, 0)

    def test_loss_clears_stabilization(self):
        monitor = InputMonitor(recovery_seconds=0)
        monitor.step(sample(1, 1), 1)
        monitor.step(None, 1.02)
        self.assertEqual(monitor.step(sample(2, 1.04), 1.04).credit, 0)

    def test_backwards_local_sample_is_rejected(self):
        monitor = InputMonitor(recovery_seconds=0)
        monitor.step(sample(1, 1), 1)
        self.assertEqual(monitor.step(sample(2, .99), 1).reason, 'nonmonotonic_sample')

    def test_outside_is_miss_not_loss_and_not_clamped(self):
        frame = InputMonitor(recovery_seconds=0).step(sample(position=(-1, 800)), 1)
        self.assertTrue(frame.usable)
        self.assertFalse(Surface().contains(frame.position))
        self.assertEqual(Surface().from_normalized(-.1, 1.1)[0], -128)

    def test_mouse_is_explicit_simulation(self):
        value = MouseInput().poll((1, 2), now=1)
        self.assertEqual(value.source, "mouse-simulation")

    def test_waiting_and_missing_dependency_reasons_survive_without_gaze(self):
        for reason in ('discovering', 'dependency_missing'):
            value = sample(valid=False, mapped=False, at=0, reason=reason)
            frame = InputMonitor().step(value, 10)
            self.assertFalse(frame.usable)
            self.assertEqual(frame.reason, reason)

    def test_shared_browser_vectors(self):
        vectors = json.loads(Path(__file__).with_name('input_vectors.json').read_text())
        monitor = InputMonitor(recovery_seconds=.1)
        for row in vectors:
            value = sample(row['seq'], row['at'], valid=row.get('valid', True))
            frame = monitor.step(value, row['now'])
            for key, expected in row['expect'].items():
                with self.subTest(row=row, key=key):
                    if key == 'credit':
                        self.assertAlmostEqual(getattr(frame, key), expected)
                    else:
                        self.assertEqual(getattr(frame, key), expected)


class GeometryTests(unittest.TestCase):
    def test_black_corners_exclude_white_border(self):
        self.assertEqual(Surface().marker_vertices()[0], [(40, 40), (168, 40), (168, 168), (40, 168)])

    def test_surface_is_configurable(self):
        self.assertEqual(Surface(1920, 1080, 120, 20).from_normalized(.5, .25), (960, 810))

    def test_letterbox_inverse_and_rejection(self):
        surface = Surface()
        self.assertEqual(surface.from_viewport((800, 600), (1600, 1200)), (640, 360))
        self.assertIsNone(surface.from_viewport((800, 100), (1600, 1200)))

    def test_bad_geometry_rejected(self):
        for args in ((100, 100), (1280, 720, 123), (1280, 720, 160, -1), (1280.5, 720)):
            with self.assertRaises(ValueError):
                Surface(*args)


class DwellTests(unittest.TestCase):
    frame = InputFrame((640, 360), True, True, True, .05)

    def test_fire_once_until_valid_leave(self):
        dwell = Dwell(.1, .1)
        self.assertIsNone(dwell.update('button', self.frame))
        self.assertIsNone(dwell.update('button', self.frame))
        self.assertEqual(dwell.update('button', self.frame), 'button')
        for _ in range(20):
            self.assertIsNone(dwell.update('button', self.frame))
        for _ in range(10):
            dwell.update(None, InputFrame())
        self.assertFalse(dwell.armed)
        for _ in range(2):
            dwell.update(None, self.frame)
        self.assertTrue(dwell.armed)

    def test_switch_target_and_loss_reset_progress(self):
        dwell = Dwell(.2)
        dwell.update('one', self.frame)
        dwell.update('one', self.frame)
        dwell.update('two', self.frame)
        self.assertEqual(dwell.progress, 0)
        dwell.update('two', self.frame)
        dwell.update(None, InputFrame())
        self.assertEqual(dwell.progress, 0)

    def test_repeated_frame_cannot_trigger(self):
        dwell = Dwell(.1)
        duplicate = InputFrame((0, 0), True, False, True, 0)
        dwell.update('button', self.frame)
        for _ in range(100):
            self.assertIsNone(dwell.update('button', duplicate))
        self.assertEqual(dwell.progress, 0)

    def test_complete_game_and_restart_with_synthetic_input(self):
        game = TargetGame(Surface(), duration=2)
        monitor = InputMonitor(recovery_seconds=0)
        now = 0

        def look(point, seconds):
            nonlocal now
            for _ in range(round(seconds/.02)):
                now += .02
                game.update(monitor.step(sample(round(now*100), now, position=point), now))

        look((640, 360), .8)
        self.assertEqual(game.state, 'playing')
        look((0, 0), .3)
        look((game.target.x, game.target.y), .8)
        self.assertEqual(game.score, 1)
        remaining = game.remaining
        for _ in range(20):
            game.update(InputFrame())
        self.assertEqual(game.remaining, remaining)
        look((0, 0), 2)
        self.assertEqual(game.state, 'result')
        look((0, 0), .3)
        look((640, 360), .8)
        self.assertEqual(game.state, 'playing')
        self.assertEqual(game.score, 0)
