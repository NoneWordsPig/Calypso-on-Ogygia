"""Calypso's Ogygia desktop pet — entry point.

Usage:
    python -m app                    # run the desktop pet
    python -m app --smoke 300        # headless-ish smoke run (300 frames) then exit
    python -m app --config data/config.json
    python -m app --provider http    # poll a real hermes-pet loopback endpoint
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
    args = parser.parse_args(argv)

    from PyQt6.QtWidgets import QApplication

    from app.config import Config
    from app.pet_window import PetWindow

    config = Config.load(args.config)
    if args.provider:
        config.data.setdefault("hermes", {})["provider"] = args.provider

    app = QApplication(sys.argv[:1])
    window = PetWindow(config, smoke_frames=args.smoke)
    window.show()
    exit_code = app.exec()
    print(f"[app] exited with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
