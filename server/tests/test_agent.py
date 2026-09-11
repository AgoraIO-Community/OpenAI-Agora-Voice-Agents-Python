"""Agent env validation + OpenAI GPT Live MLLM wiring."""
import asyncio
import sys

import pytest


def _fresh_agent_module():
    sys.modules.pop("agent", None)
    import agent

    return agent


@pytest.mark.parametrize("missing", ["AGORA_APP_ID", "AGORA_APP_CERTIFICATE", "OPENAI_API_KEY"])
def test_agent_requires_env(fake_env, monkeypatch, missing):
    monkeypatch.delenv(missing, raising=False)
    agent = _fresh_agent_module()
    with pytest.raises(ValueError):
        agent.Agent()


def test_agent_constructs_with_full_env(fake_env):
    agent = _fresh_agent_module()
    from agora_agent import AsyncAgora

    instance = agent.Agent()
    assert instance.app_id == "00000000000000000000000000000000"
    assert isinstance(instance.client, AsyncAgora)
    assert instance.prior_messages == []


def test_agent_parses_prior_messages(fake_env, monkeypatch):
    monkeypatch.setenv(
        "AGENT_PRIOR_MESSAGES",
        '[{"role":"user","content":"My name is Arlene."},'
        '{"role":"assistant","content":"Nice to meet you."}]',
    )
    agent = _fresh_agent_module()

    assert agent.Agent().prior_messages == [
        {"role": "user", "content": "My name is Arlene."},
        {"role": "assistant", "content": "Nice to meet you."},
    ]


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        "{}",
        '[{"role":"system","content":"No"}]',
        '[{"role":"user","content":42}]',
    ],
)
def test_agent_rejects_invalid_prior_messages(fake_env, monkeypatch, value):
    monkeypatch.setenv("AGENT_PRIOR_MESSAGES", value)
    agent = _fresh_agent_module()

    with pytest.raises(ValueError, match="AGENT_PRIOR_MESSAGES"):
        agent.Agent()


def test_start_wires_openai_gpt_live_mllm_and_returns_shape(fake_env, monkeypatch):
    agent = _fresh_agent_module()
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

        async def stop(self):
            captured["stopped"] = True

    def fake_create_async_session(self, **kwargs):
        captured["mllm"] = self.mllm
        captured["llm"] = self.llm
        captured["stt"] = self.stt
        captured["tts"] = self.tts
        captured["channel"] = kwargs.get("channel")
        captured["remote_uids"] = kwargs.get("remote_uids")
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    instance = agent.Agent()
    result = asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))

    assert result == {
        "agent_id": "test-agent-id",
        "channel_name": "ch",
        "status": "started",
    }
    assert captured["llm"] is None
    assert captured["stt"] is None
    assert captured["tts"] is None
    assert captured["mllm"] == {
        "enable": True,
        "vendor": "openai_gpt_live",
        "api_key": "test-openai-api-key",
        "url": "wss://api.openai.com/v1/live/sessions",
        "greeting_message": agent.DEFAULT_GREETING,
        "messages": [],
        "params": {
            "model": "gpt-live-1",
            "voice": "cedar",
            "prompt": agent.DEFAULT_INSTRUCTIONS,
        },
    }
    assert captured["channel"] == "ch"
    assert captured["remote_uids"] == ["222"]


def test_start_validates_arguments(fake_env, monkeypatch):
    agent = _fresh_agent_module()
    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", lambda self, **k: None)
    instance = agent.Agent()
    with pytest.raises(ValueError):
        asyncio.run(instance.start(channel_name="", agent_uid=1, user_uid=2))
    with pytest.raises(ValueError):
        asyncio.run(instance.start(channel_name="c", agent_uid=0, user_uid=2))


def test_stop_uses_active_session_and_unknown_id_is_idempotent(fake_env, monkeypatch):
    agent = _fresh_agent_module()

    class FakeSession:
        def __init__(self):
            self.stopped = False

        async def start(self):
            return "agent-xyz"

        async def stop(self):
            self.stopped = True

    session = FakeSession()
    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", lambda self, **k: session)
    instance = agent.Agent()

    asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))
    asyncio.run(instance.stop("agent-xyz"))
    assert session.stopped is True

    asyncio.run(instance.stop("unknown-id"))


def test_stop_propagates_retained_session_error(fake_env, monkeypatch):
    agent = _fresh_agent_module()

    class FakeSession:
        async def start(self):
            return "agent-xyz"

        async def stop(self):
            raise RuntimeError("session stale")

    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(
        AgoraAgent, "create_async_session", lambda self, **k: FakeSession()
    )
    instance = agent.Agent()
    asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))

    with pytest.raises(RuntimeError, match="session stale"):
        asyncio.run(instance.stop("agent-xyz"))
