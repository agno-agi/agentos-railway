"""
AgentOS Registry
================

The tools, functions, models, databases, and agents available to AgentOS Studio.
"""

from os import getenv

from agno.fs import FileSystem
from agno.registry import Registry
from agno.tools.mcp import MCPTools
from agno.tools.parallel import ParallelTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.slack import SlackTools

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
    """Private files for any built agent: the templated namespace resolves to the
    wielding agent's own id per call, so every agent that mounts this toolkit gets
    its own isolated store (own 20MB quota) — no agent can read another's files,
    and Chief's shared team notes stay a separate, deliberately gated surface."""
    fs = FileSystem(get_postgres_db(), namespace="{agent_id}")
    # Instructions passed explicitly: built agents have no other channel for the
    # toolkit's usage guidance (code agents compose fs.instructions() themselves).
    return [fs.tools(add_instructions=True, instructions=FileSystem.instructions(), name="agent_files")]


def get_slack_tools() -> list[SlackTools]:
    """Send-scoped Slack toolkit, only when the Slack interface is configured.

    Deliberately narrower than the SlackTools defaults: a registry any built agent
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


def route_component_type(request: str) -> str:
    """Suggest agent, team, or workflow from a plain-language request."""
    lower = request.lower()
    if any(word in lower for word in ("daily", "schedule", "pipeline", "approval", "steps", "workflow")):
        return "workflow"
    if any(word in lower for word in ("team", "specialists", "debate", "reviewers", "coordinate")):
        return "team"
    return "agent"


def score_eval_status(passed: int, total: int) -> str:
    """Return PASS only when every selected eval case passed."""
    if total <= 0:
        return "FAIL"
    return "PASS" if passed == total else "FAIL"


# Chief (a Team) is attached in app/main.py after construction — importing it here
# would cycle: chief's members include agent_builder, which imports this registry.
registry = Registry(
    name="AgentOS Registry",
    tools=[
        *get_agno_docs_tools(),
        *get_parallel_tools(),
        *get_agent_files_tools(),
        *get_slack_tools(),
        ReasoningTools(add_instructions=True),
    ],
    models=[default_model()],
    dbs=[get_postgres_db()],
    functions=[route_component_type, score_eval_status],
    agents=[platform_manager],
)
