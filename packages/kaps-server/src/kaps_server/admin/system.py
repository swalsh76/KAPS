"""The machine as the checks see it, behind one small interface so every check can be tested.

``LocalSystem`` is the real machine. Every command it runs has a fixed argument list (never a
shell) and a timeout, so a check cannot hang an unattended run.
"""

import platform
import shutil
import subprocess  # noqa: S404 (fixed argument lists only, never a shell)
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class System(Protocol):
    def read_text(self, path: str) -> str | None:
        """The file's text, or None when it is missing or unreadable."""
        ...

    def exists(self, path: str) -> bool: ...

    def run(self, argv: Sequence[str], timeout: float = 10.0) -> tuple[int, str]:
        """(exit code, standard output); (-1, "") when it cannot run or times out."""
        ...

    def free_bytes(self, path: str) -> int | None: ...

    def machine(self) -> str: ...


class LocalSystem:
    def read_text(self, path: str) -> str | None:
        try:
            return Path(path).read_text(encoding="utf-8")
        except OSError:
            return None

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def run(self, argv: Sequence[str], timeout: float = 10.0) -> tuple[int, str]:
        try:
            done = subprocess.run(  # noqa: S603 (fixed argument list, no shell)
                list(argv), capture_output=True, text=True, timeout=timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            return -1, ""
        return done.returncode, done.stdout

    def free_bytes(self, path: str) -> int | None:
        try:
            return shutil.disk_usage(path).free
        except OSError:
            return None

    def machine(self) -> str:
        return platform.machine()
