"""Locate generated pronunciation clips."""

from hashlib import sha256
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parents[1] / "static" / "audio"


def clip_name(text: str) -> str:
    """Return a filesystem-safe, stable filename for a Georgian phrase."""
    digest = sha256(text.encode("utf-8")).hexdigest()
    return f"{digest}.wav"
