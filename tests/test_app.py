"""Headless regression tests for the QR preview and continuous scans."""
import re
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from concurrent.futures import Future

from PIL import Image

from qrcode_gui.app import QRCodeApp


class FakeCanvas:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.image_kwargs = None
        self.placeholder = None

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def delete(self, what):
        self.image_kwargs = None
        self.placeholder = None

    def create_image(self, x, y, **kwargs):
        self.image_kwargs = (x, y, kwargs)

    def create_text(self, x, y, **kwargs):
        self.placeholder = (x, y, kwargs)


class AppTests(unittest.TestCase):
    def test_qr_preview_fits_height_and_is_top_aligned(self):
        app = QRCodeApp.__new__(QRCodeApp)
        app.generated_image = Image.new("RGB", (950, 950), "white")
        app.generated_preview = None
        app.qr_canvas = FakeCanvas(220, 95)
        # No Tk window/display is necessary to exercise the resize logic.
        with patch("qrcode_gui.app.ImageTk.PhotoImage", side_effect=lambda im: im):
            app.update_qr_preview()
            x, y, props = app.qr_canvas.image_kwargs
            self.assertLessEqual(app.generated_preview.width, 218)
            self.assertLessEqual(app.generated_preview.height, 93)
            self.assertEqual(x, 110)
            self.assertEqual(y, 0)
            self.assertEqual(props["anchor"], "n")
            app.qr_canvas.height = 50
            app.update_qr_preview()
            self.assertLessEqual(app.generated_preview.height, 48)

    def test_empty_preview_uses_placeholder(self):
        app = QRCodeApp.__new__(QRCodeApp)
        app.generated_image = None
        app.generated_preview = None
        app.qr_canvas = FakeCanvas(220, 95)
        app.update_qr_preview()
        self.assertIsNone(app.qr_canvas.image_kwargs)
        self.assertIn("Generated QR", app.qr_canvas.placeholder[2]["text"])

    def test_accept_scan_sets_timestamp_with_seconds(self):
        app = QRCodeApp.__new__(QRCodeApp)
        app.last_scanned = None
        app.scan_result = Mock()
        app.camera_status = Mock()
        app.scan_timestamp = Mock()
        app.root = SimpleNamespace(bell=Mock())
        app.accept_scan("QR payload")
        app.scan_result.insert.assert_called_with("1.0", "QR payload")
        stamp = app.scan_timestamp.configure.call_args.kwargs["text"]
        self.assertRegex(stamp, r"Last scan: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        app.root.bell.assert_called_once()

    def test_successful_scan_does_not_stop_camera(self):
        app = QRCodeApp.__new__(QRCodeApp)
        app.decode_future = Future()
        app.decode_future.set_result("A QR code")
        app.camera_running = True
        app.decode_session = 4
        app.session_id = 4
        app.last_scanned = None
        app.accept_scan = Mock()
        app.stop_camera = Mock()
        app.check_decode_result()
        app.accept_scan.assert_called_once_with("A QR code")
        app.stop_camera.assert_not_called()
        self.assertTrue(app.camera_running)


if __name__ == "__main__":
    unittest.main()
