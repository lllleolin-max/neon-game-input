"""Synthetic images through the real SDK. These tests do not use Neon hardware."""
from importlib.resources import files
import unittest

from neon_game_input import Surface

try:
    import cv2
    import numpy as np
    from pupil_labs.realtime_api import GazeData
    from pupil_labs.neon_recording.calib import Calibration
    from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper
    AVAILABLE = True
except (ImportError, OSError):
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Install the neon extra to test the official mapper')
class OfficialMapperTests(unittest.TestCase):
    def setup_surface(self, surface):
        image = np.full((surface.height, surface.width, 3), 25, dtype=np.uint8)
        for tag, rect in surface.marker_rects().items():
            data = files('neon_game_input').joinpath(f'assets/tag36h11_{tag}.png').read_bytes()
            marker = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            marker = cv2.resize(marker, (surface.marker_size,)*2, interpolation=cv2.INTER_NEAREST)
            x, y, s = int(rect.x), int(rect.y), surface.marker_size
            image[y:y+s, x:x+s] = marker
        source = np.zeros(1, dtype=Calibration.dtype)
        source['scene_camera_matrix'][0] = [[1000,0,surface.width/2], [0,1000,surface.height/2], [0,0,1]]
        mapper = GazeMapper(Calibration(source))
        mapped_surface = mapper.add_surface(surface.marker_vertices(), (surface.width, surface.height))
        return image, mapper, mapped_surface.uid

    def test_four_tags_and_orientation_at_multiple_canvas_sizes(self):
        for surface in (Surface(), Surface(1920,1080,120,24), Surface(1000,800,100,20)):
            with self.subTest(surface=surface):
                image, mapper, uid = self.setup_surface(surface)
                for x,y in ((surface.width*.3,surface.height*.4),(surface.width*.7,surface.height*.6)):
                    result = mapper.process_frame(image, GazeData(x,y,True,123))
                    self.assertEqual({int(str(m.uid).split(':')[-1]) for m in result.markers}, {0,1,2,3})
                    p = result.mapped_gaze[uid][0]
                    actual = surface.from_normalized(p.x,p.y)
                    self.assertAlmostEqual(actual[0],x,delta=3)
                    self.assertAlmostEqual(actual[1],y,delta=3)

    def test_perspective_and_resized_canvas_round_trip(self):
        surface = Surface()
        for transform in (np.array([[.92,-.02,40],[.01,.92,20],[.00002,.00001,1]]),
                          np.array([[1.5,0,0],[0,1.5,0],[0,0,1.]])):
            image, mapper, uid = self.setup_surface(surface)
            image = cv2.warpPerspective(image,transform,(1920,1080),borderValue=(25,25,25))
            for x,y in ((400,300),(900,470)):
                p = cv2.perspectiveTransform(np.array([[[x,y]]],dtype=float),transform)[0,0]
                result = mapper.process_frame(image,GazeData(*p,True,123))
                gaze = result.mapped_gaze[uid][0]
                actual = surface.from_normalized(gaze.x,gaze.y)
                self.assertAlmostEqual(actual[0],x,delta=3)
                self.assertAlmostEqual(actual[1],y,delta=3)

    def test_blank_image_cannot_supply_screen_gaze(self):
        image, mapper, uid = self.setup_surface(Surface())
        result = mapper.process_frame(np.full_like(image,25),GazeData(640,360,True,123))
        self.assertFalse(result.mapped_gaze[uid])
