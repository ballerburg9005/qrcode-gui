import unittest
from unittest.mock import patch

import cv2
import numpy as np

from qrcode_gui.decoder import decode_qr
from qrcode_gui.qr import create_qr_image


class DecodingTests(unittest.TestCase):
    def test_decodes_dense_qr(self):
        payload = "dense-QR-" + "".join(chr(32 + (i * 23) % 95) for i in range(1200))
        rgb = np.array(create_qr_image(payload))
        # A full-res camera still needs many pixels per tiny QR module.
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        self.assertEqual(decode_qr(bgr), payload)

    def test_decodes_generated_qr(self):
        payload = "https://example.org/a?b=1"
        bgr = cv2.cvtColor(np.array(create_qr_image(payload)), cv2.COLOR_RGB2BGR)
        self.assertEqual(decode_qr(bgr), payload)

    def test_empty_image(self):
        self.assertEqual(decode_qr(None), "")

    def test_uses_opencv_if_zxing_missing(self):
        payload = "fallback works"
        bgr = cv2.cvtColor(np.array(create_qr_image(payload)), cv2.COLOR_RGB2BGR)
        with patch("qrcode_gui.decoder.zxingcpp", None):
            self.assertEqual(decode_qr(bgr), payload)


if __name__ == "__main__":
    unittest.main()
