"""
Agent

High-level API for managing Agora Conversational AI Agents.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from agora_agent import Area, AsyncAgora
from agora_agent.agentkit import Agent as AgoraAgent
from agora_agent import OpenAIGPTLive

logger = logging.getLogger("uvicorn.error")

DEFAULT_GREETING = "Hi there! I'm Ada, your virtual assistant from Agora. How can I help?"
DEFAULT_INSTRUCTIONS = """You are **Ada**, an agentic developer advocate from **Agora**. You help developers understand and build with Agora's Conversational AI platform.

# What Agora Actually Is
Agora is a real-time communications company. The product you represent is the **Agora Conversational AI Engine**. It lets developers add voice AI agents to apps over Agora's SD-RTN (Software Defined Real-Time Network). Key facts:
- The product is called the **Conversational AI Engine** (not "Chorus", not "Harmony", or any other name you might invent)
- It supports both cascaded and multimodal model pipelines
- A cascaded pipeline connects separate ASR, LLM, and TTS providers
- An MLLM pipeline uses a multimodal large language model that handles audio input, reasoning, and audio output as one end-to-end stage
- This demo uses OpenAI GPT Live as an MLLM, so GPT Live receives the caller's audio directly and returns spoken audio without separate ASR or TTS stages
- MLLM providers use the mllm configuration; prompt supplies persistent instructions, greeting_message supplies the opening line, and messages seeds prior conversation
- Enabling MLLM disables separate ASR, LLM, and TTS stages because the multimodal model owns the end-to-end voice path
- Agora supports MLLM integrations for OpenAI Realtime, Azure OpenAI Realtime, Google Gemini Live, Gemini Live on Vertex AI, and xAI Grok
- It supports Deepgram, Microsoft, and others for ASR; OpenAI, Anthropic, and others for LLM; ElevenLabs, Microsoft, and others for TTS
- Agora's SD-RTN is its global real-time network infrastructure — not "SDRTN"
- MCP in this context means **Model Context Protocol** (Anthropic's open standard for connecting AI models to tools/data), not "multi-channel processing"
- Agora does not have a product called Chorus, Harmony, or any similar name — do not invent product names

# What You Are Running
- You are an MLLM voice agent powered by OpenAI GPT Live through Agora's Conversational AI Engine
- Your Agora MLLM vendor is openai_gpt_live, your model is gpt-live-1, and your configured voice is Cedar
- The caller's RTC audio travels through Agora to GPT Live; GPT Live understands the audio and produces spoken audio directly; Agora returns that audio to the caller
- You do not use a separate speech recognizer, text-only language model, or text-to-speech provider for your replies
- Your prompt defines your persistent behavior, your greeting is the opening line requested when the session starts, and messages can seed prior user and assistant turns
- This app enables RTM so the browser can receive transcript, agent state, metric, and error events alongside the RTC audio conversation
- If asked how you work, describe this MLLM path accurately and do not claim that you run a cascaded ASR, LLM, and TTS pipeline

# Honesty Rule
If you don't know a specific fact about Agora, say so plainly and suggest checking docs.agora.io. Never invent product names, feature names, or capabilities.

# Persona & Tone
- Friendly, technically credible, concise. You're a peer who builds things, not a support agent.
- Plain English. No marketing fluff.

# Core Behavior Guidelines
- **Default to brief**: This is a voice conversation. Keep most replies to 1–2 sentences. Only go longer if the user explicitly asks for detail or the answer genuinely requires it.
- **Never list or enumerate**: No bullet points, no numbered steps. Say the single most important thing.
- **Clarify before answering**: For anything complex, ask one focused question first.
- **Ask at most one question per turn**: Never stack questions.
- **Guide, don't lecture**: Unlock the next step, not everything at once."""


def _read_prior_messages(raw: Optional[str]) -> List[Dict[str, str]]:
    """Parse optional user/assistant history for GPT Live session input."""
    if raw is None or not raw.strip():
        return []
    error = (
        "AGENT_PRIOR_MESSAGES must be a JSON array of user/assistant messages "
        "with string content"
    )
    try:
        messages = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(error) from exc
    if not isinstance(messages, list):
        raise ValueError(error)
    parsed: List[Dict[str, str]] = []
    for message in messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
        ):
            raise ValueError(error)
        parsed.append({"role": message["role"], "content": message["content"]})
    return parsed


class Agent:
    """
    High-level wrapper for Agora Conversational AI Agent operations.

    Uses AgentSession for full lifecycle management (start/stop),
    which handles Token007 authentication automatically.
    """

    def __init__(self):
        self.app_id = os.getenv("AGORA_APP_ID")
        self.app_certificate = os.getenv("AGORA_APP_CERTIFICATE")
        self.greeting = os.getenv(
            "AGENT_GREETING",
            DEFAULT_GREETING,
        )
        self.instructions = os.getenv(
            "AGENT_INSTRUCTIONS",
            DEFAULT_INSTRUCTIONS,
        )
        self.prior_messages = _read_prior_messages(os.getenv("AGENT_PRIOR_MESSAGES"))
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.app_id or not self.app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE are required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI GPT Live")

        self.client = AsyncAgora(
            area=Area.US,
            app_id=self.app_id,
            app_certificate=self.app_certificate,
        )

        # Track active sessions by agent_id
        self._sessions: Dict[str, Any] = {}

    async def start(
        self,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start an end-to-end OpenAI GPT Live MLLM agent."""
        if not channel_name or not str(channel_name).strip():
            raise ValueError("channel_name is required and cannot be empty")
        if agent_uid <= 0:
            raise ValueError("agent_uid is required and cannot be empty")
        if user_uid <= 0:
            raise ValueError("user_uid is required and cannot be empty")

        mllm = OpenAIGPTLive(
            api_key=self.openai_api_key,
            greeting=self.greeting,
            model="gpt-live-1",
            voice="cedar",
            prompt=self.instructions,
            messages=self.prior_messages,
        )

        parameters = {
            "audio_scenario": "chorus",  # web client → ultra-low-latency chorus profile
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if isinstance(output_audio_codec, str) and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        agora_agent = AgoraAgent(
            client=self.client,
            advanced_features={"enable_rtm": True, "enable_tools": False},
            parameters=parameters,
        )
        agora_agent = agora_agent.with_mllm(mllm)

        session = agora_agent.create_async_session(
            channel=channel_name,
            agent_uid=str(agent_uid),
            remote_uids=[str(user_uid)],
            enable_string_uid=False,
            idle_timeout=30,
            expires_in=3600,
            debug=True,
        )

        logger.info(
            "Starting Agora agent channel=%s agent_uid=%s user_uid=%s",
            channel_name,
            agent_uid,
            user_uid,
        )

        try:
            agent_id = await session.start()
        except Exception:
            logger.exception(
                "Failed to start Agora agent channel=%s agent_uid=%s user_uid=%s",
                channel_name,
                agent_uid,
                user_uid,
            )
            raise

        # Save session for later stop
        self._sessions[agent_id] = session

        logger.info(
            "Started Agora agent agent_id=%s channel=%s agent_uid=%s user_uid=%s",
            agent_id,
            channel_name,
            agent_uid,
            user_uid,
        )

        return {
            "agent_id": agent_id,
            "channel_name": channel_name,
            "status": "started",
        }

    async def stop(self, agent_id: str) -> None:
        """Stop a retained running session; unknown IDs are idempotent."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")

        session = self._sessions.pop(agent_id, None)
        if session is None:
            logger.info("Agora agent session not found agent_id=%s", agent_id)
            return

        await session.stop()
        logger.info("Stopped Agora agent from active session agent_id=%s", agent_id)
