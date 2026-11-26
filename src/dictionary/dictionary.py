"""Dictionary entries and search."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from unicodedata import normalize


@dataclass(frozen=True)
class Entry:
    """One word and its meaning and pronunciation."""

    georgian: str
    spanish: str
    ipa: str
    pronunciation: str
    tags: tuple[str, ...] = ()

    def __post_init__(self):
        """Reject missing or blank fields."""
        for field in (self.georgian, self.spanish, self.ipa, self.pronunciation):
            if not isinstance(field, str) or not field.strip():
                raise ValueError("Completa los cuatro campos.")

        if not isinstance(self.tags, (tuple, list)) or any(
            not isinstance(tag, str) or not tag.strip() for tag in self.tags
        ):
            raise ValueError("Las etiquetas deben ser textos no vacíos.")

        tags = tuple(dict.fromkeys(tag.strip().lower() for tag in self.tags))
        object.__setattr__(self, "tags", tags)

    def __str__(self) -> str:
        """Format the entry for the command line."""
        return f"{self.georgian} — {self.spanish} — /{self.ipa}/ — {self.pronunciation}"


def search_key(value: str) -> str:
    """Ignore case and Spanish vowel accents while preserving ñ."""
    return normalize("NFC", value.strip().casefold()).translate(str.maketrans("áéíóúü", "aeiouu"))


class Dictionary:
    """Keep entries and match Georgian words or Spanish meanings."""

    def __init__(self, entries: Iterable[Entry] = ()):
        self.entries = list(entries)

    def search(self, query: str | None = None, tag: str | None = None) -> Iterator[Entry]:
        """Yield entries matching the given text and tag."""
        key = search_key(query) if query is not None else None
        if key == "":
            return

        tag = tag.strip().lower() if tag is not None else None

        for entry in self.entries:
            if tag is not None and tag not in entry.tags:
                continue
            if key is None or any(key in search_key(value) for value in (entry.georgian, entry.spanish)):
                yield entry

    def tags(self) -> list[str]:
        """List the distinct tags present in the dictionary."""
        return sorted({tag for entry in self.entries for tag in entry.tags})
