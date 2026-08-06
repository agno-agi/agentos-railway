"""
AgentOS Registry
================

The tools, functions, models, databases, and agents available to AgentOS Studio.
"""

import json
import re
from os import getenv

from agno.fs import FileSystem
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.tools.file_generation import FileGenerationTools
from agno.tools.mcp import MCPTools
from agno.tools.openai import OpenAITools
from agno.tools.parallel import ParallelTools
from agno.tools.slack import SlackTools
from agno.tools.user_feedback import UserFeedbackTools
from agno.workflow import StepInput

from agents.platform_manager import platform_manager
from app.settings import default_model
from db import get_postgres_db

AGNO_DOCS_MCP_URL = "https://docs.agno.com/mcp"


def get_agno_docs_tools() -> list[MCPTools]:
    return [MCPTools(transport="streamable-http", url=AGNO_DOCS_MCP_URL, name="agno_docs")]


def get_parallel_tools() -> list[ParallelTools | MCPTools]:
    if getenv("PARALLEL_API_KEY"):
        return [ParallelTools()]
    # timeout_seconds: web_fetch page extraction regularly exceeds the 10s MCP default.
    return [
        MCPTools(
            url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
        )
    ]


def get_agent_files_tools() -> list:
    """Private file system for any agent: the templated namespace resolves to the
    calling agent's id, so every agent that uses this toolkit gets its own isolated store (20MB quota)
    """
    fs = FileSystem(get_postgres_db(), namespace="{agent_id}")
    # add_instructions injects the toolkit's own usage guidance into the wielding
    # agent's system message — built agents have no other channel for it.
    return [fs.tools(add_instructions=True, name="agent_files")]


def get_slack_tools() -> list[SlackTools]:
    """Send-scoped Slack toolkit, only when the Slack interface is configured.

    Deliberately narrower than the SlackTools defaults: a registry any agent
    can draw from gets post + channel listing, never history reads or file transfer.
    """
    if not getenv("SLACK_BOT_TOKEN"):
        return []
    return [
        SlackTools(
            token=getenv("SLACK_BOT_TOKEN"),
            enable_send_message=True,
            enable_send_message_thread=True,
            enable_list_channels=True,
            enable_get_channel_history=False,
            enable_upload_file=False,
            enable_download_file=False,
        )
    ]


def get_media_tools() -> list[OpenAITools]:
    """Image generation and text-to-speech on the platform's existing OpenAI key.

    Generated media come back as run artifacts (bytes on the RunResponse), so they
    persist in Postgres and survive ephemeral container filesystems. Transcription
    stays off: transcribe_audio reads server-local file paths, which agents on this
    platform never have. The toolkit's default image model is the deprecated
    dall-e-3; gpt-image-2 is current.
    """
    # OpenAITools raises without the key; the registry import must not.
    if not getenv("OPENAI_API_KEY"):
        return []
    return [OpenAITools(enable_transcription=False, image_model="gpt-image-2")]


def get_file_generation_tools() -> list[FileGenerationTools]:
    """Downloadable files (JSON, CSV, TXT, HTML, code) as in-memory run artifacts.

    PDF and DOCX stay off until their optional deps are pinned — flip the flags
    after adding reportlab / python-docx to pyproject.toml.
    """
    return [FileGenerationTools(enable_pdf_generation=False, enable_docx_generation=False)]


# Workflow step executors are always called as func(step_input) with a StepInput —
# there is no string adapter, so every registry function takes the whole StepInput.
def _step_text(step_input: StepInput) -> str:
    """The text a function step operates on: the previous step's output, else the workflow input."""
    if step_input.previous_step_content is not None:
        return str(step_input.previous_step_content)
    return step_input.get_input_as_string() or ""


def route_component_type(step_input: StepInput) -> str:
    """Suggest agent, team, or workflow for the request in the previous step's output (or the workflow input)."""
    lower = _step_text(step_input).lower()
    if any(word in lower for word in ("daily", "schedule", "pipeline", "approval", "steps", "workflow")):
        return "workflow"
    if any(word in lower for word in ("team", "specialists", "debate", "reviewers", "coordinate")):
        return "team"
    return "agent"


def score_eval_status(step_input: StepInput) -> str:
    """PASS when the eval report in the previous step's output shows every case passed, FAIL otherwise.

    Reads JSON `passed`/`total` keys, or an `N/M passed` line like the run-evals report emits.
    """
    text = _step_text(step_input)
    passed = total = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and isinstance(data.get("passed"), int) and isinstance(data.get("total"), int):
        passed, total = data["passed"], data["total"]
    else:
        match = re.search(r"(\d+)\s*/\s*(\d+)\s*passed", text)
        if match:
            passed, total = int(match.group(1)), int(match.group(2))
    if passed is None or total is None or total <= 0:
        return "FAIL"
    return "PASS" if passed == total else "FAIL"


registry = Registry(
    name="AgentOS Registry",
    tools=[
        *get_agno_docs_tools(),
        *get_parallel_tools(),
        *get_agent_files_tools(),
        *get_slack_tools(),
        *get_media_tools(),
        *get_file_generation_tools(),
        # Structured ask-the-user questions: pauses the run, resumes via the
        # same HITL surfaces as Agent Builder's delete gate.
        UserFeedbackTools(),
        CalculatorTools(),
    ],
    models=[default_model()],
    dbs=[get_postgres_db()],
    functions=[route_component_type, score_eval_status],
    agents=[platform_manager],
)
