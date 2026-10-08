# QR Code GUI

A desktop QR-code generator and webcam/image scanner for Ubuntu 24.04 and other Linux desktops.

- Generate a QR code from any text or URL, preview it, and save it as PNG.
- Decode QR codes from a webcam or image file, copy results, or use them as input.
- Choose a video device, try Linux V4L2 first, and recover from lost webcam frames.
- All scanning and generation happens locally. The camera is only opened when you press **Start Camera**.

## Install and run on Ubuntu 24.04

This is currently **source code and an untested Snap package recipe**, not a released Store app.

```bash
sudo apt update
sudo apt install -y git python3-tk python3-venv
git clone https://github.com/ballerburg9005/qrcode-gui.git
cd qrcode-gui
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
.venv/bin/qrcode-gui
```

You do not need the external `qrcode` command or the EOG image viewer. Dependencies (Pillow, qrcode, OpenCV and its Python dependencies) are installed by pip in the isolated virtual environment.

Run tests with `.venv/bin/python -m unittest discover -s tests -v`.

## Build and install the Snap

The package targets `core24`, bundles the Python libraries and Tk runtime, and uses strict confinement. Install/configure **Snapcraft and LXD** first.

```bash
snapcraft
sudo snap install --dangerous ./qrcode-gui_*.snap
sudo snap connect qrcode-gui:camera
snap run qrcode-gui
```

Camera permission is not automatically connected. **Every user must connect it manually unless the Snap Store grants an auto-connection request:**

```bash
snap connections qrcode-gui
sudo snap connect qrcode-gui:camera
```

GitHub Actions attempts to build the Snap on every push to `main`, as well as manually. After a successful run, download the `qrcode-gui-snap` workflow artifact, extract its .snap file, and test it before distributing it.

## Troubleshooting: Unable to read webcam frame

The original script requested 1280x720 and a one-frame capture buffer after opening the webcam. Some V4L2 drivers stop providing frames after such a mode change. This version **does not change the camera mode**, probes actual frames, tries both V4L2 and the default OpenCV backend, and attempts limited reconnection if frames stop arriving.

If no camera works:

1. Close Zoom, Cheese, browsers, and other applications that may own the webcam.
2. Run `ls -l /dev/video*`. In the app select an explicit device such as `/dev/video0` or `Camera 0`. Some /dev/videoN entries are metadata-only nodes.
3. Verify that the camera works in another application such as Cheese.
4. For a Snap install, run `sudo snap connect qrcode-gui:camera`.
5. Diagnose competing processes with `sudo fuser -v /dev/video0` (adjust the device).
6. Launch from the terminal to view OpenCV warnings: `snap run qrcode-gui` or `.venv/bin/qrcode-gui`.

Use **Scan Image** to decode QR codes from a picture even when the webcam is unavailable.

## Snap Store release checklist (not published yet)

- Register `qrcode-gui` (if available) at https://snapcraft.io/register.
- Verify that the Snap actually builds and launches on Ubuntu 24.04 and test real cameras.
- Create an appropriate icon, screenshots, and listing/support information.
- After testing, change `grade: devel` to `grade: stable` in `snap/snapcraft.yaml`.
- Log in with `snapcraft login`, upload with `snapcraft upload <your.snap>`, and release to a suitable channel.

Store names are globally unique; if `qrcode-gui` is already registered, choose another name in the Snap config. Releases should not be automated before the Snap is tested and registered.

## Structure

- `src/qrcode_gui/app.py`: Tkinter interface and QR scanning loop
- `src/qrcode_gui/camera.py`: webcam discovery and backend fallbacks
- `src/qrcode_gui/qr.py`: QR generation without external commands
- `snap/snapcraft.yaml`: Snapcraft package
- `.github/workflows/build.yml`: Python tests and Snap build
- `tests/`: basic offline unit tests
