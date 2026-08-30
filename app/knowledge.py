"""
Platform Knowledge
==================

Two PgVector knowledge bases available to the platform components:

- shared-knowledge: a shared knowledge base that can be used by any component.
  Load documents through the AgentOS UI or the `/knowledge` API.
- product-knowledge: a dedicated knowledge base for product agents.
"""

from agno.knowledge import Knowledge

from db import create_knowledge

KNOWLEDGE_NAME = "shared-knowledge"
PRODUCT_KNOWLEDGE_NAME = "product-knowledge"

shared_knowledge: Knowledge = create_knowledge(
    name=KNOWLEDGE_NAME,
    table_name="shared_knowledge",
)

product_knowledge: Knowledge = create_knowledge(
    name=PRODUCT_KNOWLEDGE_NAME,
    table_name="product_knowledge",
)
