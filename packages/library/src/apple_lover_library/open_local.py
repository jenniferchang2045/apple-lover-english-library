from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from apple_lover_library.errors import NotFoundError


def open_path(path: str | Path) -> None:
    target = Path(path)
    if not target.exists():
        raise NotFoundError(f"file missing: {target}")
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(target)], check=False)
        return
    subprocess.run(["xdg-open", str(target)], check=False)
