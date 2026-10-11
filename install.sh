#!/usr/bin/env bash
# Ubuntu desktop installer. Can be downloaded and run, or run from a clone.
set -euo pipefail

REPO_URL="https://github.com/ballerburg9005/qrcode-gui.git"
APP_DIR="${QRCODE_GUI_DIR:-$HOME/qrcode-gui}"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer is for Ubuntu and other apt-based desktops." >&2
  exit 1
fi

echo "Installing QR Code Studio system prerequisites (sudo may ask for your password)..."
sudo apt-get update
sudo apt-get install -y git python3-venv python3-tk

if [ -d "$APP_DIR/.git" ]; then
  echo "Updating existing checkout in $APP_DIR..."
  git -C "$APP_DIR" pull --ff-only
elif [ -e "$APP_DIR" ]; then
  echo "Cannot install: $APP_DIR exists but is not a Git checkout." >&2
  echo "Choose another location with: QRCODE_GUI_DIR=~/my-qrcode-gui bash install.sh" >&2
  exit 1
else
  echo "Cloning into $APP_DIR..."
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "Creating a Python virtual environment and installing the application..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install --upgrade "$APP_DIR"

echo "Adding the application menu entry..."
mkdir -p "$HOME/.local/share/applications"
python3 - "$APP_DIR" "$HOME/.local/share/applications/qrcode-gui.desktop" <<'PY'
from pathlib import Path
import sys

app_dir = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2])
template = (app_dir / "desktop" / "qrcode-gui.desktop.in").read_text(encoding="utf-8")
executable = str(app_dir / ".venv" / "bin" / "qrcode-gui")

# Exec requires quotes if the installation path contains whitespace.
quoted_exec = '"' + executable.replace("\\", "\\\\").replace('"', '\\"') + '"'
entry = (template.replace("@EXEC@", quoted_exec)
                 .replace("@TRYEXEC@", executable)
                 .replace("@APP_DIR@", str(app_dir))
                 .replace("@ICON@", str(app_dir / "snap" / "gui" / "qrcode-gui.png")))
destination.write_text(entry, encoding="utf-8")
PY

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" || true
fi

echo
echo "Installed! Open your application launcher and search for 'QR Code Studio'."
echo "You can also run: $APP_DIR/.venv/bin/qrcode-gui"
