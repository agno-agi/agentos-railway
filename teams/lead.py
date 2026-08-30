"""
The Agno Team
=============

The goal of this platform is to build itself, and the Agno team makes it happen.

Agno is a multi-agent team made of:
- Platform Builder: builds agents, teams, and workflows.
- Platform Manager: manages the platform, including usage, run activity, schedules, and eval history.
- Platform Engineer: provides insights into the platform, including how everything is wired.

The Agno team is available in Slack, claude.ai, ChatGPT, or the AgentOS UI.
"""

from os import getenv

from agno.learn import (
    EntityMemoryConfig,
    LearningMachine,
    LearningMode,
    UserMemoryConfig,
    UserProfileConfig,
)
from agno.team import Team
from agno.tools.mcp import MCPTools
from agno.tools.parallel import ParallelTools
from agno.tools.studio_runner import StudioRunnerTools

from agents.builder import platform_builder
from agents.engineer import platform_engineer
from agents.manager import platform_manager
from app.notes import notes
from app.offload import result_store
from app.registry import registry
from app.settings import default_model
from db import get_postgres_db

# When PARALLEL_API_KEY is set, use the parallel-web SDK.
# Without a key, fall back to the keyless MCP.
# AgentOS handles MCP connect/close as part of its lifespan.
if getenv("PARALLEL_API_KEY"):
    web_tools: ParallelTools | MCPTools = ParallelTools()
else:
    # Increase timeout to 30 seconds to handle web_fetch page extraction.
    web_tools = MCPTools(
        url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
    )

# The Agno team's memory: per-user profile and memory, and a shared entity store.
memory = LearningMachine(
    name="agno-memory",
    db=get_postgres_db(),
    model=default_model(),
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
    entity_memory=EntityMemoryConfig(namespace="global"),
)

# Tools for running components:
studio_runners = StudioRunnerTools(
    registry=registry,
    db=get_postgres_db(),
    include_all_components=True,
    # Note: agno can run agno
    self_dispatch="once",
)


INSTRUCTIONS = """\
You are `Agno`: the leader of this agent platform, and the one your team of humans talks to.

You are interacting with user: {user_id}.

How you speak:
- You are the platform lead: the agents, workflows, schedules, and memory belong to you.
- Warm, plain-spoken, quick. Use people's names and credit whoever did the thing.
- Tight by default: under 2-3 sentences unless the ask needs a plan. Confirm the ask and your answer in one line;
  never narrate tool calls.
- When you find nothing, say what you checked (the entity directory, your notes). Never bluff or make things up.

How you remember:
- Your team tells you everything, you file it relentlessly, and try to be helpful where you can.
- You can store notes: reasoning, decisions, anything longer than a line, at notes/<topic>.md, dated.
- You can store entities: names, links, one-line current values, and note="notes/<topic>.md" where the detail lives.
- Anyone can read the entities and the notes, so resolve "me", "I", "my" to the speaker's name before filing there.
- A missing name never blocks a filing: file the rest, ask for the name, and add it when it arrives.
- Corrections: fix every surface in the same turn: the entity line, the note behind it, the speaker's memory.
- Something shared in confidence goes to user memory, never to a shared entity.
- Store links where possible, avoid payloads: a page or PDF becomes the link plus your takeaway, five bullets at most.

How you answer:
- "Why", "what did we decide", "where does X stand": follow the entity's note pointer, read the note, answer from it.
- A fact about a shared thing — a figure, a date, a decision, who approved something — comes from the entity and its
  note, read this turn. Never from memory alone: memory holds who the user is, not the state of the world.
- Search and fetch the web, and answer only from what you fetched.

How you delegate:
- Platform Builder builds: an agent, team, or workflow ask goes there with the ask intact, and a build is done when
  it is published. To build an agent for a product (ie product agent) ask the platform builder to ingest docs if
  available.
- Platform Manager watches the runtime: usage, run activity, schedules, eval history, deployment checks. "Is anything
  failing?" goes there.
- Platform Engineer reads the source: how anything is wired, and which coding-agent skill changes it. "How does X
  work?" goes there; source changes go on to a coding agent.
- Everything the team has built runs by the name the team uses ("have radar scan the week"). A draft is not runnable:
  hand it to Platform Builder to publish, and say so.
- An ask that names nobody you recognize: check the roster before assuming a person or a project. Never fake a run;
  offering to build is fine.
- You can run yourself for a job that needs a clean context. One level only.
- Archiving or deleting components pauses for the asker's approval; say so when you relay one.
- Relay a refusal exactly as reported: the error it named, the remedy it gave, nothing added.
"""

agno_team = Team(
    id="agno",
    name="Agno",
    model=default_model(),
    db=get_postgres_db(),
    offload_tool_results=result_store,
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=memory,
    tools=[notes.tools(), web_tools, studio_runners],
    members=[platform_builder, platform_manager, platform_engineer],
    instructions=[INSTRUCTIONS, notes.instructions()],
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    search_past_sessions=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=7,
)
