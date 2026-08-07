"""Text-to-speech -- THE other stub in the local voice pipeline.

Same deliberate-stub status as speech_to_text.py, independent decision
-- Mohamed may want spoken replies, or may prefer reading text replies
even once speech input works, so this is left as its own separate
connection point rather than assumed to come bundled with STT.
"""


def synthesize(text: str) -> dict:
    """THE stub. Would return a path to a generated WAV file (playable
    via shared/voice/audio_io.py's play_audio()). Returns an honest
    "not connected yet" result today."""
    return {
        "ok": False,
        "reason": "Text-to-speech model not connected yet -- architecture-only per Mohamed's instruction.",
    }
