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


# The automatic mode tries a fast HD stream first, then fast VGA, and
# finally widely supported 30 FPS modes. All accepted frames must be at
# least 640x480, even if the driver ignores our requested dimensions.
MIN_FRAME_WIDTH = 640
MIN_FRAME_HEIGHT = 480
RESOLUTIONS = {
    "High FPS (auto)": None,
    "Default": None,
    "VGA 640x480": (640, 480),
    "HD 1280x720": (1280, 720),
    "Full HD 1920x1080": (1920, 1080),
}


def capture_modes(resolution):
    """List (dimensions, target FPS) in order of preference."""
    if resolution == "High FPS (auto)":
        return [
            ((1280, 720), 60),
            ((640, 480), 60),
            ((1280, 720), 30),
            ((640, 480), 30),
            (None, None),
        ]
    if resolution == "Default":
        return [(None, None), ((640, 480), 60), ((640, 480), 30)]
    size = RESOLUTIONS.get(resolution)
    if size is None:
        size = (640, 480)
    # Respect a manually chosen resolution first. Fall back only when
    # the requested stream cannot provide valid frames.
    modes = [(size, 60), (size, 30)]
    if size != (1280, 720):
        modes.append(((1280, 720), 30))
    if size != (640, 480):
        modes.append(((640, 480), 30))
    modes.append((None, None))
    return modes


def open_camera(cv, selected="Automatic", resolution="High FPS (auto)"):
    """Return (capture, device, error), preferring fast >=640x480 video.

    Prefer 60 FPS, but accept 30 FPS or a valid driver default when higher
    FPS is unavailable. VideoCapture properties are advisory: reject an
    undersized *actual frame*, regardless of what set() returned.
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
            for dimensions, fps in capture_modes(resolution):
                capture = None
                keep = False
                try:
                    capture = cv.VideoCapture(device, backend)
                    if not capture or not capture.isOpened():
                        continue
                    # MJPG frequently enables faster frame rates on USB cameras.
                    if dimensions and hasattr(cv, "CAP_PROP_FOURCC") and hasattr(cv, "VideoWriter_fourcc"):
                        capture.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*"MJPG"))
                    if dimensions:
                        capture.set(cv.CAP_PROP_FRAME_WIDTH, dimensions[0])
                        capture.set(cv.CAP_PROP_FRAME_HEIGHT, dimensions[1])
                    if fps and hasattr(cv, "CAP_PROP_FPS"):
                        capture.set(cv.CAP_PROP_FPS, fps)
                    for _ in range(6):
                        ok, frame = capture.read()
                        if not ok or frame is None or not getattr(frame, "size", 0):
                            continue
                        # OpenCV arrays always expose shape, so validate the
                        # stream itself rather than relying on CAP_PROP_*.
                        shape = getattr(frame, "shape", None)
                        if shape is None or len(shape) < 2:
                            continue
                        height, width = shape[:2]
                        if width < MIN_FRAME_WIDTH or height < MIN_FRAME_HEIGHT:
                            break
                        if fps == 60 and resolution == "High FPS (auto)":
                            reported_fps = capture.get(cv.CAP_PROP_FPS) if hasattr(cv, "CAP_PROP_FPS") else 0
                            # Some devices silently ignore 60 FPS. Try a lower
                            # resolution before settling for a 30 FPS stream.
                            if 0 < reported_fps < 50:
                                break
                        keep = True
                        return capture, str(device), None
                except Exception:
                    pass
                finally:
                    if capture is not None and not keep:
                        capture.release()
    return None, None, (
        "Unable to read camera frames at 640x480 or higher. Close other "
        "webcam applications, try a different /dev/video device, and for "
        "Snap installations run 'sudo snap connect qrcode-gui:camera'."
    )
