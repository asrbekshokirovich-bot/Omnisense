"""Ingest an audio file (or a .txt transcript) through the pipeline, then optionally ask.

    # offline (mock STT reads the file as a UTF-8 transcript):
    python ingest_file.py meeting.txt --lang uz --ask "demoni qachon yetkazamiz?"

    # real Uzbek/Russian STT (the Week-1 spike):
    OMNI_STT=yandex YANDEX_API_KEY=... YANDEX_FOLDER_ID=... \
        python ingest_file.py meeting.ogg --lang uz

Pair this with ml/eval/run_eval.py to score transcription quality.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.pipeline import Pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest an audio/transcript file into Omnisense.")
    ap.add_argument("path", help="audio file (real STT) or .txt transcript (mock STT)")
    ap.add_argument("--lang", default="ru", help="ru | uz | en")
    ap.add_argument("--source", default="file")
    ap.add_argument("--ask", default=None, help="optional question to run after ingest")
    args = ap.parse_args()

    data = Path(args.path).read_bytes()
    p = Pipeline()
    session = p.ingest_audio(data, args.lang, args.source)
    stats = p.stats()
    print(f"Ingested {Path(args.path).name} -> session {session.id[:8]} "
          f"({stats['segments']} memories) via STT={stats['providers']['stt']}")

    if args.ask:
        res = p.ask(args.ask, args.lang)
        print(f"\nQ: {args.ask}\nA: {res['answer']}")
        for c in res["citations"][:3]:
            print(f"   ↳ [{c['timestamp']}] {c['speaker']}: {c['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
