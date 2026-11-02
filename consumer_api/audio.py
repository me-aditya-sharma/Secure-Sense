"""Bounded audio decoding and local-only optional transcription."""
import importlib.util
import os
from pathlib import Path
import numpy as np
import soundfile as sf

MAX_BYTES = 25 * 1024 * 1024
MAX_SECONDS = 300
EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}

def inspect_audio(path: Path) -> dict:
    try:
        with sf.SoundFile(path) as audio:
            duration = len(audio) / audio.samplerate
            if duration < 1 or duration > MAX_SECONDS:
                raise ValueError("Use a recording between 1 second and 5 minutes long.")
            if audio.channels > 2 or audio.samplerate > 96000:
                raise ValueError("Use mono or stereo audio at no more than 96 kHz.")
            peak = 0.0
            for block in audio.blocks(blocksize=65536):
                if not np.isfinite(block).all():
                    raise ValueError("The recording contains invalid sample data.")
                peak = max(peak, float(np.max(np.abs(block))))
            if peak < .001:
                raise ValueError("This recording is silent or too quiet. Add a clear recording or paste a transcript.")
            return {"duration":round(duration,2),"sample_rate":audio.samplerate,"channels":audio.channels}
    except (RuntimeError, sf.LibsndfileError):
        raise ValueError("This file could not be decoded as supported audio. Try a WAV, MP3, FLAC or OGG recording.") from None

def model_path():
    value = os.getenv("SS_WHISPER_MODEL", "")
    return Path(value).resolve() if value else None

def asr_available():
    path = model_path()
    return bool(path and (path / "model.bin").is_file() and importlib.util.find_spec("faster_whisper"))
