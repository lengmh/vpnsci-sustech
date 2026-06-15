from __future__ import annotations

import os
from pathlib import Path
import uuid


def usable_temp_parent(path: Path) -> Path | None:
    if not path.is_dir():
        return None
    probe = path / f".vpnsci-test-probe-{os.getpid()}-{uuid.uuid4().hex}"
    try:
        probe.mkdir()
        probe.rmdir()
    except OSError:
        return None
    return path


def select_temp_parent(primary: Path, *fallbacks: Path) -> Path:
    for candidate in (primary, *fallbacks):
        usable = usable_temp_parent(candidate)
        if usable is not None:
            return usable
    raise RuntimeError("No writable temporary parent is available for tests")
