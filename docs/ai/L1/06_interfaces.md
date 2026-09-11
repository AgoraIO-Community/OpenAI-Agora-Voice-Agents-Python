# 06 Interfaces

> Boundary contracts: FastAPI routes, Next rewrites, environment variables, and managed agent payload.

## Python Backend Routes

`server/src/server.py` registers these on an `APIRouter`:

| Path           | Method | Request                                                                              | Success (200)                                                                                | Errors                                                          |
| -------------- | ------ | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `/get_config`  | GET    | Query: optional `channel`, optional `uid`                                            | `{ "code": 0, "msg": "success", "data": { app_id, token, uid, channel_name, agent_uid } }`   | `500` if `agent is None`; exceptions via `_to_http_error`        |
| `/startAgent`  | POST   | JSON `StartAgentRequest`: `channelName`, `rtcUid`, `userUid`, optional `parameters`  | `{ "code": 0, "msg": "success", "data": { agent_id, channel_name, status } }`                | `400` validation (`ValueError`); `500` runtime / generic        |
| `/stopAgent`   | POST   | JSON `StopAgentRequest`: `agentId`                                                   | `{ "code": 0, "msg": "success" }`                                                            | Same shape                                                       |

CORS middleware: `allow_origins=["*"]`, `allow_credentials=True`.

`StartAgentRequest.parameters` is optional — the handler only reads `output_audio_codec` from it today.

`get_config` treats missing, zero, and negative UIDs as "generate a random user UID" and returns the generated value. This keeps the single RTC+RTM token usable for RTM, where `0` is not a valid login subject.

## Next.js Rewrites

`web/next.config.ts` registers these only when `AGENT_BACKEND_URL` is set:

| Source             | Destination                                  |
| ------------------ | -------------------------------------------- |
| `/api/get_config`  | `${AGENT_BACKEND_URL}/get_config`             |
| `/api/startAgent`  | `${AGENT_BACKEND_URL}/startAgent`             |
| `/api/stopAgent`   | `${AGENT_BACKEND_URL}/stopAgent`              |

`verify-api-contracts.ts` asserts that no `web/app/api/**/route.ts` files exist. Adding one would create a competing handler in front of the rewrite — don't.

## Environment Variables

| Scope                  | Variable                                  |
| ---------------------- | ----------------------------------------- |
| Python server (required) | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE` |
| Python server (optional) | `AGENT_GREETING`, `AGENT_INSTRUCTIONS`, `AGENT_PRIOR_MESSAGES`, `PORT` |
| Next build             | `AGENT_BACKEND_URL`                       |
| Browser                | `NEXT_PUBLIC_AGENT_UID` (optional)        |

`AGENT_BACKEND_URL` is a Next **server**-time env var (used inside `next.config.ts`), not a `NEXT_PUBLIC_*` value — do not prefix it.

## Token Shape

`get_config` returns:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "app_id": "string",
    "token": "string",          // built by generate_convo_ai_token, token_expire=3600
    "uid": "string",            // serialized number
    "channel_name": "string",
    "agent_uid": "string"
  }
}
```

The same token grants RTC and RTM privileges.

## Managed Agent Payload

`server/src/agent.py` does not POST a hand-written JSON payload to Agora — it uses the SDK builder chain:

```python
agent = (
    AgoraAgent(...)
    .with_mllm(OpenAIGPTLive(
        api_key=os.environ["OPENAI_API_KEY"],
        greeting=self.greeting,
    ))
)

session = agora_agent.create_async_session(
    client=self.client,
    channel=channel_name,
    agent_uid=str(agent_uid),
    remote_uids=[str(user_uid)],
    enable_string_uid=False,
    idle_timeout=30,
    expires_in=3600,
)
agent_id = await session.start()
```

## RTM Event Shapes (Client-Side)

`AgoraVoiceAI` emits the same toolkit events as the other quickstarts:

- `TRANSCRIPT_UPDATED` — `{ uid, text, status, timestamp }[]`
- `AGENT_STATE_CHANGED` — `AgentState`
- `AGENT_METRICS` — `{ type, name, value, timestamp }`
- `MESSAGE_ERROR` — `{ module, code, message, send_ts }`
- `MESSAGE_SAL_STATUS` — `{ status, timestamp }`
- `AGENT_ERROR` — SDK error info

`ConversationComponent.tsx` also attaches a raw RTM `message` listener as a fallback for the same `message.error` / `message.sal_status` payloads.

## Internal Types

| Type                          | Lives in                                       | Notes                                            |
| ----------------------------- | ---------------------------------------------- | ------------------------------------------------ |
| `StartAgentRequest`           | `server/src/server.py`                         | pydantic, camelCase fields                       |
| `StopAgentRequest`            | `server/src/server.py`                         | pydantic, `agentId`                              |
| `AgoraTokenData`              | `web/src/types/conversation.ts`                | Used by `LandingPage` + `ConversationComponent`  |
| `AgoraRenewalTokens`          | `web/src/types/conversation.ts`                | Renewal handler payload                          |
| `ConversationComponentProps`  | `web/src/types/conversation.ts`                | Includes RTM client + data                       |
| `GetConfigResponse`           | `web/src/services/api.ts`                      | Browser shape for `data` field                   |

## Related Deep Dives

- [Managed Agent Config](L2/managed_agent_config.md) — Detailed field reference.
- [Verification Scripts](L2/verification_scripts.md) — How the contracts above are enforced by local pre-ship checks.

### GPT Live v3 model contract

The application sets `params.model: gpt-live-1-diamond-alpha`, `params.voice: cedar`, and `params.prompt` from `AGENT_INSTRUCTIONS`. Without an override, the prompt and greeting use the built-in Ada developer advocate persona. The SDK supplies `/v1/live/sessions` and its protocol selector default. Browser API contracts are unchanged.

`AGENT_PRIOR_MESSAGES` is parsed as a JSON array of user/assistant text turns and sent as `mllm.messages`. It is independent of `AGENT_INSTRUCTIONS`; invalid history prevents backend startup.
