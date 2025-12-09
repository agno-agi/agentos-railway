# ============================================================================
# Configure database for storing sessions, memories, metrics, evals and knowledge
# ============================================================================
from agno.db.postgres import PostgresDb

from db.url import get_db_url

# ************* Create database *************
db_url = get_db_url()
demo_db = PostgresDb(id="demo-db", db_url=db_url)
