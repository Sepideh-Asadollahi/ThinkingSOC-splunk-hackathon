"""Logging configuration for setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("setup")


def configure_logging(log_file: Optional[Path], verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
        LOG.info("Logging to file: %s", log_file)
