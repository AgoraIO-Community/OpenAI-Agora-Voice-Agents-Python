# OpenAI GPT Live with Agora and Python

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Agora Agents](https://img.shields.io/badge/agora--agents-2.8.1-099DFD)](https://pypi.org/project/agora-agents/2.8.1/)

Build a browser-based voice agent with OpenAI GPT Live and the Agora Conversational AI Engine. A FastAPI backend starts and stops the agent, while a Next.js client handles microphone audio, playback, live transcripts, state, and latency metrics.

The sample uses the published `agora-agents` 2.8.1 package and configures GPT Live as one end-to-end multimodal stage.

## Prerequisites

- Python 3.10 or newer
- [Bun](https://bun.sh/)
- An Agora project with App ID and App Certificate
- An OpenAI API key with access to `gpt-live-1`

## Run locally

Install dependencies and create `server/.env.local`:

```bash
bun run setup
```

Install the [Agora CLI](https://github.com/AgoraIO/cli), sign in, select your Agora project, and write its App ID and App Certificate to the environment file:

```bash
curl -fsSL https://raw.githubusercontent.com/AgoraIO/cli/main/install.sh | sh -s -- --add-to-path
agora login
agora project use <your-project-name-or-id>
agora project env write server/.env.local --template standard
```

The CLI configures `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE`. Add your OpenAI key to `server/.env.local`:

```dotenv
OPENAI_API_KEY=your_openai_api_key
PORT=8000
```

If you prefer to configure the file manually, also set `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE` in `server/.env.local`.

Start the backend and web client:

```bash
bun run dev
```

Open [http://localhost:3000](http://localhost:3000), allow microphone access, and select **Start conversation**. Ada will greet you after the agent joins the channel.

Local services:

| Service | URL |
| --- | --- |
| Next.js client | `http://localhost:3000` |
| FastAPI backend | `http://localhost:8000` |
| FastAPI API docs | `http://localhost:8000/docs` |

## Configure the agent

The backend reads these optional values from `server/.env.local`:

| Variable | Purpose |
| --- | --- |
| `AGENT_GREETING` | Changes the first line the agent speaks. |
| `AGENT_INSTRUCTIONS` | Replaces the built-in Ada system prompt. |
| `AGENT_PRIOR_MESSAGES` | Seeds prior user and assistant turns as a JSON array. |

Example conversation history:

```dotenv
AGENT_PRIOR_MESSAGES='[{"role":"user","content":"I am planning a trip to Kyoto."},{"role":"assistant","content":"How many days will you be staying?"}]'
```

The backend sends instructions through `mllm.params.prompt` and sends conversation history through `mllm.messages`. Keep credentials and user history on the server.

See the [GPT Live recipe card](./docs/ai/RECIPE.md) for the SDK configuration and the fields used by this sample.

## How it works

1. The browser requests a channel, user ID, agent ID, and RTC+RTM token from FastAPI.
2. The browser joins the Agora channel and publishes microphone audio.
3. FastAPI creates an `OpenAIGPTLive` agent session for the same channel.
4. Agora carries audio between the browser and GPT Live. RTM carries transcripts, state changes, metrics, and errors.
5. The browser ends the call and FastAPI stops the retained agent session.

The backend keeps active sessions in process memory. Use shared storage or request affinity before running more than one backend instance.

## Project layout

| Path | Purpose |
| --- | --- |
| `server/src/agent.py` | GPT Live configuration and agent lifecycle |
| `server/src/server.py` | FastAPI routes and token generation |
| `web/` | Next.js conversation client |
| `docs/ai/RECIPE.md` | Copyable GPT Live SDK recipe |
| `ARCHITECTURE.md` | Full request and media flow |

## Verify changes

```bash
bun run verify:backend
bun run verify:web
```

Run the complete local integration checks when you change the backend or proxy boundary:

```bash
bun run verify:local
```

## Deploy

Deploy `server` as a reachable Python service and `web` as a Next.js app. Set the three credentials on the backend. Set this value on the web deployment:

```dotenv
AGENT_BACKEND_URL=https://your-python-backend.example.com
```

The Next.js client proxies its `/api/*` requests to that backend URL.

## Troubleshooting

- **The agent does not join:** confirm that the Agora project has Conversational AI enabled and that the OpenAI key can use the configured GPT Live model.
- **The backend rejects the request:** check `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, and `OPENAI_API_KEY` in `server/.env.local`.
- **The browser receives no transcript or state events:** confirm that the browser and agent use the same channel and that RTM is not blocked by the network.
- **The web client cannot reach FastAPI:** confirm that port 8000 is available and that the frontend uses `AGENT_BACKEND_URL=http://localhost:8000`.

If you use the Agora CLI, `agora project doctor --deep` checks project binding, credentials, feature access, and network reachability.

## Security

Keep the Agora App Certificate and OpenAI API key on the backend. Do not expose either value through browser code or a `NEXT_PUBLIC_*` variable.

## License

Released under the [MIT License](./LICENSE).
