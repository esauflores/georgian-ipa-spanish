"""Generate local Georgian WAV clips for the starter dictionary with Piper."""

import json
import subprocess
import sys
import wave
from pathlib import Path
from tempfile import NamedTemporaryFile

from piper import PiperVoice

from src.dictionary.audio import AUDIO_DIR, clip_name

ROOT = Path(__file__).resolve().parents[1]
VOICE = "ka_GE-natia-medium"
MODEL_DIR = ROOT / ".piper"


def generate_audio() -> None:
    """Download the voice if needed and synthesize missing clips."""
    entries = json.loads((ROOT / "data" / "starter.json").read_text(encoding="utf-8"))
    texts = dict.fromkeys(entry["georgian"] for entry in entries)
    pending = {}

    for text in texts:
        destination = AUDIO_DIR / clip_name(text)
        if not destination.is_file():
            pending[text] = destination

    if not pending:
        print(f"All {len(texts)} clips already exist.")
        return

    model = MODEL_DIR / f"{VOICE}.onnx"
    if not model.is_file() or not model.with_suffix(".onnx.json").is_file():
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "piper.download_voices", VOICE, "--download-dir", str(MODEL_DIR)],
            check=True,
        )

    voice = PiperVoice.load(model)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for text, destination in pending.items():
        with NamedTemporaryFile(dir=AUDIO_DIR, delete=False) as temporary:
            temporary_path = Path(temporary.name)

        try:
            with wave.open(str(temporary_path), "wb") as audio:
                voice.synthesize_wav(text, audio)
            temporary_path.replace(destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    print(f"Generated {len(pending)} WAV files in {AUDIO_DIR.relative_to(ROOT)}.")


if __name__ == "__main__":
    generate_audio()
