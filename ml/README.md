# ml — speech models & evaluation

Home of the **Uzbek/Russian speech-to-text workstream** (the moat) and its eval harness.

## WER eval harness (the Week-1 risk check)
The single most important early check: *how good is Uzbek/Russian transcription?* Produce
`{ref, hyp, lang}` rows from any STT model (cloud Yandex now, self-hosted fine-tuned Whisper
later) and score them:
```bash
cd ml/eval
python run_eval.py                 # bundled RU/UZ samples
python run_eval.py mydata.jsonl    # your model's outputs
```
Output is per-language average **WER** — the gate for promoting any STT model.

Dataset format (JSONL, one row per utterance):
```json
{"lang": "uz", "ref": "ground truth transcript", "hyp": "model output"}
```

## Roadmap (per docs/development-plan.md §6)
- **Data:** UzbekVoice (~1,400h), Common Voice Uzbek (~265h), USC, FeruzaSpeech.
- **Model:** fine-tune Whisper (medium → large-v3) on Uzbek; add a meeting-domain LM.
- **Serve:** faster-whisper / CTranslate2 on a GPU **in Tashkent** (residency + cost).
- **Gate:** beat the cloud baseline on this harness before promoting to production.
