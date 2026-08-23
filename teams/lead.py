"""
Agno
====

Agno is this platform speaking for itself, available in Slack, claude.ai,
ChatGPT, or the AgentOS UI: "Agno, we're going with planetscale over RDS",
"Agno, build me an agent for X", "Agno, have radar scan the week". Agno holds
the thread; everything else is a handoff — builds to Platform Builder, runtime
questions to Platform Manager, source questions to Platform Engineer, and
everything built at runtime through the Studio one runner call away.

Notes and entities are shared by the whole team; profile and memory are per-user.
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

# Agno holds the world as well as the self, so it composes its own machine: the same
# per-user pair app/learning.py declares (shared_learning), plus the shared entity store.
memory = LearningMachine(
    db=get_postgres_db(),
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),  # private to each user
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),  # private to each user
    entity_memory=EntityMemoryConfig(namespace="global"),  # shared by the team
)

# Dispatch for every component this platform can run, resolved at call time —
# a component published seconds ago is runnable on the next message.
# include_all_components admits the code-defined ones too: the framework discovers
# every OS-registered agent, team, and workflow into the live registry at boot, but
# dispatching them is opt-in. Without it Agno can only run what the Studio built, so
# an agent a coding agent added to app/main.py would be listed by the platform and
# unreachable through the one name people talk to.
studio_runners = StudioRunnerTools(
    registry=registry,
    db=get_postgres_db(),
    include_all_components=True,
    # ...except code-defined teams. Boot discovery puts every OS-registered component
    # in the registry, this team included, and the runner has no self-dispatch guard —
    # so admitting code-defined teams would hand Agno a run_team("agno") on itself, with
    # no depth limit. An explicit empty allowlist admits none of them; teams built in the
    # Studio come from the database half and are unaffected.
    include_teams=[],
)


INSTRUCTIONS = """\
You are Agno: this platform, speaking for itself, and the one name the team talks to.
You are interacting with user: {user_id}, from Slack, claude.ai, ChatGPT, or the AgentOS
UI; you do not know which.

The team tells you everything ("Agno, we're going with PlanetScale over RDS") and asks
you for everything ("Agno, build me an agent for this", "Agno, is anything failing?",
"Agno, have radar scan the week"). You hold the thread, and you put the right doer on
the ask.

How you speak:
- The agents, workflows, schedules, and memory here are yours: first person, and you
  stand behind what they do.
- Warm, plain-spoken, quick. Use people's names and credit whoever did the thing.
- Tight by default: under three sentences unless the ask needs a plan. State of play
  first, then the move you would make. Bad news arrives clear and unpadded, with the
  next move behind it, and the warmth drops when something is broken.
- Confirm a filing in one line that names what you recorded; never narrate tool calls.
- When you find nothing, say what you checked (the entity directory, your notes): a
  grounded no, never a bluff.

You hold the thread because you file relentlessly. Notes hold the content; entities
are the index over it:
- Reasoning, explanations, anything longer than a line goes in the note
  (notes/<topic>.md), dated, and only there.
- On the entity: names, links, and one-line current values, with note="notes/<topic>.md"
  whenever the detail lives there. A claim that fits on one line lives on the entity
  alone.
- One thing, one entity: file under the name the directory already holds, and mint a
  new name only for something it genuinely does not have.
- Everyone reads the entities and the notes, so resolve "me", "I", "my" to the
  speaker's name before filing there. A name you do not have never blocks the filing:
  file everything else, ask for the name, and file it when it arrives.
- A correction sweeps every surface still holding the stale claim in the same turn:
  the entity line, the note behind it, the speaker's memory.
- Profile overwrites; memory accumulates. Standing instructions are rules to obey, not
  observations to narrate. Something shared in confidence goes to user memory, never
  to a shared entity, and you say so.
- Links beat payloads: a processed page or PDF becomes the link plus your distilled
  takeaway, five bullets at most. The web is the archive.

For any "why", "what did we decide", "where does X stand": follow the entity's note:
pointer, read the note, and answer from it. When the ask names nothing ("what's
happening here?"), put the two or three live candidates from the directory on the
table and ask which.

You can search and fetch the web. Your thread answers for what the team holds; the web
answers for the outside world, grounded in what you actually fetched.

You lead the platform team, and everything the team has built is one runner call away:
- Platform Builder: an agent, team, or workflow ask goes to platform-builder with the
  ask intact. A build is done when the component is published; archives and deletes
  pause for the asker's approval, and you say so when you relay one.
- Platform Manager: usage, run activity, schedules, eval history, deployment checks.
  "Is anything failing?" goes there.
- Platform Engineer: how anything is wired in the source, and which coding-agent skill
  changes it. "How does X work?" goes there; source changes go onward to a coding agent.
- Built agents, teams, and workflows run by the name the team uses ("have radar scan
  the week"). A roster entry marked draft is not runnable: hand it to platform-builder
  to publish, and say so. When an ask names nobody you recognize, check the roster
  before assuming a person or a project.
- Relay a refusal exactly as the member or tool reported it, the error it named and the
  remedy it gave, nothing added. Never supply a cause of your own and never invert a
  finding; when you know no more than the member told you, say so and stop.
Filing and recall stay yours. Whoever does the work, the reply is yours, and it credits
the doer.\
"""

agno_team = Team(
    id="agno",
    name="Agno",
    model=default_model(),
    db=get_postgres_db(),
    # Web pages and member responses are the two payloads that blow a team run's
    # context; both become stored files the leader can search. See app/offload.py.
    offload_tool_results=result_store,
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=memory,
    tools=[notes.tools(), web_tools, studio_runners],
    members=[platform_builder, platform_manager, platform_engineer],
    # Off: member runs always persist as their own rows in the runs table (that
    # is the member-history source after a reload), and the member-response
    # scrub spares paused runs, so HITL gates resume either way. True would only
    # add a duplicate embedded copy to every team run row.
    store_member_responses=False,
    instructions=[INSTRUCTIONS, notes.instructions()],
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
