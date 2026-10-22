"""
AgentOS Registry
================
"""

from os import getenv

from agno.fs import FileSystem
from agno.learn import LearningMachine, LearningMode, UserMemoryConfig, UserProfileConfig
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.tools.file import FileGenerationTools
from agno.tools.mcp import MCPTools
from agno.tools.parallel import ParallelTools
from agno.workflow.functions import content_to_file, csv_to_markdown_table, extract_json, extract_urls, json_to_csv

from app.settings import default_model
from db import create_knowledge, get_postgres_db


def get_web_tools() -> list[ParallelTools | MCPTools]:
    if getenv("PARALLEL_API_KEY"):
        return [ParallelTools()]
    return [
        MCPTools(
            url="https://search.parallel.ai/mcp",
            transport="streamable-http",
            name="parallel_tools",
            timeout_seconds=30,
        )
    ]


shared_knowledge = create_knowledge(name="shared-knowledge", table_name="shared_knowledge")

shared_learning = LearningMachine(
    db=get_postgres_db(),
    name="shared-learning",
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
)

shared_notes = FileSystem(
    db=get_postgres_db(),
    namespace="shared-notes",
)

registry = Registry(
    name="AgentOS Registry",
    tools=[
        *get_web_tools(),
        shared_notes.tools(add_instructions=True),
        FileGenerationTools(enable_pdf_generation=False, enable_docx_generation=False),
        CalculatorTools(),
    ],
    models=[default_model()],
    functions=[
        extract_json,
        extract_urls,
        json_to_csv,
        csv_to_markdown_table,
        content_to_file,
    ],
    dbs=[get_postgres_db()],
    learning=[shared_learning],
    knowledge=[shared_knowledge],
)
