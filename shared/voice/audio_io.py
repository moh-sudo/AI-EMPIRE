"""Real microphone capture -- generic shared infra, not division-specific.

This is genuine, working hardware I/O (records real audio from the
default input device), deliberately kept separate from
speech_to_text.py's transcription -- recording audio and understanding
what was said are two different concerns, and only the second one
needs a model. speech_to_text.py was a stub when this file was first
written; it's run real faster-whisper transcription since 2026-08-10
(corrected here 2026-08-20).
"""

import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # standard rate for speech models (Whisper etc. expect 16kHz)
CHANNELS = 1


def record_audio(duration_seconds: float, output_path: Path | None = None) -> dict:
    """Records real audio from the default microphone for a fixed
    duration and saves it as a 16kHz mono WAV file. Never raises --
    returns {"ok": False, "reason": ...} if no microphone is available
    or recording fails, same fail-safe pattern as every other external
    call in this project."""
    if output_path is None:
        output_path = Path(__file__).resolve().parent / ".last_recording.wav"

    try:
        # Explicit device index, not PortAudio's implicit default-device
        # resolution -- on this machine the implicit path hangs
        # indefinitely opening the stream, while forcing the same
        # device by index works (confirmed 2026-08-10).
        input_device = sd.default.device[0]
        recording = sd.rec(
            int(duration_seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            device=input_device,
        )
        sd.wait()
    except Exception as e:
        return {"ok": False, "reason": f"Recording failed: {e}"}

    try:
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(recording.tobytes())
    except OSError as e:
        return {"ok": False, "reason": f"Could not save recording: {e}"}

    return {"ok": True, "path": str(output_path), "duration_seconds": duration_seconds}


def list_input_devices() -> list[dict]:
    """Lists available microphone devices -- useful for confirming a
    real mic is detected before attempting to record."""
    try:
        devices = sd.query_devices()
    except Exception as e:
        return [{"error": str(e)}]
    return [
        {"index": i, "name": d["name"], "max_input_channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]


def play_audio(audio_path: str) -> dict:
    """Plays back a WAV file through the default output device --
    real playback, used since text_to_speech.py started producing
    real audio via pyttsx3 (was a stub when this docstring was first
    written; corrected 2026-08-20)."""
    try:
        with wave.open(audio_path, "rb") as wf:
            data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="int16")
            rate = wf.getframerate()
        sd.play(data, samplerate=rate)
        sd.wait()
    except Exception as e:
        return {"ok": False, "reason": f"Playback failed: {e}"}
    return {"ok": True}
