"""Text-to-speech -- runs locally via pyttsx3 (Windows SAPI5).

Independent decision from speech_to_text.py -- Mohamed may want spoken
replies, or may prefer reading text replies even with speech input
working, so this stays its own separate connection point rather than
assumed to come bundled with STT.

Unlike faster-whisper, this wraps Windows' built-in SAPI5 voices --
no model download, no heavy native dependency chain, offline by
construction. The engine is loaded once and reused across calls.
"""

from pathlib import Path

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        import pyttsx3

        _engine = pyttsx3.init()
    return _engine


def synthesize(text: str, output_path: str | None = None) -> dict:
    """Renders text to a WAV file (playable via
    shared/voice/audio_io.py's play_audio()). Never raises -- same
    fail-closed principle as every other external call in this
    project."""
    if not text.strip():
        return {"ok": False, "reason": "No text to synthesize."}

    if output_path is None:
        output_path = str(Path(__file__).resolve().parent / ".last_tts_output.wav")

    try:
        engine = _get_engine()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
    except Exception as e:
        return {"ok": False, "reason": f"Synthesis failed: {e}"}

    return {"ok": True, "path": output_path}
