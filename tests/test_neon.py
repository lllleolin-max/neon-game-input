import sys
import time
import types
import unittest
from unittest.mock import Mock, patch

from neon_game_input import NeonInput, Surface


class NeonTests(unittest.TestCase):
    def setUp(self):
        self.neon = NeonInput(Surface())
        self.gaze = types.SimpleNamespace(x=640., y=360., worn=True, timestamp_unix_seconds=123.)
        self.mapper = Mock()
        self.mapper.process_frame.return_value = types.SimpleNamespace(
            markers=[types.SimpleNamespace(uid=f'tag36h11:{i}') for i in range(4)],
            mapped_gaze={'surface': [types.SimpleNamespace(x=.25, y=.75)]})

    def process(self, previous=None, received=10):
        with patch('neon_game_input.neon.time.monotonic', return_value=10):
            self.neon._process_pair(self.mapper, 'surface', (object(), self.gaze), previous, received)
        return self.neon.poll(10)

    def test_real_sdk_result_contract_maps_canvas(self):
        value = self.process()
        self.assertTrue(value.valid)
        self.assertEqual(value.position, (320, 180))
        self.assertEqual(value.markers, (0,1,2,3))

    def test_unworn_or_duplicate_never_enters_mapper(self):
        self.gaze.worn = False
        self.assertEqual(self.process().reason, 'not_worn')
        self.gaze.worn = True
        self.assertEqual(self.process(previous=123).reason, 'duplicate_device_sample')
        self.mapper.process_frame.assert_not_called()

    def test_missing_markers_and_surface_never_fabricate_coordinates(self):
        self.mapper.process_frame.return_value.markers = []
        self.assertEqual(self.process().reason, 'markers_missing')
        self.neon.require_all_markers = False
        self.mapper.process_frame.return_value.mapped_gaze = {}
        value = self.process()
        self.assertEqual(value.reason, 'surface_not_located')
        self.assertIsNone(value.position)

    def test_processing_age_includes_mapper_time(self):
        self.assertEqual(self.process(received=9).reason, 'processing_too_slow')
        self.assertEqual(self.neon._sample.reason, 'processing_too_slow')

    def test_invalid_coordinates_are_rejected(self):
        self.gaze.x = float('nan')
        self.assertEqual(self.process().reason, 'invalid_gaze')
        self.mapper.process_frame.assert_not_called()

    def test_poll_hides_on_blur_and_close(self):
        self.process()
        self.assertEqual(self.neon.poll(10, focused=False).reason, 'window_unfocused')
        self.neon.close()
        self.assertFalse(self.neon.poll(10).valid)
        with self.assertRaises(RuntimeError):
            self.neon.start()

    def run_device(self, version, address=None):
        neon = NeonInput(address=address)
        device = Mock(version_glasses=version)
        mapper = Mock()
        mapper.add_surface.return_value = types.SimpleNamespace(uid='surface')
        mapper.process_frame = self.mapper.process_frame
        def receive(**kwargs):
            neon._stop.set()
            return object(), self.gaze
        device.receive_matched_scene_video_frame_and_gaze.side_effect = receive
        api = types.ModuleType('pupil_labs.realtime_api.simple')
        api.Device = Mock(return_value=device)
        api.discover_one_device = Mock(return_value=device)
        mapping = types.ModuleType('pupil_labs.real_time_screen_gaze.gaze_mapper')
        mapping.GazeMapper = Mock(return_value=mapper)
        with patch.dict(sys.modules, {api.__name__: api, mapping.__name__: mapping}), \
                patch.object(neon._stop, 'wait', side_effect=lambda _: neon._stop.set()):
            neon._run()
        device.close.assert_called_once()
        self.assertFalse(neon.connected)
        return neon._sample, api, mapping

    def test_hardware_version_compatibility_and_discovery(self):
        for version in ('2', '2.0', 2, 2.0):
            with self.subTest(version=version):
                value, api, _ = self.run_device(version)
                self.assertTrue(value.valid)
                api.discover_one_device.assert_called_once()
                api.Device.assert_not_called()

    def test_unsupported_device_rejected(self):
        for version in ('1', None, '20'):
            value, _, mapping = self.run_device(version)
            self.assertEqual(value.reason, 'unsupported_device')
            mapping.GazeMapper.assert_not_called()

    def test_explicit_address_uses_sdk_device(self):
        value, api, _ = self.run_device('2.0', '192.0.2.1')
        self.assertTrue(value.valid)
        api.Device.assert_called_once_with('192.0.2.1', 8080)
        api.discover_one_device.assert_not_called()
