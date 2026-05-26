# ml — speech models & evaluation

Home of the **Uzbek/Russian speech-to-text workstream** (the moat) and its eval harness.

## WER + CER eval harness (the Week-1 risk check)
The single most important early check: *how good is Uzbek/Russian transcription?* Produce
`{ref, hyp, lang}` rows from any STT model, or point the harness at a directory of audio
and let it call the provider for you, then score.

```bash
cd ml/eval

# Bundled RU/UZ samples (pre-transcribed).
python run_eval.py

# Your own pre-transcribed file.
python run_eval.py --dataset mydata.jsonl

# Actually run Yandex on real Uzbek audio. Needs YANDEX_API_KEY in env.
python run_eval.py --dataset uz_audio.jsonl --audio-dir ./audio --provider yandex

# Compare providers side-by-side; emit JSON for CI / dashboards.
python run_eval.py --provider yandex --provider mock --json > scores.json

# Test the harness itself.
python -m pytest -q
```

Output is per-language **WER** and **CER**. CER protects against Uzbek-morphology misses
that look small at the character level but flip a whole word at WER (e.g. *kelishdik* vs
*keldik*). Both metrics gate any STT promotion.

Dataset formats (JSONL, one row per utterance):
```json
{"lang": "uz", "ref": "ground truth transcript", "hyp": "model output"}
{"lang": "uz", "ref": "ground truth transcript", "audio": "clip01.ogg"}
```

## Roadmap (per docs/development-plan.md §6)
- **Data:** UzbekVoice (~1,400h), Common Voice Uzbek (~265h), USC, FeruzaSpeech.
- **Model:** fine-tune Whisper (medium → large-v3) on Uzbek; add a meeting-domain LM.
- **Serve:** faster-whisper / CTranslate2 on a GPU **in Tashkent** (residency + cost).
- **Gate:** beat the cloud baseline on this harness before promoting to production.
