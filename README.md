# QR Code Studio

Local QR generator and webcam/image scanner for Ubuntu 24.04, built with Tkinter.
Everything stays on your computer: no cloud scanning, tracking, or login.

## Improvements in v0.2.0

- **Dense QR codes:** ZXing-C++ decoder, with OpenCV fallback and contrast enhancement.
- **Higher resolution:** selectable driver default, HD 1280×720 or Full HD 1920×1080.
  The scanner decodes the **original full-resolution frames**, not the smaller on-screen preview.
- **Responsive scanning:** decode work runs in a single background worker; the window doesn't
  hang during complex QR decoding.
- **Cleaner interface:** two panels, better styling, input **and** output vertical scrollbars,
  image scanning, copy / paste-into-generator, and PNG export.
- **Snap packaging:** an application icon, a correctly located desktop launcher,
  the Python/Tk/OpenCV/ZXing dependencies, and strict confinement.

Dense codes still depend on the camera's physical resolution, focus, exposure and contrast.
For complex symbols use **Full HD**, bring the QR into a large portion of the frame without
cutting off the border, hold the camera steady, and avoid glare/reflections.

## Install from source: Ubuntu 24.04

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

This installs Python dependencies (Pillow, qrcode, OpenCV, ZXing-C++) into a local virtual
environment. No external `qrcode` executable or EOG is required.

Run tests with `.venv/bin/python -m unittest discover -s tests -v`.

## Build/test the Ubuntu Snap

`snap/snapcraft.yaml` uses `core24`, strict confinement, a desktop launcher and an
app icon. It **has not yet been published to the Snap Store**.

On a host with Snapcraft + LXD configured:

```bash
snapcraft
sudo snap install --dangerous ./qrcode-gui_*.snap
sudo snap connect qrcode-gui:camera
snap run qrcode-gui
```

Or open [GitHub Actions](https://github.com/ballerburg9005/qrcode-gui/actions),
select a successful **Test and build Snap** run, download `qrcode-gui-snap`, unzip,
then install the `.snap` with `sudo snap install --dangerous <file.snap>`.

**Camera access is not auto-connected by default:** if the preview doesn't open, run
`snap connections qrcode-gui` and `sudo snap connect qrcode-gui:camera`.
The home plug permits ordinary files in your home directory, but strict Snap confinement
can prevent reading arbitrary system paths.

For some USB webcams `/dev/video0` is not the imaging node (a second node might carry
metadata). Refresh the camera list and try another device. If frames drop after
requesting Full HD, select **Default** or **HD** and restart the camera.

If all camera modes fail:

```bash
ls -l /dev/video*
sudo fuser -v /dev/video0
snap connections qrcode-gui
```

Also try the **Scan Image** button for a QR saved as PNG/JPG.

## Release checklist (not yet published)

1. Confirm the Snap build workflow succeeds on Ubuntu 24.04.
2. Install and test it on a physical webcam, including dense QR symbols.
3. Register an available Snap name at https://snapcraft.io/register.
4. Add screenshots and publisher/contact details to the Snap Store listing.
5. Once validated, set `grade: stable`; upload and release using Snapcraft
   credentials on the publisher's machine or configured store-publishing workflow.

This repository does **not** contain publisher credentials or publish automatically.
For strict-confinement camera access users must connect the `camera` plug unless
automatic connection is approved.

## Layout

- `src/qrcode_gui/app.py`: UI, preview and background scanning
- `src/qrcode_gui/decoder.py`: ZXing and OpenCV decoders
- `src/qrcode_gui/camera.py`: V4L2 device selection / resolution fallback
- `src/qrcode_gui/qr.py`: local QR generation
- `snap/`: core24 Snap and desktop metadata
- `.github/workflows/build.yml`: automated tests and Snap build
