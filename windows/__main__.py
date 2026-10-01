"""Entry point: python -m windows [--engine] [--tray]"""
from __future__ import annotations

import sys


def main() -> None:
    # Before monitors / Qt / pen injection — see windows.dpi.
    from windows.dpi import enable_dpi_awareness

    enable_dpi_awareness()

    if "--engine" in sys.argv:
        from windows.engine import engine_main
        engine_main()
        return
    from windows.ui.main_window import run_gui
    raise SystemExit(run_gui(start_hidden="--tray" in sys.argv))


if __name__ == "__main__":
    main()
