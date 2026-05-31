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
    """Short-audio synchronous path (the demo's bread and butter)."""
    fake, calls = _capture({"result": "salom dunyo"})
    monkeypatch.setattr(httpx, "post", fake)
    from app.providers.yandex_stt import YandexSTT

    segs = YandexSTT("key123", "folder42").transcribe(b"audio-bytes", "uz")

    assert segs[0]["text"] == "salom dunyo"
    assert calls["url"].endswith("stt:recognize")
    assert calls["kw"]["params"]["lang"] == "uz-UZ"
    assert calls["kw"]["params"]["folderId"] == "folder42"
    assert calls["kw"]["params"]["format"] == "oggopus"
    assert calls["kw"]["headers"]["Authorization"] == "Api-Key key123"
    assert calls["kw"]["content"] == b"audio-bytes"


def test_yandex_stt_async_path_for_long_audio(monkeypatch):
    """Long-audio path: submit (POST) → poll until done (GET) → parse speaker-labeled
    chunks. We size the input above the sync threshold and stub both verbs."""
    from app.providers import yandex_stt as ystt_mod

    big_audio = b"x" * (1_000_000)  # > 900 KB → async path
    posts: list[dict] = []
    gets: list[dict] = []

    def fake_post(url, **kw):
        posts.append({"url": url, "kw": kw})
        return FakeResp({"id": "op-42"})  # operation submission ack

    def fake_get(url, **kw):
        gets.append({"url": url, "kw": kw})
        return FakeResp({
            "done": True,
            "response": {"chunks": [
                {"alternatives": [{"text": "первая реплика"}],
                 "startTime": "0.000s", "endTime": "5.500s", "speakerTag": "1"},
                {"alternatives": [{"text": "второй спикер"}],
                 "startTime": "5.500s", "endTime": "10.000s", "speakerTag": "2"},
            ]},
        })

    monkeypatch.setattr(ystt_mod, "time", type("T", (), {"monotonic": staticmethod(lambda: 0.0),
                                                          "sleep": staticmethod(lambda _t: None)}))
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    from app.providers.yandex_stt import YandexSTT
    segs = YandexSTT("sk", "folder42", poll_interval_s=0.0).transcribe(big_audio, "ru")

    assert [s["text"] for s in segs] == ["первая реплика", "второй спикер"]
    assert segs[0]["start_ms"] == 0 and segs[0]["end_ms"] == 5500
    assert segs[1]["speaker"] == "speaker_2"
    # The submission hit the long-running endpoint, the poll hit the operations API.
    assert posts and posts[0]["url"].endswith("longRunningRecognize")
    assert gets and "operations/op-42" in gets[0]["url"]


# ---- OpenAI-compatible ---------------------------------------------------
def test_openai_embedding(monkeypatch):
    fake, calls = _capture({"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})
    monkeypatch.setattr(httpx, "post", fake)
    from app.providers.llm_openai import OpenAIEmbedding

    emb = OpenAIEmbedding("k", "https://api.openai.com/v1", "text-embedding-3-small", dim=1536)
    out = emb.embed(["a", "b"])
    assert out == [[0.1, 0.2], [0.3, 0.4]]
    assert emb.dim == 1536
    # Self-hostable: the model name is sent verbatim, so a TEI/vLLM box serving
    # "BAAI/bge-m3" answers the same code path.
    assert calls["kw"]["json"]["model"] == "text-embedding-3-small"
    assert calls["kw"]["json"]["input"] == ["a", "b"]


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
