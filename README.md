# QR Code Studio

A private, offline **QR generator and webcam/image scanner** for Ubuntu/Linux.
Built with Python, Tkinter, OpenCV and ZXing-C++. No login or network service
is needed to generate or scan codes.

- Generate and save QR codes as full-quality PNG images.
- Scan images or webcam frames without uploading anything.
- Use automatic high-FPS capture (minimum 640×480), or select a manual quality.
  Changing camera or capture quality applies immediately while the camera runs.
- Continue scanning until you stop the camera; display the last result and a
  timestamp with seconds.
- Automatically fit large QR codes into the preview without clipping.
- Suggest filenames like `qrcode-2026-12-24--18-00.png` and open the save dialog
  in your XDG Pictures folder (or home directory when there is no Pictures folder).

The application icon (`snap/gui/qrcode-gui.png`) is a QR code containing
`qrcode-gui`.

## Install on Ubuntu without Snap — one paste

**Copy/paste the entire block** into a terminal on an Ubuntu desktop:

```bash
sudo apt-get update && sudo apt-get install -y curl && \
curl -fsSL https://raw.githubusercontent.com/ballerburg9005/qrcode-gui/main/install.sh -o /tmp/install-qrcode-gui.sh && \
bash /tmp/install-qrcode-gui.sh
```

The [installer](install.sh) installs Git and Python/Tk prerequisites through
`apt`, clones the repository into `~/qrcode-gui` (or updates an existing
checkout), creates a Python **virtual environment**, installs the application,
and adds `~/.local/share/applications/qrcode-gui.desktop` to the application
menu with the bundled QR icon.

**After installation:** open Ubuntu's app launcher and search for
**QR Code Studio**. There is no need to activate the venv or write a launcher
yourself. If you prefer a terminal, run:

```bash
~/qrcode-gui/.venv/bin/qrcode-gui
```

To update an existing source installation later:

```bash
bash ~/qrcode-gui/install.sh
```

You can inspect the installer before running it. The installed desktop launcher
is created from [desktop/qrcode-gui.desktop.in](desktop/qrcode-gui.desktop.in).
Running the installer requires an internet connection and `sudo` for the apt
prerequisites; the application itself works offline. Ubuntu may need a logout
and login for a newly installed menu icon to appear.

## Build a Snap on Ubuntu 24.04

**Snapcraft is installed with `snap`, not `apt`.** Install Snapcraft and LXD,
which provides an isolated environment for building packages:

```bash
sudo snap install snapcraft --classic
sudo snap install lxd
sudo usermod -aG lxd "$USER"
```

**Log out of Ubuntu and log back in** so that the `lxd` group takes effect.
Then run these commands:

```bash
sudo lxd init --auto
cd ~/qrcode-gui
git pull --ff-only
snapcraft
```

The first build downloads a core24 build environment and dependencies, so it
can take several minutes. When it finishes, the Snap is created in the current
directory, for example `qrcode-gui_0.2.0_amd64.snap`. Inspect it:

```bash
ls -lh qrcode-gui_*.snap
```

To install the **one** freshly built Snap locally, then connect webcam access:

```bash
sudo snap install --dangerous ./qrcode-gui_*.snap
sudo snap connect qrcode-gui:camera
snap run qrcode-gui
```

`--dangerous` means **locally built and not signed by the Snap Store**; it does
not disable strict confinement. The Snap should also appear in the Ubuntu
application menu with the QR icon. If multiple `.snap` files are present, pass
the one specific filename instead of a wildcard.

You can alternatively build without local Snapcraft/LXD: go to
[GitHub Actions](https://github.com/ballerburg9005/qrcode-gui/actions),
open a successful **Test and build Snap** run, download the
`qrcode-gui-snap` artifact, unzip it, and install the `.snap` as above.

**Camera note:** strict Snap confinement requires permission to access the
webcam. If the camera doesn't work, check `snap connections qrcode-gui` and run
`sudo snap connect qrcode-gui:camera`. Saving to ordinary folders under the
real home directory is permitted by the `home` interface, but hidden or
external paths may require different permissions.

## Publish your Snap to the Snap Store / Ubuntu App Center

A Snap is published through the [Snap Store](https://snapcraft.io/); this is
the store used by Ubuntu's App Center, **not an apt/PPA upload**.

1. Create an [Ubuntu One / Snapcraft account](https://snapcraft.io/account).
   Choose a unique Snap name. The manifest currently uses
   `name: qrcode-gui`; it must match the name you register. If that name is
   unavailable, change `name:` in `snap/snapcraft.yaml` and build again.
2. Sign in and register the name:

   ```bash
   snapcraft login
   snapcraft register qrcode-gui
   ```

3. **Test the Snap on a real Ubuntu desktop with a camera**, including
   generating a PNG, saving it in Pictures, and scanning with the connected
   `camera` interface. The manifest is set to `grade: stable`, which is needed
   for the stable release channel.
4. From the directory containing the built Snap, upload and release it:

   ```bash
   snapcraft upload --release=stable qrcode-gui_0.2.0_amd64.snap
   ```

   Replace the filename (and snap name) with your actual built file.
   Uploads undergo automated store checks and may need fixes or further
   review before publication.
5. Visit the [Snapcraft publisher dashboard](https://dashboard.snapcraft.io/)
   to complete the store listing (description, screenshots, contact information,
   categories and other requested details). Once published, other users can
   install it with `sudo snap install qrcode-gui`.

Official references:
[Install Snapcraft](https://snapcraft.io/install/snapcraft/ubuntu) ·
[Build setup](https://snapcraft.io/docs/snapcraft-setup/) ·
[Register a name](https://snapcraft.io/docs/registering-your-app-name/) ·
[Publish a snap](https://snapcraft.io/docs/releasing-your-app/).

## Developer notes

```bash
cd ~/qrcode-gui
.venv/bin/python -m unittest discover -s tests -v
```

- `src/qrcode_gui/app.py` — responsive UI, camera streaming and decoding
- `src/qrcode_gui/paths.py` — sensible save location (XDG user directories)
- `src/qrcode_gui/decoder.py` — ZXing with OpenCV fallback
- `src/qrcode_gui/camera.py` — camera selection and FPS/resolution negotiation
- `src/qrcode_gui/qr.py` — generate QR images
- `install.sh` and `desktop/` — one-command source installation and menu icon
- `snap/` — core24 Snapcraft manifest, icon and Snap menu integration
- `.github/workflows/build.yml` — Python tests and build artifacts

Snap publishing requires the developer's own credentials; this repository does
not contain credentials or automatically publish store releases.
