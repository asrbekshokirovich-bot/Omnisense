"""Run a WER evaluation over a JSONL dataset of {ref, hyp, lang} rows, grouped by language.

    python run_eval.py [dataset.jsonl ...]

With no args it evaluates the bundled samples. This is the gate for promoting any STT model
(cloud or self-hosted): produce {ref, hyp, lang} rows from your model, then run this.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from wer import wer

DEFAULTS = [Path(__file__).parent / "sample" / "ru.jsonl",
            Path(__file__).parent / "sample" / "uz.jsonl"]


def load(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or DEFAULTS
    rows = load(paths)
    by_lang: dict[str, list[float]] = {}
    for r in rows:
        score = wer(r["ref"], r["hyp"])
        by_lang.setdefault(r.get("lang", "??"), []).append(score)

    print(f"{'lang':<6}{'samples':>9}{'avg WER':>12}")
    print("-" * 27)
    all_scores: list[float] = []
    for lang, scores in sorted(by_lang.items()):
        all_scores += scores
        print(f"{lang:<6}{len(scores):>9}{sum(scores) / len(scores):>11.1%}")
    if all_scores:
        print("-" * 27)
        print(f"{'ALL':<6}{len(all_scores):>9}{sum(all_scores) / len(all_scores):>11.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
