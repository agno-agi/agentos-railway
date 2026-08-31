"""
Database Session
================

PostgreSQL connection helpers. Use:
- get_postgres_db() for agent storage backed by Postgres.
- create_knowledge() for agent knowledge backed by PgVector.
"""

from functools import cache

from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.pgvector import PgVector, SearchType

from db.url import db_url

DB_ID = "agentos-db"


@cache
def get_postgres_db(contents_table: str | None = None) -> PostgresDb:
    """Returns the shared PostgresDb instance for the AgentOS.

    Memoized so every agent/workflow/schedule reuses the same object
    instead of constructing a fresh PostgresDb on each call.

    Pass contents_table when this database is used as the contents_db of a Knowledge base.
    For plain agent persistence (sessions, memory), leave it unset.
    """
    if contents_table is not None:
        return PostgresDb(id=f"{DB_ID}-{contents_table}", db_url=db_url, knowledge_table=contents_table)
    return PostgresDb(id=DB_ID, db_url=db_url)


def create_knowledge(name: str, table_name: str) -> Knowledge:
    """Creates a PgVector knowledge base with hybrid search."""
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=get_postgres_db(contents_table=f"{table_name}_contents"),
    )
