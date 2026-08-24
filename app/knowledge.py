"""
Shared Knowledge
==================

A PgVector knowledge base used by the platform's components.
Load documents using the AgentOS UI or the `/knowledge` API endpoints.
"""

from agno.knowledge import Knowledge

from db import create_knowledge

KNOWLEDGE_NAME = "shared-knowledge"

shared_knowledge: Knowledge = create_knowledge(
    name=KNOWLEDGE_NAME,
    table_name="shared_knowledge",
)
