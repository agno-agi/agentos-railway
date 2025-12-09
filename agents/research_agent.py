from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.parallel import ParallelTools

from db.demo_db import demo_db

# ============================================================================
# Description & Instructions
# ============================================================================
instructions = dedent("""\
    You are a Research Agent that helps users explore new topics.
    You can use the ParallelTools to search for up-to-date information.

    Instructions:
    1. Understand the user's query and identify the main research goal.
    2. Use ParallelTools to run 1-3 targeted searches for relevant, recent information.
    3. Summarize and synthesize findings in a clear, conversational tone — avoid unnecessary jargon.
    4. Always prioritize credible sources and mention or link to them when appropriate.
    5. If the answer is already known or can be reasoned directly, respond concisely without searching.
    """)

# ============================================================================
# Create the Agent
# ============================================================================
research_agent = Agent(
    name="Research Agent",
    role="Assist with research and information synthesis",
    model=OpenAIChat(id="gpt-5-mini"),
    tools=[ParallelTools(enable_search=True, enable_extract=True)],
    instructions=instructions,
    add_history_to_context=True,
    add_datetime_to_context=True,
    enable_agentic_memory=True,
    markdown=True,
    db=demo_db,
)
