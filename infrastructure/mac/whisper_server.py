"""Local Whisper speech-to-text server -- runs on Mohamed's Mac, NOT
on the Windows machine this repo mostly runs on. Mirrors the Ollama
LAN pattern (a small local service exposed over the network, called
from shared/voice/speech_to_text.py on the Windows side).

Run: python3 -m uvicorn infrastructure.mac.whisper_server:app --host 0.0.0.0 --port 8100
(from the Mac, with fastapi/uvicorn/faster-whisper installed via
pip3 -- see CONTEXT.md's 2026-08-03 session log for the full setup
walkthrough.)

Uses faster-whisper (CTranslate2-based, much faster CPU inference than
plain openai-whisper) with the "base" model -- a reasonable balance of
speed/quality for an 8GB M1. Model auto-downloads on first request.
"""

import tempfile

from fastapi import FastAPI, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="Local Whisper STT Server")

# Loaded once at startup, reused across requests.
model = WhisperModel("base", device="cpu", compute_type="int8")


@app.post("/transcribe")
async def transcribe(file: UploadFile):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    segments, info = model.transcribe(tmp_path)
    text = " ".join(segment.text.strip() for segment in segments)
    return {"text": text, "language": info.language}


@app.get("/")
def health():
    return {"status": "Whisper server is running"}
