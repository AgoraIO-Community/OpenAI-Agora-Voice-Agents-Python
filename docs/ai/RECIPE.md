# Build an OpenAI GPT Live voice agent with Python

Use Agora's Python SDK to place an OpenAI GPT Live voice agent in an Agora channel. GPT Live handles speech input, reasoning, and speech output as one MLLM stage. The included browser client publishes microphone audio and displays transcripts, agent state, and latency metrics.

| Item | Value |
| --- | --- |
| SDK | `agora-agents==2.8.1` |
| Provider | `openai_gpt_live` |
| Model | `gpt-live-1` |
| Voice | `cedar` |
| Backend | Python and FastAPI |
| Web client | Next.js |

## Prerequisites

- Python 3.10 or newer
- [Bun](https://bun.sh/)
- [Agora CLI](https://github.com/AgoraIO/cli)
- An Agora project with an App ID and App Certificate
- An OpenAI API key with GPT Live access

## Run the recipe

Clone the repository and install its dependencies:

```bash
git clone git@github.com:AgoraIO-Community/OpenAI-Agora-Voice-Agents-Python.git
cd OpenAI-Agora-Voice-Agents-Python
bun run setup
```

Use the Agora CLI to select a project and write its credentials to `server/.env.local`:

```bash
agora login
agora project use <your-project-name-or-id>
agora project env write server/.env.local --template standard
```

Add your OpenAI key to `server/.env.local`:

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

Start the FastAPI backend and Next.js client:

```bash
bun run dev
```

Open [http://localhost:3000](http://localhost:3000), allow microphone access, and select **Start conversation**.

## Configure GPT Live

The backend creates the MLLM and starts a session with the browser's channel and UID:

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

    agent = Agent(
        client=client,
        advanced_features={"enable_rtm": True, "enable_tools": False},
        parameters={
            "audio_scenario": "chorus",
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        },
    ).with_mllm(
        OpenAIGPTLive(
            api_key=os.environ["OPENAI_API_KEY"],
            model="gpt-live-1",
            voice="cedar",
            prompt="You are a concise and helpful voice assistant.",
            greeting="Hello! How can I help?",
            messages=[
                {"role": "user", "content": "My name is Arlene."},
                {"role": "assistant", "content": "Nice to meet you, Arlene."},
            ],
        )
    )

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

The complete sample generates an RTC+RTM token before starting the agent. The browser and agent join the same channel with different UIDs, and `remote_uids` identifies the browser user whose audio the agent should process.

## Customize the conversation

| Python option | Request field | Purpose |
| --- | --- | --- |
| `prompt` | `mllm.params.prompt` | Persistent system instructions |
| `greeting` | `mllm.greeting_message` | Requested opening line |
| `messages` | `mllm.messages` | Prior user and assistant turns |
| `voice` | `mllm.params.voice` | Output voice |

Use `prompt` for system behavior and `messages` to continue an earlier conversation. Keep credentials and conversation history on the server.

## Stop the agent

Retain the session returned by `start_agent` and stop it when the call ends:

```python
await session.stop()
```

For a multi-worker deployment, store lifecycle ownership in shared state or route start and stop requests to the same worker.

## Verify the project

```bash
bun run verify:backend
bun run verify:web
```

See the [project README](../../README.md) for architecture, deployment, configuration options, and troubleshooting.
