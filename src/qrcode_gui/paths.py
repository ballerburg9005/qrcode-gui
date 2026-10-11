"""Choose a sensible default directory for saved QR PNGs."""
import os
import re
from pathlib import Path


def default_save_directory():
    """Prefer the desktop's Pictures folder, then ~/Pictures, then home.

    A confined Snap may use a private HOME; SNAP_REAL_HOME points to the
    user's actual home directory when provided by snapd.
    """
    home = Path(os.environ.get("SNAP_REAL_HOME") or Path.home()).expanduser()
    config = home / ".config" / "user-dirs.dirs"
    try:
        for line in config.read_text(encoding="utf-8").splitlines():
            match = re.match(r'^\s*XDG_PICTURES_DIR\s*=\s*"([^"]+)"\s*$', line)
            if match:
                value = match.group(1)
                folder = Path(
                    value.replace("${HOME}", str(home)).replace("$HOME", str(home))
                ).expanduser()
                if folder.is_dir():
                    return str(folder)
    except (OSError, UnicodeError):
        pass
    pictures = home / "Pictures"
    return str(pictures if pictures.is_dir() else home)
