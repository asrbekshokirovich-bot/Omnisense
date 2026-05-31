"""WER + CER evaluation over a JSONL dataset.

Two modes:

1) **Pre-transcribed**: each row has `ref` and `hyp` — fast, the bundled samples ride
   this. Use for grading hypotheses you already produced (Yandex, fine-tuned Whisper,
   anything).
2) **Audio mode**: each row has `ref` and `audio` (path relative to --audio-dir or
   absolute). The named provider transcribes the audio, the harness scores it.

Examples:

    # bundled samples (pre-transcribed)
    python run_eval.py

    # your own pre-transcribed file
    python run_eval.py --dataset mydata.jsonl

    # actually run Yandex on real audio (requires YANDEX_API_KEY env)
    python run_eval.py --dataset uz_audio.jsonl --audio-dir ./audio --provider yandex

    # compare multiple providers side-by-side
    python run_eval.py --provider yandex --provider mock --json > scores.json

Dataset format (JSONL):

    {"lang": "uz", "ref": "ground truth", "hyp": "model output"}      # pre-transcribed
    {"lang": "uz", "ref": "ground truth", "audio": "clip01.ogg"}      # audio mode

This is the gate from docs/development-plan.md §6 / §13: any STT candidate (cloud or
self-hosted in Tashkent) must beat the baseline on this harness before promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wer import cer, wer  # noqa: I001  (sibling module)

DEFAULTS = [
    Path(__file__).parent / "sample" / "ru.jsonl",
    Path(__file__).parent / "sample" / "uz.jsonl",
]


# ---- Provider registry -----------------------------------------------------
# Providers take audio bytes + a language code, return a transcript. "mock" exists so
# the harness can be smoke-tested end-to-end offline (e.g. in CI on the sample dataset).
def _build_provider(name: str):
    if name == "mock":
        # Round-trips the (UTF-8) audio bytes as text. Useful for unit-testing the harness.
        def transcribe(audio: bytes, lang: str) -> str:
            return audio.decode("utf-8", errors="ignore")
        return transcribe
    if name == "yandex":
        # Lazy import so the harness runs without the backend deps installed.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
        from app.providers.yandex_stt import YandexSTT  # type: ignore
        import os
        stt = YandexSTT(
            api_key=os.environ.get("YANDEX_API_KEY", ""),
            folder_id=os.environ.get("YANDEX_FOLDER_ID", ""),
        )
        def transcribe(audio: bytes, lang: str) -> str:
            return " ".join(s["text"] for s in stt.transcribe(audio, lang))
        return transcribe
    raise SystemExit(f"unknown provider: {name}")


def _load(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _hyp_for_row(row: dict, provider, audio_dir: Path | None) -> str:
    if "hyp" in row and provider is None:
        return row["hyp"]
    if "audio" in row:
        if provider is None:
            raise SystemExit(f"row has audio but no --provider configured: {row}")
        audio_path = Path(row["audio"])
        if not audio_path.is_absolute() and audio_dir is not None:
            audio_path = audio_dir / audio_path
        audio = audio_path.read_bytes()
        return provider(audio, row.get("lang", "ru"))
    # Fall back: provider is set but row has only hyp → just use hyp.
    return row.get("hyp", "")


def _score_rows(rows: list[dict], provider, audio_dir: Path | None) -> dict:
    by_lang: dict[str, dict] = {}
    for row in rows:
        lang = row.get("lang", "??")
        hyp = _hyp_for_row(row, provider, audio_dir)
        agg = by_lang.setdefault(lang, {"samples": 0, "wer_sum": 0.0, "cer_sum": 0.0})
        agg["samples"] += 1
        agg["wer_sum"] += wer(row["ref"], hyp)
        agg["cer_sum"] += cer(row["ref"], hyp)
    for agg in by_lang.values():
        n = agg["samples"]
        agg["wer"] = agg["wer_sum"] / n if n else 0.0
        agg["cer"] = agg["cer_sum"] / n if n else 0.0
        del agg["wer_sum"], agg["cer_sum"]
    return by_lang


def _format_table(per_provider: dict[str, dict]) -> str:
    pw = max(8, max(len(name) for name in per_provider))  # provider-column width
    out: list[str] = []
    header = f"{'provider':<{pw}}  {'lang':<5}{'samples':>9}{'avg WER':>11}{'avg CER':>11}"
    out.append(header)
    out.append("-" * len(header))
    for prov_name, by_lang in per_provider.items():
        all_w: list[float] = []
        all_c: list[float] = []
        for lang in sorted(by_lang):
            row = by_lang[lang]
            out.append(
                f"{prov_name:<{pw}}  {lang:<5}{row['samples']:>9}"
                f"{row['wer']:>10.1%}{row['cer']:>10.1%}"
            )
            all_w += [row["wer"]] * row["samples"]
            all_c += [row["cer"]] * row["samples"]
        if all_w:
            out.append(
                f"{prov_name:<{pw}}  {'ALL':<5}{len(all_w):>9}"
                f"{sum(all_w)/len(all_w):>10.1%}{sum(all_c)/len(all_c):>10.1%}"
            )
            out.append("")
    return "\n".join(out).rstrip()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="WER/CER eval for Omnisense STT candidates.")
    parser.add_argument("--dataset", action="append", type=Path, default=[],
                        help="JSONL dataset(s). Repeatable. Defaults to bundled RU/UZ.")
    parser.add_argument("--provider", action="append", default=[],
                        help="Provider name (mock | yandex). Repeatable. Omit to score "
                             "pre-transcribed hyp rows.")
    parser.add_argument("--audio-dir", type=Path, default=None,
                        help="Base dir for relative audio paths in the dataset.")
    parser.add_argument("--json", action="store_true",
                        help="Emit scores as JSON instead of a text table.")
    args = parser.parse_args(argv)

    paths = args.dataset or DEFAULTS
    rows = _load(paths)
    providers = args.provider or [None]  # None = use the row's own hyp field

    per_provider: dict[str, dict] = {}
    for name in providers:
        callable_ = _build_provider(name) if name else None
        per_provider[name or "(pre-transcribed)"] = _score_rows(rows, callable_, args.audio_dir)

    if args.json:
        print(json.dumps({
            "datasets": [str(p) for p in paths],
            "providers": per_provider,
        }, ensure_ascii=False, indent=2))
    else:
        print(_format_table(per_provider))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
