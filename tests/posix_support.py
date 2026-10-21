"""Capability helpers for tests that need POSIX-only features.

``os.mkfifo`` does not exist on Windows. Pyright narrows ``sys.platform`` comparisons, so
the call sits behind such a check: the type checker then accepts the code on every
platform, and the tests that need a FIFO are skipped where the capability is missing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HAS_MKFIFO = sys.platform != "win32" and hasattr(os, "mkfifo")
FIFO_SKIP_REASON = "FIFOs need a POSIX platform"


def make_fifo(path: Path) -> None:
    """Create a named pipe at ``path``; raise ``NotImplementedError`` if unsupported."""
    if sys.platform == "win32":
        raise NotImplementedError(FIFO_SKIP_REASON)
    os.mkfifo(path)
