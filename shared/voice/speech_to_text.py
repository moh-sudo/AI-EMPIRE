"""Speech-to-text -- THE stub in the local voice pipeline.

Architecture-only per Mohamed's 2026-07-31/08-01 instruction: the real
transcription model is deliberately not connected yet. Realistic
candidates once he's ready: a local Whisper model (small/base sizes
are actually plausible even on the current 8GB M1, unlike the
vision/GPT-4-class text cases already discussed -- speech recognition
models are much smaller) or a cloud STT API. That decision is his to
make; this function is the single, clearly-marked place to wire it in.
"""

from pathlib import Path


def transcribe(audio_path: str) -> dict:
    """THE stub. Takes a path to a recorded WAV file (see
    shared/voice/audio_io.py's record_audio()) and would return the
    transcribed text. Returns an honest "not connected yet" result
    today instead of silently returning empty/fake text -- same
    fail-closed principle as every other stub in this project
    (marketing_content.py's _call_content_model, etc.)."""
    if not Path(audio_path).exists():
        return {"ok": False, "reason": f"Audio file not found: {audio_path}"}

    return {
        "ok": False,
        "reason": "Speech-to-text model not connected yet -- architecture-only per Mohamed's instruction.",
    }
