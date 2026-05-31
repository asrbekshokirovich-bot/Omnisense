"""Tests for the WER/CER eval harness.

Runs offline. Lives next to run_eval.py so the harness stays a single-folder unit; the
backend's main test suite (`backend/python -m pytest`) does not pick this up.

    cd ml/eval && python -m pytest -q
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

# Allow `from wer import …` / `from run_eval import …` when invoked from anywhere.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def test_wer_and_cer_basic():
    from wer import cer, wer
    assert wer("hello world", "hello world") == 0.0
    assert cer("hello world", "hello world") == 0.0
    # One word substituted out of two → 50% WER.
    assert wer("hello world", "hello there") == 0.5
    # CER is finer-grained: a one-char trailing edit is ~10% CER but 50% WER.
    assert wer("hello world", "hello worlds") == 0.5
    assert 0.05 < cer("hello world", "hello worlds") < 0.15


def test_normalization_strips_punctuation_and_case():
    from wer import wer
    assert wer("Hello, world!", "hello world") == 0.0


def test_uzbek_morphology_caught_by_cer():
    """A common Uzbek miss: kelishdik (we agreed) vs keldik (we came) — should produce
    both WER and CER signal."""
    from wer import cer, wer
    w = wer("biz kelishdik", "biz keldik")
    c = cer("biz kelishdik", "biz keldik")
    assert w > 0
    assert c > 0
    assert c < w  # CER < WER for partial-word edits — that is the point of having both


def test_eval_runs_on_bundled_samples():
    """Smoke: the harness still scores the bundled RU/UZ JSONL the same way it did
    before the refactor (pre-transcribed mode). 12.2% RU WER and 10.8% UZ WER."""
    import run_eval
    rows = run_eval._load([HERE / "sample" / "ru.jsonl", HERE / "sample" / "uz.jsonl"])
    scored = run_eval._score_rows(rows, provider=None, audio_dir=None)
    assert abs(scored["ru"]["wer"] - 0.12222) < 1e-3
    assert abs(scored["uz"]["wer"] - 0.10833) < 1e-3
    # CER should be lower than WER for these (small character edits within words).
    assert scored["ru"]["cer"] < scored["ru"]["wer"]
    assert scored["uz"]["cer"] < scored["uz"]["wer"]


def test_audio_mode_uses_provider(tmp_path):
    """Audio-mode: rows have `audio` paths, the harness reads the file and invokes the
    named provider. Uses the `mock` provider which round-trips bytes as text — so a
    perfect ref/audio match yields WER=0."""
    import run_eval
    (tmp_path / "clip.txt").write_text("hello world", encoding="utf-8")
    dataset = tmp_path / "data.jsonl"
    dataset.write_text(
        json.dumps({"lang": "en", "ref": "hello world", "audio": "clip.txt"}) + "\n",
        encoding="utf-8",
    )
    rc = run_eval.main([
        "--dataset", str(dataset),
        "--audio-dir", str(tmp_path),
        "--provider", "mock",
        "--json",
    ])
    assert rc == 0


def test_json_output_is_valid_and_lossless(capsys):
    import run_eval
    run_eval.main(["--json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "providers" in parsed
    assert "(pre-transcribed)" in parsed["providers"]
