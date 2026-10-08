import unittest
from unittest.mock import patch

from qrcode_gui.camera import camera_candidates, open_camera


class FakeFrame:
    size = 10


class FakeCapture:
    def __init__(self, frames):
        self.frames = list(frames)
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        if not self.frames:
            return False, None
        return self.frames.pop(0)

    def release(self):
        self.released = True


class FakeCV:
    CAP_V4L2 = 200
    CAP_ANY = 0

    def __init__(self, captures):
        self.captures = list(captures)

    def VideoCapture(self, device, backend):
        return self.captures.pop(0)


class CameraTests(unittest.TestCase):
    @patch("qrcode_gui.camera.video_devices", return_value=["/dev/video0", "/dev/video2"])
    def test_auto_candidates(self, _mock):
        self.assertEqual(
            camera_candidates(), ["/dev/video0", "/dev/video2", 0, 1, 2, 3]
        )

    def test_rejects_unreadable_and_uses_fallback(self):
        broken = FakeCapture([(False, None)] * 5)
        working = FakeCapture([(True, FakeFrame())])
        capture, label, error = open_camera(FakeCV([broken, working]), "Camera 0")
        self.assertIs(capture, working)
        self.assertEqual(label, "0")
        self.assertIsNone(error)
        self.assertTrue(broken.released)
        self.assertFalse(working.released)

    def test_no_camera_import(self):
        capture, device, error = open_camera(None)
        self.assertIsNone(capture)
        self.assertIn("OpenCV", error)


if __name__ == "__main__":
    unittest.main()
