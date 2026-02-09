from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class FileLike:
    path: str
    content: str


class Workspace:
    """
    Creates a temp directory workspace and lets you write project files into it.
    Designed for:
      - materializing a Spring Initializr Maven project sent from VS Code (path+content)
      - applying student edits (override)
      - injecting generated tests
    """

    def __init__(self, prefix: str = "codellamas_"):
        self.root = tempfile.mkdtemp(prefix=prefix)

    def write_files(self, files: Iterable[FileLike]) -> None:
        for f in files:
            self._write_one(f.path, f.content)

    def write_file_map(self, file_map: Dict[str, str]) -> None:
        for path, content in file_map.items():
            self._write_one(path, content)

    def _write_one(self, rel_path: str, content: str) -> None:
        rel_path = rel_path.lstrip("/").replace("\\", "/")
        abs_path = os.path.join(self.root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as out:
            out.write(content)

    def read(self, rel_path: str) -> Optional[str]:
        rel_path = rel_path.lstrip("/").replace("\\", "/")
        abs_path = os.path.join(self.root, rel_path)
        if not os.path.exists(abs_path):
            return None
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()
