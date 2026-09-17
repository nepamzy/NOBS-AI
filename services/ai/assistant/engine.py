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
from dataclasses import dataclass, field

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
    "alone for facts, prices, or current events), and real coding help — "
    "not just talk: use the code_execution tool to actually write and run "
    "code, test it, and iterate, the same way you would in a real "
    "development session. You can also generate a real PDF file when "
    "asked (write it with code_execution — pick whatever library is "
    "available or install one — the file comes back as a download link). "
    "Also give practical cybersecurity guidance (recognizing phishing/ "
    "scams, account hardening, safe practices) — defensive advice only, "
    "never help attacking or compromising a system that isn't his own. If "
    "he shares an image or PDF, analyze it directly and answer his "
    "question about it. You cannot yet accept video files — only images "
    "and PDFs.\n\n"
    "You DO have real, live access to three of his accounts, each scoped "
    "to exactly one thing and each deliberately missing its most "
    "dangerous capability:\n"
    "- GitHub: read files and write them, but ONLY on a new branch you "
    "create — you can never touch the default branch directly. Always "
    "finish a set of changes with github_create_pull_request so Nobert "
    "reviews and merges himself. You cannot merge, delete, or force-push.\n"
    "- Vercel: read deployments and env var names, and add/update env "
    "vars. You cannot trigger a deploy, delete anything, or touch domains.\n"
    "- Gmail: create drafts only, in his Drafts folder. You can NEVER "
    "send an email — say so plainly if asked to, rather than pretending.\n"
    "If any of these three tools comes back with a 'not configured' "
    "error, tell him plainly what's missing rather than retrying."
)

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
CODE_EXECUTION_TOOL = {"type": "code_execution_20260120", "name": "code_execution"}

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

# Admin-only. Each connector is hardcoded to exactly one repo/project/
# account server-side (see services/connectors/*/adapter.py) — none of
# these input schemas accept a repo/project/account to target, precisely
# so a bad or injected tool call can't redirect one at something Nobert
# didn't approve.
CONNECTOR_TOOLS = [
    {
        "name": "github_read_file",
        "description": "Read a file's contents from the configured GitHub repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "ref": {"type": "string", "description": "Branch/tag/sha, defaults to main"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "github_create_branch",
        "description": "Create a new branch to make changes on. Always do this before writing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch_name": {"type": "string"},
                "from_branch": {"type": "string", "description": "Defaults to main"},
            },
            "required": ["branch_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "github_write_file",
        "description": (
            "Create or update a file. Must target a branch created with "
            "github_create_branch, never the default branch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "message": {"type": "string", "description": "Commit message"},
                "branch": {"type": "string"},
            },
            "required": ["path", "content", "message", "branch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "github_create_pull_request",
        "description": (
            "Open a PR from your branch so Nobert can review and merge. "
            "This is the only way changes reach the default branch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "base": {"type": "string", "description": "Defaults to main"},
            },
            "required": ["branch", "title", "body"],
            "additionalProperties": False,
        },
    },
    {
        "name": "vercel_list_deployments",
        "description": "List recent deployments for the configured Vercel project.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "vercel_get_deployment",
        "description": "Get details/status for one deployment.",
        "input_schema": {
            "type": "object",
            "properties": {"deployment_id": {"type": "string"}},
            "required": ["deployment_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "vercel_list_env_vars",
        "description": "List environment variable names (not values) on the configured project.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "vercel_set_env_var",
        "description": (
            "Add or update one environment variable. Takes effect on the "
            "next deploy Nobert triggers — this never deploys."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
                "target": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["key", "value"],
            "additionalProperties": False,
        },
    },
    {
        "name": "gmail_create_draft",
        "description": (
            "Create a Gmail draft. NEVER sends — Nobert must open Gmail "
            "and send it himself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False,
        },
    },
]

MEMORY_TOOL = {
    "name": "remember",
    "description": (
        "Save a short, durable fact about Nobert or his preferences for "
        "future conversations (e.g. 'prefers Sonnet over Opus for cost', "
        "'building a YouTube automation tool called NOBS AI'). Call this "
        "whenever he tells you something worth remembering long-term — "
        "don't wait to be asked. Not for one-off task details."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"fact": {"type": "string"}},
        "required": ["fact"],
        "additionalProperties": False,
    },
}


@dataclass
class GeneratedFile:
    filename: str
    content: bytes
    media_type: str


@dataclass
class ChatTurnResult:
    reply: str
    messages: list[dict]  # full updated conversation, incl. tool_use/tool_result blocks
    generated_files: list[GeneratedFile] = field(default_factory=list)


def _extract_generated_files(client, response) -> list[GeneratedFile]:
    """Pulls out any file the code_execution tool wrote (e.g. a generated
    PDF) so the caller can store/serve it — Claude's own Files API only
    lets code-execution-created files be downloaded, not re-served
    directly to a browser, so we pull the bytes down once here."""
    import tempfile
    from pathlib import Path

    files = []
    for block in response.content:
        if block.type != "bash_code_execution_tool_result":
            continue
        result = block.content
        if getattr(result, "type", None) != "bash_code_execution_result":
            continue
        for file_ref in getattr(result, "content", None) or []:
            if file_ref.type != "bash_code_execution_output":
                continue
            metadata = client.files.retrieve_metadata(file_ref.file_id)
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / Path(metadata.filename).name
                client.files.download(file_ref.file_id).write_to_file(str(tmp_path))
                files.append(
                    GeneratedFile(
                        filename=Path(metadata.filename).name,
                        content=tmp_path.read_bytes(),
                        media_type=metadata.mime_type,
                    )
                )
    return files


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
    generated_files: list[GeneratedFile] = []

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
        generated_files.extend(_extract_generated_files(client, response))

        if response.stop_reason != "tool_use":
            reply = "".join(b["text"] for b in content_blocks if b["type"] == "text")
            return ChatTurnResult(reply=reply, messages=messages, generated_files=generated_files)

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
        generated_files=generated_files,
    )
