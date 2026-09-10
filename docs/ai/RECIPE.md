# Recipe card: OpenAI GPT Live with the Agora Python SDK

Use this recipe when your Python backend should run an end-to-end GPT Live voice agent in an Agora channel.

| Item | Value |
| --- | --- |
| SDK | `agora-agents==2.8.0` |
| Provider | `openai_gpt_live` |
| Model | `gpt-live-1-diamond-alpha` |
| Voice | `cedar` |
| Data channel | RTM |
| Agent pipeline | MLLM only |

## Install

```bash
python -m pip install agora-agents==2.8.0
```

## Configure credentials

```dotenv
AGORA_APP_ID=your_agora_app_id
AGORA_APP_CERTIFICATE=your_agora_app_certificate
OPENAI_API_KEY=your_openai_api_key
```

Keep all three values on the server.

## Create the agent

```python
import os

from agora_agent import Area, AsyncAgora, OpenAIGPTLive
from agora_agent.agentkit import Agent

async def start_agent(channel: str, agent_uid: str, user_uid: str):
    client = AsyncAgora(
        area=Area.US,
        app_id=os.environ["AGORA_APP_ID"],
        app_certificate=os.environ["AGORA_APP_CERTIFICATE"],
    )

    mllm = OpenAIGPTLive(
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-live-1-diamond-alpha",
        alpha_selector="quicksilver=v3",
        voice="cedar",
        prompt="You are a concise and helpful voice assistant.",
        greeting="Hello! How can I help?",
        messages=[
            {"role": "user", "content": "My name is Arlene."},
            {"role": "assistant", "content": "Nice to meet you, Arlene."},
        ],
    )

    agent = Agent(
        client=client,
        advanced_features={"enable_rtm": True, "enable_tools": False},
        parameters={
            "audio_scenario": "chorus",
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        },
    ).with_mllm(mllm)

    session = agent.create_async_session(
        channel=channel,
        agent_uid=agent_uid,
        remote_uids=[user_uid],
        idle_timeout=30,
        expires_in=3600,
    )

    agent_id = await session.start()
    return agent_id, session
```

Generate the RTC+RTM token before starting the session. The browser and agent must join the same channel with different UIDs. Set `remote_uids` to the browser user's UID so the agent processes that user's audio.

## Parameter map

| Python option | Request field | Purpose |
| --- | --- | --- |
| `prompt` | `mllm.params.prompt` | Persistent system instructions |
| `greeting` | `mllm.greeting_message` | Opening line |
| `messages` | `mllm.messages` | Prior user and assistant turns |
| `voice` | `mllm.params.voice` | Output voice |
| `alpha_selector` | `mllm.params.alpha_selector` | Selects the GPT Live v3 contract |

Use `messages` for prior conversation. Keep system behavior in `prompt`.

## Stop the session

Retain the session object with its returned agent ID, then stop it through the same object:

```python
await session.stop()
```

For a multi-worker backend, store lifecycle ownership in shared state or route start and stop requests to the same worker.

## Try the complete sample

Return to the [project README](../../README.md) for credential setup, local run commands, browser UI, and troubleshooting.
