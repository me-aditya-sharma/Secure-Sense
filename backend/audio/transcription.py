# backend/audio/transcription.py
"""
Real speech-to-text for SecureSense.

Uses faster-whisper (CPU, "tiny" model - fastest + smallest download, good
enough for a live demo) to transcribe the call audio directly, so the system
no longer depends on someone manually typing out what was said.

Falls back to a random test transcript if transcription fails for any reason
(model not downloaded yet, bad/corrupt audio, etc.) so a live demo can never
hard-crash on this step - matches the workflow doc's own rule: "Use prepared
fixtures if live microphone/model behaviour is unreliable."
"""

import logging
import random

from backend.NLP.fixtures import TEST_TRANSCRIPTS

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio_path: str) -> str:
    """Transcribes the given audio file to text using Whisper.
    Never raises - falls back to a random test transcript on any failure,
    so callers can treat this as always returning a usable string."""
    try:
        model = _get_model()
        segments, _info = model.transcribe(audio_path, beam_size=1)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise ValueError("empty transcription result")
        return text
    except Exception as exc:
        logger.warning("Live transcription failed (%s) - falling back to test transcript.", exc)
        return random.choice(TEST_TRANSCRIPTS)
