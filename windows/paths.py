"""Shared paths and localhost ports for the Windows runtime."""
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
STATIC_DIR = PACKAGE_ROOT / "static"
SETTINGS_PATH = PACKAGE_ROOT / "galaxytrackpad_settings.json"
ADB = REPO_ROOT / "platform-tools" / "adb.exe"

HTTP_PORT = 8765
WS_PORT = 8766
CONTROL_PORT = 8767

PAD_W, PAD_H = 10000, 6000
