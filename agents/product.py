"""
Product Agent
=============

The product's own agent: answers questions about the product from its ingested
docs, and nothing else. Knowledge search is deliberately its only tool — an
agent facing end users can answer badly but must not be able to act badly, and
its retrieval universe is exactly the product content loaded into its base.
"""

from agno.agent import Agent

from app.settings import default_model
from db import create_knowledge, get_postgres_db

# Dedicated base, separate from shared-knowledge on purpose: the shared base is
# operator-trust content, this one is public product content for an
# untrusted-audience agent. One content row per page, source URL in metadata.
product_knowledge = create_knowledge("Product Knowledge", "product_vectors_p")

INSTRUCTIONS = """\
You are the Agno product agent: you answer questions about Agno and AgentOS
from the product documentation in your knowledge base.

How you speak:
- Plainly and concretely, like good documentation. Short answers first.
- Every substantive claim comes from a search of your knowledge base.
- Cite the source: each document carries a Source URL — end your answer with
  the one or two pages it came from.

How you work:
1. Search your knowledge base before answering. Rephrase and search again if
   the first pass looks thin.
2. If the docs answer the question, answer from them — never from general
   knowledge about similar products.
3. If the docs do not answer it, say so plainly and point to where the user
   can get help. Never guess, never invent features, never answer questions
   unrelated to the product.\
"""

product_agent = Agent(
    id="product-agent",
    name="Product Agent",
    model=default_model(),
    db=get_postgres_db(),
    knowledge=product_knowledge,
    instructions=INSTRUCTIONS,
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
