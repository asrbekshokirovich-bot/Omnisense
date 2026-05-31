"""Live-verify the Claude answer + briefing path in UZ / RU / EN, through the
consent gate.

Run:

    python scripts/verify_anthropic.py

Requires `ANTHROPIC_API_KEY` to be set — either in `backend/.env` (the auto-loaded
gitignored file) or in the process environment. The script force-reloads from
`backend/.env` to defeat the case where a parent shell has the variable set as
empty string (in which case `os.environ.setdefault` in `app.config._load_dotenv`
correctly refuses to overwrite, but the user actually wants the file value).

Checks:
  1. The region gate refuses /ask without `cross_border_llm` consent (HTTP 451).
  2. Granting consent unblocks the call.
  3. Claude returns a non-empty answer in each of the three target languages.
  4. The answer cites a segment that's actually in memory (no hallucinated sources).
     We check ALL returned citations — the top one is the highest-cosine match,
     but Claude is free to ground its answer in any of them.
  5. /briefing renders cleanly in each language (decisions or action_items present).

Exit code: 0 on full pass, non-zero on any failure. Failures print a clear diagnosis
without leaking the API key.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Windows console defaults to cp1251 → kills RU/UZ output. Force UTF-8 like demo.py.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def _bootstrap_path() -> None:
    """Make `backend/` importable regardless of CWD."""
    here = Path(__file__).resolve().parent
    backend = here.parent / "backend"
    if not backend.is_dir():
        print(f"FATAL: expected backend at {backend}", file=sys.stderr)
        sys.exit(2)
    sys.path.insert(0, str(backend))


def _force_load_anthropic_key() -> str:
    """Read backend/.env and OVERWRITE the env var. The normal _load_dotenv() uses
    setdefault so the user can pin a value in the parent shell — but for live
    verification we want the file to win, otherwise an empty parent-shell var
    silently masks the file's value."""
    env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
    if env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() == "ANTHROPIC_API_KEY":
                os.environ["ANTHROPIC_API_KEY"] = val.strip().strip('"').strip("'")
                break
    return os.environ.get("ANTHROPIC_API_KEY", "")


def _mask(key: str) -> str:
    if len(key) <= 14:
        return f"<{len(key)} chars>"
    return f"{key[:10]}…{key[-4:]}"


SAMPLE_MEETING = [
    ("owner",     "Bugun mijoz bilan demo haqida gaplashdik."),
    ("speaker_2", "We agreed to deliver the first demo by Friday."),
    ("owner",     "Narxni keyinroq hal qilamiz, lekin men ertaga taklif yuboraman."),
    ("speaker_2", "I will prepare the contract draft tomorrow morning."),
]

PROBES = [
    # (lang, question, expected substring(s) in the cited segment)
    ("uz", "demoni qachon yetkazamiz?",
     ("juma", "friday", "yetkazib", "demoni", "demo")),
    ("ru", "Кто готовит контракт?",
     ("contract", "prepare", "draft", "shartnoma")),
    ("en", "what was decided about the price?",
     ("price", "narx", "narxni", "later", "hal")),
]


class Failure(Exception):
    """Raised when a check fails. The runner prints the message and exits 1."""


