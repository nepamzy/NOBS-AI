"""NOBS AI assistant chat.

Two modes, chosen by the caller (the /chat router) based on who's asking:

- **Guest mode** (every non-admin user): narrow on purpose — CLAUDE.md
  Part 2 marks a general-purpose assistant chat as out of scope for V1.
  Guests only get NOBS_TOOLS (direct their own videos) and
  NOBS_SYSTEM_PROMPT, not web search or open-ended conversation.
- **Admin mode** (Nobert only, per his explicit instruction): broader —
  general research (with real web search, not just training-data recall),
  coding help, and security guidance, in addition to everything guest mode
  can do. Still not a payment-connected or multi-user feature; it's an
  admin-only capability layer on the same chat.

This file never touches the database. Every NOBS_TOOLS entry is a plain
Python callable the router provides, already bound to the signed-in user —
wired to the exact same functions the regular REST endpoints call, so
chat enforces the same ownership/token-balance checks as everything else.
Nothing here grants a capability a normal authenticated request couldn't
already do; web search is the one genuinely new (and separately billed —
$0.01/search plus normal input tokens for results, see CLAUDE.md chat
history) capability admin mode adds.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError

_MAX_TOOL_ROUNDS = 6  # safety cap against a runaway tool-call loop
_MAX_OUTPUT_TOKENS = 2048

NOBS_SYSTEM_PROMPT = (
    "You are the NOBS AI assistant. You help the signed-in user create and "
    "manage their YouTube videos through this conversation. You can list "
    "their projects/videos, check a video's pipeline status, create a new "
    "video, view a video's script, regenerate a single scene, and approve "
    "a storyboard. Only ever act on the current user's own data — every "
    "tool is already scoped to them, you don't need to ask whose data it "
    "is. Be concise. If a tool call comes back describing something that "
    "needs approval or setup (e.g. no tokens left, or a paid engine isn't "
    "configured), explain that plainly to the user rather than retrying."
)

ADMIN_SYSTEM_PROMPT_ADDENDUM = (
    "\n\nYou are talking to Nobert, the product's admin — beyond directing "
    "NOBS AI itself, he also wants you as a general assistant: deep "
    "research on any topic (use the web_search tool for anything "
    "time-sensitive or where accuracy matters — don't rely on memory "
    "alone for facts, prices, or current events), coding help and "
    "teaching across any language or framework, and practical "
    "cybersecurity guidance (recognizing phishing/scams, account "
    "hardening, safe practices) — defensive advice only, never help "
    "attacking or compromising a system that isn't his own. If he shares "
    "an image or PDF, analyze it directly and answer his question about "
    "it. You cannot yet accept video files — only images and PDFs."
)

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}

NOBS_TOOLS = [
    {
        "name": "list_projects",
        "description": "List the current user's projects.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "list_videos",
        "description": "List the current user's videos, optionally filtered to one project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Optional project UUID"}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_video",
        "description": "Get a single video's current pipeline stage/status.",
        "input_schema": {
            "type": "object",
            "properties": {"video_id": {"type": "string"}},
            "required": ["video_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_video",
        "description": "Start creating a new video in a project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "topic": {"type": "string"},
                "target_duration_seconds": {"type": "integer"},
                "voice_preset": {"type": "string"},
                "style_preset": {"type": "string"},
                "run_research": {"type": "boolean"},
            },
            "required": ["project_id", "topic", "target_duration_seconds"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_video_script",
        "description": "Get a video's generated script and scenes.",
        "input_schema": {
            "type": "object",
            "properties": {"video_id": {"type": "string"}},
            "required": ["video_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "regenerate_scene",
        "description": (
            "Regenerate one scene's narration/visual prompt. Only works "
            "before the storyboard is approved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "video_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "instructions": {"type": "string", "description": "Optional guidance"},
            },
            "required": ["video_id", "scene_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "approve_storyboard",
        "description": "Approve a video's storyboard so generation can proceed.",
        "input_schema": {
            "type": "object",
            "properties": {"video_id": {"type": "string"}},
            "required": ["video_id"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class ChatTurnResult:
    reply: str
    messages: list[dict]  # full updated conversation, incl. tool_use/tool_result blocks


def run_chat_turn(
    llm_provider: str,
    llm_api_key: str,
    llm_model: str,
    conversation: list[dict],
    tool_executor: Callable[[str, dict], object],
    system_prompt: str = NOBS_SYSTEM_PROMPT,
    tools: list[dict] | None = None,
) -> ChatTurnResult:
    if tools is None:
        tools = NOBS_TOOLS
    if not llm_provider or not llm_api_key:
        raise EngineNotConfiguredError(
            "No LLM_PROVIDER/LLM_API_KEY configured — the assistant needs "
            "the same LLM setup as script/research generation."
        )
    if llm_provider != "anthropic":
        raise EngineNotConfiguredError(
            f"LLM_PROVIDER={llm_provider!r} is not implemented — only "
            "'anthropic' is wired up so far."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=llm_api_key)
    messages = list(conversation)

    for _ in range(_MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=llm_model,
            max_tokens=_MAX_OUTPUT_TOKENS,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        content_blocks = [block.model_dump() for block in response.content]
        messages.append({"role": "assistant", "content": content_blocks})

        if response.stop_reason != "tool_use":
            reply = "".join(b["text"] for b in content_blocks if b["type"] == "text")
            return ChatTurnResult(reply=reply, messages=messages)

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                output = tool_executor(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(output, default=str),
                    }
                )
            except ApprovalRequiredError as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": exc.cost_warning.render(),
                        "is_error": True,
                    }
                )
            except Exception as exc:
                # Surfaced back to the model as a tool error, not raised —
                # a bad tool call (e.g. a video the user doesn't own) should
                # become a conversational explanation, not a crashed chat.
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return ChatTurnResult(
        reply=(
            "I've made several tool calls but haven't reached a final "
            "answer yet — try rephrasing or asking a narrower question."
        ),
        messages=messages,
    )
