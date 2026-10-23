"""Shared PostgreSQL storage and knowledge creation."""

from functools import cache

from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.pgvector import PgVector, SearchType

from db.url import db_url

__all__ = ["create_knowledge", "db_url", "get_postgres_db"]

DB_ID = "agentos-db"


@cache
def get_postgres_db() -> PostgresDb:
    """Return the shared database for AgentOS and its components."""
    return PostgresDb(id=DB_ID, db_url=db_url)


def create_knowledge(name: str, table_name: str) -> Knowledge:
    """Create hybrid-search knowledge with its own content adapter."""
    contents_table = f"{table_name}_contents"
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=PostgresDb(
            id=f"{DB_ID}-{contents_table}",
            db_url=db_url,
            knowledge_table=contents_table,
        ),
    )
