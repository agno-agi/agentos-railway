"""
Knowledge
=========

Two PgVector knowledge bases, kept apart on purpose.

- shared-knowledge: the operators' base. Load documents through the AgentOS UI or
  the `/knowledge` API. Anything a platform agent should know goes here.
- product-knowledge: the product's docs, one row per page with its source URL.
  Filled by Platform Builder's ingestion toolkit (app/ingest.py) or by hand
  through the UI. An end-user-facing product agent reads this base and never
  the operators' one.
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
