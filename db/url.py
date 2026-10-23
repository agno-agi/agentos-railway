"""PostgreSQL connection configuration."""

from os import getenv

from sqlalchemy.engine import URL


def build_db_url() -> str:
    """Build database URL from environment variables."""
    return URL.create(
        drivername=getenv("DB_DRIVER", "postgresql+psycopg"),
        username=getenv("DB_USER", "ai"),
        password=getenv("DB_PASS", "ai"),
        host=getenv("DB_HOST", "localhost"),
        port=int(getenv("DB_PORT", "5432")),
        database=getenv("DB_DATABASE", "ai"),
    ).render_as_string(hide_password=False)


db_url = build_db_url()
