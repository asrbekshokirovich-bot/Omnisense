"""Quick offline demo of the Omnisense loop (no keys, no infra).

    python demo.py

Seeds a sample meeting, asks a question, and prints the morning briefing — the exact loop
the investor demo shows, but in the terminal.
"""
import sys

# On Windows the default console encoding (cp1251) can't render the citation arrow ↳
# without crashing. Force UTF-8 on the streams so the demo runs identically across
# Mac / Linux / Windows. (No effect on already-UTF-8 platforms.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from app.pipeline import Pipeline

SAMPLE_MEETING = [
    ("owner", "Bugun mijoz bilan demo haqida gaplashdik."),
    ("speaker_2", "We agreed to deliver the first demo by Friday."),
    ("owner", "Narxni keyinroq hal qilamiz, lekin men ertaga taklif yuboraman."),
    ("speaker_2", "I will prepare the contract draft tomorrow morning."),
]


def main() -> None:
    p = Pipeline()
    p.delete_all()

    # Use the audio path: MockSTT splits each line into a speaker-attributed, timed segment
    # (feed a real .wav here once OMNI_STT=yandex). This gives multiple distinct memories.
    transcript = "\n".join(text for _, text in SAMPLE_MEETING)
    session = p.ingest_audio(transcript.encode("utf-8"), lang="uz", source="demo-meeting")
    print(f"Ingested session {session.id[:8]} · {p.stats()['segments']} memories\n")

    for q, lang in [("demoni qachon yetkazamiz?", "uz"), ("who prepares the contract?", "en")]:
        res = p.ask(q, lang=lang)
        print(f"Q: {q}\nA: {res['answer']}")
        if res["citations"]:
            c = res["citations"][0]
            print(f"   ↳ cite: [{c['timestamp']}] {c['speaker']}: {c['text']}")
        print()

    brief = p.briefing(lang="en")
    print("Morning briefing:")
    print(f"  summary: {brief['summary']}")
    print(f"  action_items: {brief['action_items']}")


if __name__ == "__main__":
    main()
