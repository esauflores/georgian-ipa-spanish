"""Read and write dictionary entries in UTF-8 JSON."""

import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from .dictionary import Entry


class JsonStore:
    """Load entries and replace the saved file after a complete write."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[Entry]:
        """Read and validate entries."""
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise TypeError("Se esperaba una lista de entradas.")
        return [Entry(**item) for item in data]

    def save(self, entries: Iterable[Entry]) -> None:
        """Save entries without overwriting the previous file on write failure."""
        data = json.dumps([asdict(entry) for entry in entries], ensure_ascii=False, indent=2)
        temporary_path = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(data + "\n")
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
