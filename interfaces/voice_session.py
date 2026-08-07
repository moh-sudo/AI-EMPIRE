"""Local voice session -- Mohamed speaks to a division's agent while
at this computer, gets a reply back (spoken once TTS is connected,
printed today).

Lives under interfaces/, not agents/<division>/, because it's cross-
division routing/UI, not agent logic -- it's allowed to know about
multiple divisions (Fixera, Forex, whatever comes next) the same way
agents/fixera/server.py is allowed to know about Fixera specifically.
Each division's actual question-answering logic stays exactly where it
already lives (agents/fixera/telegram_listener.py's answer_question(),
agents/forex/telegram_listener.py's answer_question()) -- this script
only adds a voice front-end on top, it doesn't duplicate that logic.

Architecture-only per Mohamed's instruction (2026-08-01): real
microphone recording (shared/voice/audio_io.py) is fully working today.
Speech-to-text and text-to-speech (shared/voice/speech_to_text.py,
text_to_speech.py) are both deliberately stubbed -- this script proves
the full pipeline's shape (record -> transcribe -> route to the right
division -> answer -> speak) and fails closed at the transcription
step until a real STT model is connected. Nothing here is faked to
look like it works when it doesn't.

Usage: python -m interfaces.voice_session --division fixera
"""

import argparse

DIVISIONS = {
    "fixera": "agents.fixera.telegram_listener",
    "forex": "agents.forex.telegram_listener",
}

RECORD_SECONDS = 5.0


def _get_answer_fn(division: str):
    import importlib

    module = importlib.import_module(DIVISIONS[division])
    return module.answer_question


def run_voice_session(division: str) -> None:
    if division not in DIVISIONS:
        print(f"Unknown division '{division}'. Choose one of: {', '.join(DIVISIONS)}")
        return

    from shared.voice.audio_io import list_input_devices, record_audio
    from shared.voice.speech_to_text import transcribe
    from shared.voice.text_to_speech import synthesize

    devices = list_input_devices()
    if not devices or "error" in devices[0]:
        print(f"No working microphone detected: {devices}")
        return
    print(f"Microphone detected: {devices[0]['name']}")

    answer_fn = _get_answer_fn(division)
    print(
        f"Voice session started for {division.upper()}. Press Enter to record a {RECORD_SECONDS:.0f}s question, Ctrl+C to quit."
    )

    while True:
        try:
            input("\n[Press Enter to speak]")
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            return

        print("Recording...")
        record_result = record_audio(RECORD_SECONDS)
        if not record_result.get("ok"):
            print(f"Recording failed: {record_result.get('reason')}")
            continue

        transcription = transcribe(record_result["path"])
        if not transcription.get("ok"):
            print(f"Couldn't process that: {transcription.get('reason')}")
            continue

        # Unreachable today (transcribe() always returns ok=False) --
        # kept real so this activates automatically once a real STT
        # model is wired into speech_to_text.py, no changes needed here.
        text = transcription["text"]
        print(f"You said: {text}")

        result = answer_fn(text)
        reply = result["reply"]
        print(f"{division.upper()}: {reply}")

        speech = synthesize(reply)
        if speech.get("ok"):
            from shared.voice.audio_io import play_audio

            play_audio(speech["path"])
        else:
            print(f"(spoken reply unavailable: {speech.get('reason')})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local voice session with an AI_EMPIRE division agent.")
    parser.add_argument("--division", choices=list(DIVISIONS), required=True)
    args = parser.parse_args()
    run_voice_session(args.division)


if __name__ == "__main__":
    main()
