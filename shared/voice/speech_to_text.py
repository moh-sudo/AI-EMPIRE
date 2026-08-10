"""Speech-to-text -- runs locally via faster-whisper.

Runs in-process on this machine rather than as a separate networked
service on the Mac. The Mac is reserved for Ollama specifically
because that needs its specs; transcription doesn't, and everything
else already lives here, so a network hop would add nothing. Decided
2026-08-10 -- see CONTEXT.md.

Model size is configurable via WHISPER_MODEL_SIZE (default "base", a
reasonable speed/quality balance on an 8GB machine). Loaded once and
reused across calls -- reloading the model per transcription would be
wasteful.
"""

import os
from pathlib import Path

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> dict:
    """Takes a path to a recorded WAV file (see
    shared/voice/audio_io.py's record_audio()) and returns the
    transcribed text. Never raises -- same fail-closed principle as
    every other external call in this project."""
    if not Path(audio_path).exists():
        return {"ok": False, "reason": f"Audio file not found: {audio_path}"}

    try:
        model = _get_model()
        segments, info = model.transcribe(audio_path)
        text = " ".join(segment.text.strip() for segment in segments)
    except Exception as e:
        return {"ok": False, "reason": f"Transcription failed: {e}"}

    return {"ok": True, "text": text, "language": info.language}
