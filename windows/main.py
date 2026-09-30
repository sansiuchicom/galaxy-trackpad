"""Convenience entry: python windows/main.py [--engine]

Prefer from repo root:
  python -m windows
  python -m windows --engine
"""
from pathlib import Path
import sys

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

import galaxytrackpad_v08 as app


def main() -> None:
    if "--engine" in sys.argv:
        app.engine_main()
    else:
        app.gui_main()


if __name__ == "__main__":
    main()
