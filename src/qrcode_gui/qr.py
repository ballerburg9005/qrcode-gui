"""Generate QR images without any external CLI dependency."""
import qrcode
from PIL import Image


def create_qr_image(content: str) -> Image.Image:
    if not content.strip():
        raise ValueError("Enter text or a URL.")
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")
