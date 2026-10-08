"""Decode dense QR codes using ZXing-C++ with an OpenCV fallback.

Never resize camera frames *down* to the on-screen preview resolution before
decoding. With dense symbols, the amount of captured detail is critical.
"""
import cv2

try:
    import zxingcpp
except ImportError:
    zxingcpp = None


def decode_qr(frame):
    """Return decoded text or empty string; accepts OpenCV BGR or grayscale."""
    if frame is None or not getattr(frame, "size", 0):
        return ""
    if zxingcpp is not None:
        try:
            code = zxingcpp.read_barcode(
                frame, formats=zxingcpp.BarcodeFormat.QRCode,
                try_rotate=True, try_downscale=True, try_invert=True,
            )
            if code and code.text:
                return code.text
        except Exception:
            pass

    detector = cv2.QRCodeDetector()
    # Two gentle contrast strategies help with low-light/screen QR codes.
    frames = [frame]
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        frames.append(gray)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        frames.append(clahe.apply(gray))
        if min(gray.shape[:2]) <= 720:
            frames.append(cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    except cv2.error:
        pass

    for candidate in frames:
        try:
            value, _, _ = detector.detectAndDecode(candidate)
            if value:
                return value
        except cv2.error:
            continue
    return ""
