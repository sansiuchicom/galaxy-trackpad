"""Entry point: python -m windows [--engine]"""
from __future__ import annotations

import sys


def main() -> None:
    if "--engine" in sys.argv:
        from windows.engine import engine_main
        engine_main()
    else:
        from windows.ui.main_window import run_gui
        raise SystemExit(run_gui())


if __name__ == "__main__":
    main()
