"""Hands-free wake trigger -- clap arms a short listening window, then
saying "wake up" fires a real voice capture (interfaces.voice_capture).

Runs as a long-lived background loop, not a one-shot script like
voice_session.py/voice_capture.py -- Mohamed's explicit choice
(2026-08-10) over a manually-started listener, so he can just clap and
talk without running anything first. Making this survive a machine
restart (e.g. Task Scheduler) is a separate, later step -- matches how
n8n and the division servers already need manual restart each session
(see ARCHITECTURE.md's "Nothing persists across a machine restart").

Two-stage trigger, not clap-alone or phrase-alone:
- Clap-alone is prone to false positives (any sudden loud noise).
- Phrase-alone would mean running real speech transcription
  continuously, expensive compared to a lightweight amplitude check.
A clap is a cheap, continuous peak-amplitude check running on every
audio chunk; the (comparatively expensive) transcription step only
runs for a few seconds after a clap fires, not continuously --
consistent with this project's own Energy-Aware Computing standard
(CONTEXT.md's Operational Efficiency Standard).

CLAP_THRESHOLD was set from a real calibration recording on this
machine (2026-08-10), not guessed: a genuine clap peaked at 2359
(int16 scale), quiet ambient periods stayed under ~200, and separately
measured loud/close speech topped out around 1600-1700. 1800 sits
between the two. A false clap-arm (dropped object, door closing, loud
speech) is harmless -- it just transcribes a few seconds that don't
contain "wake up" and goes back to listening. Nothing is triggered
without the phrase actually being said.

Usage: python -m interfaces.wake_listener
"""

import queue
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from shared.agent_identities import SUPREME_BOSS, SUPREME_BOSS_NICKNAME
from shared.voice.audio_io import SAMPLE_RATE

VOICE = f"{SUPREME_BOSS} ({SUPREME_BOSS_NICKNAME})"

CLAP_THRESHOLD = 1800
CHUNK_SECONDS = 0.1
LISTEN_AFTER_CLAP_SECONDS = 3.0
WAKE_PHRASE = "wake up"
CAPTURE_SECONDS = 8.0
COOLDOWN_SECONDS = 2.0  # ignore further claps right after a trigger, avoid double-fires


def is_clap(chunk: np.ndarray, threshold: int = CLAP_THRESHOLD) -> bool:
    """Pure, testable: a chunk counts as a clap if its peak amplitude
    crosses the threshold. Deliberately simple (no ML) -- the
    downstream "wake up" phrase check is what actually gates any real
    action, so this only needs to be cheap, not precise."""
    return int(np.abs(chunk).max()) >= threshold


def _save_wav(samples: np.ndarray, path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples.tobytes())


def _collect_seconds(audio_q: "queue.Queue[np.ndarray]", seconds: float, seed: list | None = None) -> np.ndarray:
    """Drains the shared audio queue for the given duration, optionally
    starting from already-collected chunks (seed) so no audio between
    the clap and the follow-up check is lost."""
    chunks = list(seed) if seed else []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            chunks.append(audio_q.get(timeout=max(0.0, deadline - time.time())))
        except queue.Empty:
            break
    return np.concatenate(chunks) if chunks else np.array([], dtype="int16")


def listen_forever() -> None:
    """Blocks forever, listening for the clap + "wake up" trigger.
    Ctrl+C to stop."""
    from interfaces.voice_capture import route_capture
    from shared.voice.speech_to_text import transcribe

    audio_q: queue.Queue[np.ndarray] = queue.Queue()

    def _callback(indata, frames, time_info, status):
        audio_q.put(indata[:, 0].copy())

    device = sd.default.device[0]
    chunk_frames = int(CHUNK_SECONDS * SAMPLE_RATE)
    snippet_path = Path(tempfile.gettempdir()) / "wake_listener_snippet.wav"

    print(f"{VOICE}: listening for a clap... (Ctrl+C to stop)")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=device,
        blocksize=chunk_frames,
        callback=_callback,
    ):
        last_trigger = 0.0
        while True:
            chunk = audio_q.get()
            if time.time() - last_trigger < COOLDOWN_SECONDS:
                continue
            if not is_clap(chunk):
                continue

            print(f'{VOICE}: clap detected -- listening for "{WAKE_PHRASE}"...')
            snippet = _collect_seconds(audio_q, LISTEN_AFTER_CLAP_SECONDS, seed=[chunk])
            _save_wav(snippet, snippet_path)

            heard = transcribe(str(snippet_path))
            heard_text = heard.get("text", "") if heard.get("ok") else ""

            if WAKE_PHRASE not in heard_text.lower():
                print(f"{VOICE}: no wake phrase heard -- back to listening.")
                continue

            last_trigger = time.time()
            print(f"{VOICE}: confirmed -- go ahead, recording for {CAPTURE_SECONDS:.0f}s...")
            capture = _collect_seconds(audio_q, CAPTURE_SECONDS)
            _save_wav(capture, snippet_path)

            transcription = transcribe(str(snippet_path))
            text = transcription.get("text", "").strip() if transcription.get("ok") else ""
            if not text:
                print(f"{VOICE}: didn't catch anything that time.")
                continue

            print(f"You said: {text}")
            result = route_capture(text)
            if not result.get("ok"):
                print(f"{VOICE}: routing failed -- {result.get('reason', 'unknown error')}")
            elif result["destination"] == "learning":
                print(f"{VOICE}: sent to Learning -- {result['cards_created']} flashcard(s) created.")
            else:
                print(f"{VOICE}: sent to Obsidian -- {result['path']}")

            print(f"\n{VOICE}: listening for a clap...")


if __name__ == "__main__":
    listen_forever()
