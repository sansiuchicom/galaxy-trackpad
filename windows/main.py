"""Convenience entry: python windows/main.py [--engine]

Prefer from repo root:
  python -m windows
  python -m windows --engine
"""
from pathlib import Path
import sys

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from windows.__main__ import main

if __name__ == "__main__":
    main()
