"""Real diarization via pyannote-audio. Used when OMNI_DIARIZER=pyannote.

Runtime requirements (NOT installed by the base requirements.txt — keeps the offline demo
light, and HuggingFace is blocked in this sandbox so we cannot smoke-test here):

    pip install pyannote.audio>=3.1 torchaudio soundfile

You also need:
  - HF_TOKEN with access to `pyannote/speaker-diarization-3.1` and `pyannote/embedding`
    (both are gated — accept the model EULA on HuggingFace once per account).
  - ~250 MB of weights cached under HF_HOME on first run.

Residency: pyannote runs **locally** — voice and voiceprints never leave the box. This is
the in-country path in docs/development-plan.md. The cloud-STT call (Yandex) and the cloud
LLM call (Anthropic) get TEXT only; voiceprints stay here.

Audio handling: pyannote expects a tensor/waveform, not raw bytes. We decode through
`soundfile` (supports WAV, FLAC, OGG; for compressed inputs the team should resample to
16 kHz mono WAV in the mobile/edge layer before upload, per the pipeline doc §5).
"""
from __future__ import annotations

import io
import os

from .base import Diarizer


class PyannoteDiarizer(Diarizer):
    """Wraps pyannote's speaker-diarization-3.1 pipeline + pyannote/embedding inference."""

    def __init__(self, hf_token: str | None = None, device: str = "cpu") -> None:
        # All heavy imports are lazy so importing this module costs ~nothing when pyannote
        # is not installed — tests can still load the file and assert it raises a clean
        # error path on missing deps / token.
        token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if not token:
            raise ValueError(
                "OMNI_DIARIZER=pyannote requires HF_TOKEN (gated models on HuggingFace)."
            )

        from pyannote.audio import Inference, Pipeline  # lazy
        import torch  # lazy

        self._torch = torch
        self._diar = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", use_auth_token=token,
        ).to(torch.device(device))
        self._embed = Inference("pyannote/embedding", window="whole", use_auth_token=token)
        # pyannote/embedding emits 192-dim vectors (ECAPA-style).
        self._dim = 192

    @property
    def dim(self) -> int:
        return self._dim

    def _waveform(self, audio: bytes):
        """Decode bytes → (waveform tensor, sample_rate). Mono. 16 kHz preferred upstream."""
        import soundfile as sf  # lazy
        import numpy as np  # lazy (pulled in by pyannote anyway)

        wav, sr = sf.read(io.BytesIO(audio), dtype="float32", always_2d=True)
        wav = wav.mean(axis=1)  # mix down to mono
        tensor = self._torch.from_numpy(np.asarray(wav)).unsqueeze(0)
        return tensor, sr

    def diarize(self, audio: bytes) -> list[dict]:
        wav, sr = self._waveform(audio)
        annotation = self._diar({"waveform": wav, "sample_rate": sr})
        turns: list[dict] = []
        for segment, _track, label in annotation.itertracks(yield_label=True):
            start = float(segment.start)
            end = float(segment.end)
            # Embed just this turn so each turn carries its own voiceprint.
            clip = wav[:, int(start * sr): int(end * sr)]
            vec = self._embed({"waveform": clip, "sample_rate": sr})
            turns.append({
                "start_ms": int(start * 1000),
                "end_ms": int(end * 1000),
                "speaker_label": str(label),
                "voiceprint": [float(x) for x in vec.flatten().tolist()],
            })
        return turns

    def embed_voice(self, audio: bytes) -> list[float]:
        wav, sr = self._waveform(audio)
        vec = self._embed({"waveform": wav, "sample_rate": sr})
        return [float(x) for x in vec.flatten().tolist()]