def main() -> int:
    _bootstrap_path()
    key = _force_load_anthropic_key()
    if not key:
        print("FAIL: ANTHROPIC_API_KEY not set (looked in backend/.env + environ).",
              file=sys.stderr)
        return 1
    print(f"key: {_mask(key)} ({len(key)} chars)")

    # Force the live LLM provider before anything constructs the pipeline.
    os.environ["OMNI_LLM"] = "anthropic"

    # Reload config + downstream modules so the Settings dataclass picks up OMNI_LLM.
    import importlib
    import app.config
    import app.providers
    import app.pipeline
    importlib.reload(app.config)
    importlib.reload(app.providers)
    importlib.reload(app.pipeline)
    from app.pipeline import ConsentRequired, Pipeline  # noqa: I001

    p = Pipeline(app.config.settings)
    p.delete_all()

    # Seed the sample meeting via the audio path so MockSTT splits into segments.
    transcript = "\n".join(text for _, text in SAMPLE_MEETING)
    sess = p.ingest_audio(transcript.encode("utf-8"), lang="uz", source="verify")
    seg_count = len([s for s in p.store.all_segments("default") if s.session_id == sess.id])
    if seg_count < len(SAMPLE_MEETING):
        raise Failure(
            f"ingest produced {seg_count} segments but expected >= {len(SAMPLE_MEETING)}; "
            f"the sample meeting was not chunked as planned"
        )
    print(f"seeded {seg_count} segments under session {sess.id[:8]}")
    print()

    # ---- 1. Region gate refuses without consent -----------------------------
    print("[1] region gate without consent: expecting ConsentRequired")
    try:
        p.ask(PROBES[0][1], lang=PROBES[0][0])
    except ConsentRequired as e:
        if e.scope != "cross_border_llm" or e.provider != "anthropic":
            raise Failure(
                f"wrong gate error: scope={e.scope!r}, provider={e.provider!r}"
            )
        print(f"  OK: refused scope={e.scope!r} provider={e.provider!r}")
    else:
        raise Failure("region gate did NOT refuse; cross-border call went through "
                      "without consent — privacy regression")
    print()

    # ---- 2. Grant consent ---------------------------------------------------
    print("[2] granting cross_border_llm consent")
    p.consent().record("cross_border_llm", True, reason="scripts/verify_anthropic.py")
    if not p.consent().is_granted("cross_border_llm"):
        raise Failure("consent record() returned but is_granted() is False")
    print("  OK: scope LLM_TEXT (cross_border_llm) is now granted")
    print()

    # ---- 3-4. Live /ask in each language ------------------------------------
    failures: list[str] = []
    for lang, question, expected_any in PROBES:
        print(f"[3.{lang}] /ask in {lang!r}: {question}")
        t0 = time.monotonic()
        try:
            r = p.ask(question, lang=lang)
        except Exception as e:
            failures.append(f"[{lang}] ask raised {type(e).__name__}: {e}")
            print(f"  FAIL: {type(e).__name__}: {e}")
            print()
            continue
        dt = time.monotonic() - t0
        ans = (r.get("answer") or "").strip()
        cites = r.get("citations") or []
        if not ans:
            failures.append(f"[{lang}] answer empty")
            print("  FAIL: empty answer")
        elif not cites:
            failures.append(f"[{lang}] no citations returned")
            print("  FAIL: no citations")
        else:
            existing = {s.text.lower() for s in p.store.all_segments("default")}
            print(f"  status: 200 in {dt:.2f}s")
            print(f"  answer (first 200): {ans[:200]!r}")
            for i, c in enumerate(cites):
                print(f"  cite[{i}]: [{c.get('timestamp')}] {c.get('speaker')}: "
                      f"{(c.get('text') or '')[:80]!r}")
            # Grounding: SOME citation in the top-K must contain an expected substring.
            grounded_idx = None
            for i, c in enumerate(cites):
                ct = (c.get("text") or "").lower()
                if any(needle.lower() in ct for needle in expected_any):
                    grounded_idx = i
                    break
            if grounded_idx is None:
                failures.append(
                    f"[{lang}] no citation contains any of {expected_any} — possible "
                    f"hallucinated source. citations: "
                    f"{[c.get('text','')[:60] for c in cites]}"
                )
                print(f"  FAIL: no citation matches expected substrings")
            else:
                print(f"  grounded via cite[{grounded_idx}]")
            # No-hallucination: every returned citation text must exist in the store.
            invented = [c.get("text", "") for c in cites
                        if (c.get("text") or "").lower() not in existing]
            if invented:
                failures.append(
                    f"[{lang}] {len(invented)} citation(s) not present in memory: "
                    f"{[t[:60] for t in invented]}"
                )
                print(f"  FAIL: {len(invented)} citation(s) do not exist in memory")
        print()

    # ---- 5. /briefing in each language --------------------------------------
    for lang in ("en", "ru", "uz"):
        print(f"[4.{lang}] /briefing in {lang!r}")
        t0 = time.monotonic()
        try:
            b = p.briefing(lang=lang)
        except Exception as e:
            failures.append(f"[briefing {lang}] raised {type(e).__name__}: {e}")
            print(f"  FAIL: {type(e).__name__}: {e}")
            continue
        dt = time.monotonic() - t0
        summary = (b.get("summary") or "").strip()
        decisions = b.get("decisions") or []
        actions = b.get("action_items") or []
        print(f"  status: 200 in {dt:.2f}s")
        print(f"  summary (first 140): {summary[:140]!r}")
        print(f"  decisions: {len(decisions)}, action_items: {len(actions)}")
        if not summary:
            failures.append(f"[briefing {lang}] empty summary")
            print("  FAIL: empty summary")
        if not (decisions or actions):
            failures.append(
                f"[briefing {lang}] both decisions[] and action_items[] are empty; "
                f"a meeting with 'We agreed' + 'I will' should produce something"
            )
            print("  FAIL: no decisions or action_items")
        print()

    if failures:
        print("=" * 60)
        print("VERIFICATION FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("=" * 60)
    print("ALL CHECKS PASSED — Anthropic answer + briefing live in UZ/RU/EN, "
          "consent gate behaves correctly.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Failure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
