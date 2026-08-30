"""
AgentOS Registry
================

The tools, functions, models, databases, and agents available to AgentOS Studio.
"""

from agno.registry import Registry
from agno.tools.calculator import CalculatorTools

from agents.manager import platform_manager
from app.functions import (
    content_to_file,
    csv_to_markdown_table,
    extract_json,
    extract_urls,
    json_to_csv,
)
from app.knowledge import product_knowledge, shared_knowledge
from app.learning import shared_learning
from app.notes import get_shared_notes_tools
from app.settings import default_model
from app.tools import (
    get_agno_docs_tools,
    get_file_generation_tools,
    get_media_tools,
    get_parallel_tools,
    get_slack_tools,
)
from db import get_postgres_db

registry = Registry(
    name="AgentOS Registry",
    tools=[
        *get_agno_docs_tools(),
        *get_parallel_tools(),
        *get_shared_notes_tools(),
        *get_slack_tools(),
        *get_media_tools(),
        *get_file_generation_tools(),
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
    knowledge=[shared_knowledge, product_knowledge],
    agents=[platform_manager],
)
