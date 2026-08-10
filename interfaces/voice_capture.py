"""Local voice capture -- Mohamed speaks a quick thought, it's routed
automatically to wherever it belongs: a spaced-repetition flashcard
(agents.learning) for atomic facts worth remembering long-term, or a
freeform note (shared.obsidian.vault) for everything else.

Lives under interfaces/, not agents/learning/ or shared/, for the same
reason voice_session.py does -- this is cross-cutting routing between
two independent destinations, not agent logic belonging to either one.
Learning's own ingest_and_generate() and Obsidian's own write_note()
are both unchanged; this only decides which one a given capture goes
to.

The routing decision is a judgment call, not a hardcoded rule -- made
via shared/models/generate.py's chat() (defaults to Ollama, same
provider as every other classification-style judgment call in this
project: RII's research synthesis, Learning's flashcard generation,
Audit's QA review).

Usage: python -m interfaces.voice_capture
"""

import argparse

ROUTING_PROMPT = (
    "You decide where a transcribed voice note belongs. Read the text below "
    "and reply with EXACTLY one line in one of these two formats:\n"
    "LEARNING: <short category, 1-3 words>\n"
    "OBSIDIAN\n\n"
    "Choose LEARNING only for a short, atomic, factual statement worth "
    "memorizing long-term (a definition, a fact, a specific piece of "
    "knowledge) -- something that makes sense as a spaced-repetition "
    "flashcard. Choose OBSIDIAN for everything else: ideas, reflections, "
    "reminders, plans, questions, anything longer or more open-ended than "
    "a single fact.\n\nText:\n"
)


def classify_capture(text: str) -> dict:
    """Decides "learning" (with a category) or "obsidian" for a piece
    of transcribed text. Never raises -- falls back to "obsidian" (the
    safer default: a note is never lost, just possibly mis-filed) if
    the model call fails or its reply can't be parsed, rather than
    silently dropping the capture."""
    from shared.models.generate import chat

    result = chat(text, system=ROUTING_PROMPT)
    if not result.get("ok"):
        return {"destination": "obsidian", "category": None, "fallback_reason": result["reason"]}

    reply = result["reply"].strip()
    if reply.upper().startswith("LEARNING"):
        category = reply.split(":", 1)[1].strip() if ":" in reply else "general"
        return {"destination": "learning", "category": category or "general"}
    return {"destination": "obsidian", "category": None}


def route_capture(text: str, source_reference: str | None = None) -> dict:
    """Classifies text and dispatches it to the right destination.
    Returns the destination's own result dict (its own "ok"/"reason"
    shape, untouched) plus which destination was chosen."""
    decision = classify_capture(text)

    if decision["destination"] == "learning":
        from agents.learning.content_transform import ingest_and_generate

        result = ingest_and_generate(text, decision["category"], "voice", source_reference)
    else:
        from shared.obsidian.vault import write_note

        result = write_note(text, "voice", source_reference)

    result["destination"] = decision["destination"]
    if "fallback_reason" in decision:
        result["classification_fallback_reason"] = decision["fallback_reason"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a quick voice capture and route it automatically.")
    parser.add_argument("--seconds", type=float, default=8.0)
    args = parser.parse_args()

    from shared.voice.audio_io import record_audio
    from shared.voice.speech_to_text import transcribe

    print(f"Recording for {args.seconds:.0f}s -- speak now.")
    record_result = record_audio(args.seconds)
    if not record_result.get("ok"):
        print(f"Recording failed: {record_result['reason']}")
        return

    transcription = transcribe(record_result["path"])
    if not transcription.get("ok"):
        print(f"Couldn't transcribe: {transcription['reason']}")
        return

    text = transcription["text"]
    if not text.strip():
        print("Nothing was transcribed (silence?). Nothing routed.")
        return

    print(f"You said: {text}")
    result = route_capture(text)

    if not result.get("ok"):
        print(f"Routing failed: {result.get('reason', 'unknown error')}")
        return

    if result["destination"] == "learning":
        print(f"-> Learning: {result['cards_created']} flashcard(s) created.")
    else:
        print(f"-> Obsidian: note written to {result['path']}")


if __name__ == "__main__":
    main()
