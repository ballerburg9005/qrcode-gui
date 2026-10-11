"""Saved-PNG location should follow the desktop's XDG user dirs."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qrcode_gui.paths import default_save_directory


class SavePathTests(unittest.TestCase):
    def test_uses_localized_xdg_pictures_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".config").mkdir()
            (home / "Bilder").mkdir()
            (home / ".config" / "user-dirs.dirs").write_text(
                'XDG_PICTURES_DIR="$HOME/Bilder"\n', encoding="utf-8",
            )
            with patch.dict(os.environ, {"SNAP_REAL_HOME": str(home)}):
                self.assertEqual(default_save_directory(), str(home / "Bilder"))

    def test_falls_back_to_existing_pictures_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "Pictures").mkdir()
            with patch.dict(os.environ, {"SNAP_REAL_HOME": str(home)}):
                self.assertEqual(default_save_directory(), str(home / "Pictures"))

    def test_falls_back_to_home_when_no_pictures_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"SNAP_REAL_HOME": tmp}):
                self.assertEqual(default_save_directory(), tmp)


if __name__ == "__main__":
    unittest.main()
