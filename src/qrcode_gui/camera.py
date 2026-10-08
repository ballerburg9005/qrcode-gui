"""Linux-friendly camera discovery with driver-backend fallbacks."""
import glob
import re
import sys


def video_devices():
    """Video nodes are sorted numerically; some nodes are metadata only."""
    return sorted(
        glob.glob("/dev/video[0-9]*"),
        key=lambda name: int(re.search(r"(\d+)$", name).group(1)),
    )


def choices():
    return ["Automatic", *video_devices(), *[f"Camera {i}" for i in range(4)]]


def camera_candidates(selected="Automatic"):
    if selected.startswith("Camera "):
        try:
            return [int(selected.split()[-1])]
        except ValueError:
            return []
    if selected != "Automatic":
        return [selected]
    # Indexed capture can work on devices not listed in the container.
    return [*video_devices(), *range(4)]


def open_camera(cv, selected="Automatic"):
    """Return (capture, device, error); only keep a capture that reads frames.

    Avoid changing resolution or V4L2 buffer settings: those mode changes
    can cause read() failures immediately after a successful first frame.
    """
    if cv is None:
        return None, None, "OpenCV is not installed."
    candidates = camera_candidates(selected)
    if not candidates:
        return None, None, "No camera device was found."
    backends = [getattr(cv, "CAP_V4L2", 200)] if sys.platform == "linux" else []
    backends.append(getattr(cv, "CAP_ANY", 0))
    for device in candidates:
        for backend in dict.fromkeys(backends):
            capture = None
            keep = False
            try:
                capture = cv.VideoCapture(device, backend)
                if not capture or not capture.isOpened():
                    continue
                for _ in range(5):
                    ok, frame = capture.read()
                    if ok and frame is not None and getattr(frame, "size", 0):
                        keep = True
                        return capture, str(device), None
            except Exception:
                pass
            finally:
                if capture is not None and not keep:
                    capture.release()
    return None, None, (
        "Unable to read camera frames. Close other webcam applications, "
        "try a different /dev/video device, and for Snap installations run "
        "'sudo snap connect qrcode-gui:camera'."
    )
