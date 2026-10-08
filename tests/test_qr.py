import unittest

from qrcode_gui.qr import create_qr_image


class QRGenerationTests(unittest.TestCase):
    def test_generates_rgb_image(self):
        image = create_qr_image("https://example.org")
        self.assertEqual(image.mode, "RGB")
        self.assertGreater(image.width, 100)

    def test_rejects_blank(self):
        with self.assertRaises(ValueError):
            create_qr_image("  ")


if __name__ == "__main__":
    unittest.main()
