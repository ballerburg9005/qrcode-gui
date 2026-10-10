import unittest
from unittest.mock import patch

from qrcode_gui.camera import camera_candidates, capture_modes, open_camera


class FakeFrame:
    def __init__(self, width=640, height=480):
        self.shape = (height, width, 3)
        self.size = width * height * 3


class FakeCapture:
    def __init__(self, frames, reported_fps=30):
        self.frames = list(frames)
        self.released = False
        self.reported_fps = reported_fps
        self.properties = {}

    def isOpened(self):
        return True

    def read(self):
        if not self.frames:
            return False, None
        return self.frames.pop(0)

    def set(self, prop, value):
        self.properties[prop] = value
        return True

    def get(self, prop):
        return self.reported_fps if prop == FakeCV.CAP_PROP_FPS else self.properties.get(prop, 0)

    def release(self):
        self.released = True


class FakeCV:
    CAP_V4L2 = 200
    CAP_ANY = 0
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5
    CAP_PROP_FOURCC = 6

    def __init__(self, captures):
        self.captures = list(captures)

    def VideoCapture(self, device, backend):
        return self.captures.pop(0)

    @staticmethod
    def VideoWriter_fourcc(*letters):
        return 1196444237


class CameraTests(unittest.TestCase):
    @patch("qrcode_gui.camera.video_devices", return_value=["/dev/video0", "/dev/video2"])
    def test_auto_candidates(self, _mock):
        self.assertEqual(
            camera_candidates(), ["/dev/video0", "/dev/video2", 0, 1, 2, 3]
        )

    def test_fast_capture_prefs_start_with_hd_then_vga(self):
        self.assertEqual(
            capture_modes("High FPS (auto)")[:2],
            [((1280, 720), 60), ((640, 480), 60)],
        )

    def test_rejects_unreadable_and_uses_fallback(self):
        broken = FakeCapture([(False, None)] * 6)
        working = FakeCapture([(True, FakeFrame())], reported_fps=60)
        capture, label, error = open_camera(FakeCV([broken, working]), "Camera 0")
        self.assertIs(capture, working)
        self.assertEqual(label, "0")
        self.assertIsNone(error)
        self.assertTrue(broken.released)
        self.assertFalse(working.released)

    def test_high_resolution_falls_back_to_slow_mode(self):
        bad = FakeCapture([(False, None)] * 6)
        good = FakeCapture([(True, FakeFrame(1920, 1080))])
        cap, _, err = open_camera(FakeCV([bad, good]), "Camera 0", "Full HD 1920x1080")
        self.assertIs(cap, good)
        self.assertIsNone(err)
        self.assertTrue(bad.released)

    def test_prefers_real_60_fps_over_30_fps_hd(self):
        hd_slow = FakeCapture([(True, FakeFrame(1280, 720))], reported_fps=30)
        vga_fast = FakeCapture([(True, FakeFrame())], reported_fps=60)
        cv = FakeCV([hd_slow, vga_fast])
        cap, _, err = open_camera(cv, "Camera 0")
        self.assertIs(cap, vga_fast)
        self.assertIsNone(err)
        self.assertTrue(hd_slow.released)
        self.assertEqual(vga_fast.properties[cv.CAP_PROP_FRAME_WIDTH], 640)
        self.assertEqual(vga_fast.properties[cv.CAP_PROP_FPS], 60)

    def test_rejects_frames_below_minimum_despite_successful_reads(self):
        too_small = FakeCapture([(True, FakeFrame(320, 240))], reported_fps=60)
        valid = FakeCapture([(True, FakeFrame(640, 480))], reported_fps=60)
        cap, _, err = open_camera(FakeCV([too_small, valid]), "Camera 0")
        self.assertIs(cap, valid)
        self.assertIsNone(err)
        self.assertTrue(too_small.released)

    def test_default_mode_also_enforces_minimum(self):
        too_small = FakeCapture([(True, FakeFrame(320, 240))])
        valid = FakeCapture([(True, FakeFrame(640, 480))], reported_fps=60)
        cap, _, err = open_camera(FakeCV([too_small, valid]), "Camera 0", "Default")
        self.assertIs(cap, valid)
        self.assertIsNone(err)

    def test_no_camera_import(self):
        capture, device, error = open_camera(None)
        self.assertIsNone(capture)
        self.assertIn("OpenCV", error)


if __name__ == "__main__":
    unittest.main()
