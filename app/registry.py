"""
AgentOS Registry
================

The tools, functions, models, databases, and agents available to AgentOS Studio.
"""

from os import getenv

from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.tools.file_generation import FileGenerationTools
from agno.tools.mcp import MCPTools
from agno.tools.openai import OpenAITools
from agno.tools.parallel import ParallelTools
from agno.tools.slack import SlackTools
from agno.tools.user_feedback import UserFeedbackTools

from agents.manager import platform_manager
from app.functions import (
    content_to_file,
    csv_to_markdown_table,
    extract_json,
    extract_urls,
    json_to_csv,
)
from app.knowledge import shared_knowledge
from app.learning import shared_learning
from app.notes import get_shared_notes_tools
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
    platform never have.
    """
    # OpenAITools raises without the key; the registry import must not.
    if not getenv("OPENAI_API_KEY"):
        return []
    return [OpenAITools(enable_transcription=False, image_model="gpt-image-2")]


def get_file_generation_tools() -> list[FileGenerationTools]:
    """Downloadable files (JSON, CSV, TXT, HTML, code) as in-memory run artifacts."""
    return [FileGenerationTools(enable_pdf_generation=False, enable_docx_generation=False)]


registry = Registry(
    name="AgentOS Registry",
    tools=[
        *get_agno_docs_tools(),
        *get_parallel_tools(),
        *get_shared_notes_tools(),
        *get_slack_tools(),
        *get_media_tools(),
        *get_file_generation_tools(),
        # Structured ask-the-user questions. A component carrying this pauses for a human, so it is a
        # poor schedule target -- build a separate, non-pausing agent for scheduled work.
        UserFeedbackTools(),
        CalculatorTools(),
    ],
    models=[default_model()],
    dbs=[get_postgres_db()],
    functions=[
        extract_json,
        extract_urls,
        json_to_csv,
        csv_to_markdown_table,
        content_to_file,
    ],
    learning=[shared_learning],
    knowledge=[shared_knowledge],
    agents=[platform_manager],
)
