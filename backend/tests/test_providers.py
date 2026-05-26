"""Unit tests for the real provider adapters. The HTTP layer (httpx.post) is monkeypatched,
so these run offline with no API keys — they verify we build the right request and parse the
right response for Yandex STT, OpenAI, and Anthropic."""
import httpx
import pytest


class FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _capture(payload):
    calls = {}

    def fake_post(url, **kw):
        calls["url"] = url
        calls["kw"] = kw
        return FakeResp(payload)

    return fake_post, calls


# ---- Yandex STT ----------------------------------------------------------
def test_yandex_stt_request_and_parse(monkeypatch):
    fake, calls = _capture({"result": "salom dunyo"})
    monkeypatch.setattr(httpx, "post", fake)
    from app.providers.yandex_stt import YandexSTT

    segs = YandexSTT("key123", "folder42").transcribe(b"audio-bytes", "uz")

    assert segs[0]["text"] == "salom dunyo"
    assert calls["url"].endswith("stt:recognize")
    assert calls["kw"]["params"]["lang"] == "uz-UZ"
    assert calls["kw"]["params"]["folderId"] == "folder42"
    assert calls["kw"]["headers"]["Authorization"] == "Api-Key key123"
    assert calls["kw"]["content"] == b"audio-bytes"


# ---- OpenAI-compatible ---------------------------------------------------
def test_openai_embedding(monkeypatch):
    fake, _ = _capture({"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})
    monkeypatch.setattr(httpx, "post", fake)
    from app.providers.llm_openai import OpenAIEmbedding

    out = OpenAIEmbedding("k", "https://api.openai.com/v1", "text-embedding-3-small").embed(["a", "b"])
    assert out == [[0.1, 0.2], [0.3, 0.4]]


def test_openai_llm_answer_and_summary(monkeypatch):
    from app.providers.llm_openai import OpenAILLM

    fake, calls = _capture({"choices": [{"message": {"content": "the answer"}}]})
    monkeypatch.setattr(httpx, "post", fake)
    llm = OpenAILLM("k", "https://api.openai.com/v1", "gpt-4o-mini")
    ans = llm.answer("q", [{"text": "x", "speaker": "o", "timestamp": "00:00"}], "en")
    assert ans == "the answer"
    assert calls["kw"]["json"]["model"] == "gpt-4o-mini"

    fake2, _ = _capture({"choices": [{"message": {"content":
        '{"summary":"s","decisions":[],"action_items":["a"],"key_quotes":[]}'}}]})
    monkeypatch.setattr(httpx, "post", fake2)
    brief = llm.summarize_day([{"text": "we will do x"}], "en")
    assert brief["action_items"] == ["a"]


# ---- Anthropic (Claude) --------------------------------------------------
def test_anthropic_answer_request_and_parse(monkeypatch):
    fake, calls = _capture({"content": [{"type": "text", "text": "javob"}]})
    monkeypatch.setattr(httpx, "post", fake)
    from app.providers.llm_anthropic import AnthropicLLM

    llm = AnthropicLLM("sk-ant", "claude-haiku-4-5-20251001")
    ans = llm.answer("savol", [{"text": "x", "speaker": "owner", "timestamp": "00:00"}], "uz")

    assert ans == "javob"
    assert calls["url"].endswith("/v1/messages")
    assert calls["kw"]["headers"]["x-api-key"] == "sk-ant"
    assert calls["kw"]["json"]["model"] == "claude-haiku-4-5-20251001"


def test_anthropic_summary_extracts_json(monkeypatch):
    fake, _ = _capture({"content": [{"type": "text", "text":
        'Here you go: {"summary":"day","decisions":["d"],"action_items":["a"],"key_quotes":[]}'}]})
    monkeypatch.setattr(httpx, "post", fake)
    from app.providers.llm_anthropic import AnthropicLLM

    brief = AnthropicLLM("sk-ant", "claude-haiku-4-5-20251001").summarize_day([{"text": "x"}], "en")
    assert brief["decisions"] == ["d"]
    assert brief["action_items"] == ["a"]


def test_missing_key_raises():
    from app.providers.llm_anthropic import AnthropicLLM
    with pytest.raises(ValueError):
        AnthropicLLM("", "claude-haiku-4-5-20251001")
