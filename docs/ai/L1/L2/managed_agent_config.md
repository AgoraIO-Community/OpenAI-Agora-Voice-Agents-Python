# OpenAI GPT Live Agent Config

> **When to Read This:** Load this document when changing the Python preview agent, greeting, credentials, or session options.

The backend integration lives in `server/src/agent.py`. `Agent.__init__` reads the Agora credentials and `OPENAI_API_KEY`, then constructs the standard `AsyncAgora` client. It detects OpenAI GPT Live and routes start through the preview endpoint.

```python
self.client = AsyncAgora(
    area=Area.US,
    app_id=self.app_id,
    app_certificate=self.app_certificate,
)

mllm = OpenAIGPTLive(
    api_key=self.openai_api_key,
    model="gpt-live-1-diamond-alpha",
    voice="cedar",
    prompt=self.instructions,
    greeting=self.greeting,
)

agora_agent = AgoraAgent(
    client=self.client,
    advanced_features={"enable_rtm": True, "enable_tools": False},
    parameters={
        "audio_scenario": "chorus",
        "data_channel": "rtm",
        "enable_error_message": True,
        "enable_metrics": True,
    },
).with_mllm(mllm)
```

`OpenAIGPTLive` emits `mllm.vendor: "openai_gpt_live"`, `wss://api.openai.com/v1/live/sessions`, and `greeting_message` for the opening line. Do not add `.with_stt()`, `.with_llm()`, or `.with_tts()` to this demo.

Required server environment:

```bash
AGORA_APP_ID=...
AGORA_APP_CERTIFICATE=...
OPENAI_API_KEY=...
```

`AGENT_GREETING` and `AGENT_INSTRUCTIONS` are optional. `AGENT_PRIOR_MESSAGES` accepts a JSON array of user/assistant text turns and is sent as `mllm.messages`, separately from the prompt. Sessions keep numeric RTC identities serialized as strings and keep `remote_uids` as an array. Started sessions are stored in a worker-local map by agent ID. Stop removes and calls that retained session; unknown IDs are idempotent success and there is no standalone `client.stop_agent` fallback.

Run `server/venv/bin/pytest server/tests -q` and `bun run build` after changes.
