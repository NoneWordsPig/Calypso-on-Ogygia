"""Calypso's Ogygia desktop pet — entry point.

The map is the desktop wallpaper; the pet runs in a transparent click-through
overlay with a small control panel.

Usage:
    python -m app                        # run on the desktop
    python -m app --smoke 300            # run 300 frames then exit (validation)
    python -m app --preview              # also draw the map (debug/screenshots)
    python -m app --provider http        # poll a real hermes-pet loopback endpoint
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="calypso-ogygia", description="Calypso's Ogygia desktop pet")
    parser.add_argument("--config", default=None, help="path to config.json (default data/config.json)")
    parser.add_argument("--provider", choices=["mock", "http"], default=None,
                        help="hermes status provider override")
    parser.add_argument("--smoke", type=int, default=0, metavar="FRAMES",
                        help="run N frames then quit (for validation)")
    parser.add_argument("--preview", action="store_true",
                        help="draw the map too (debug/screenshot mode)")
    args = parser.parse_args(argv)

    from PyQt6.QtWidgets import QApplication

    from app.config import Config
    from app.pet_window import ControlPanel, DesktopOverlay, PetCore

    config = Config.load(args.config)
    if args.provider:
        config.data.setdefault("hermes", {})["provider"] = args.provider
    if args.preview:
        config.data.setdefault("display", {})["draw_debug_map"] = True

    app = QApplication(sys.argv[:1])
    core = PetCore(config)
    overlay = DesktopOverlay(config, core)
    overlay.smoke_frames = args.smoke
    overlay.show()

    panel = None
    if config.get("display", "control_panel", {}).get("enabled", True):
        panel = ControlPanel(config, core)
        panel.show()

    if args.smoke == 0:
        print(overlay.placement.describe())

    exit_code = app.exec()
    print(f"[app] exited with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
