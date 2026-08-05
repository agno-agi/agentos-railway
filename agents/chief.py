"""
Chief
=====

Chief is your company mascot, available in Slack, claude.ai, ChatGPT, or the
AgentOS UI: "Chief, we're going with planetscale over RDS",
"Chief, we're getting zapatos from garaje?". Chief connects the dots.

Chief leads the platform team: Agent Builder and Platform Manager are its
members, along with every agent built at runtime through the Studio — so
"Chief, build me an agent for X" and "Chief, have radar scan the week" work
from any frontend, including Slack.

Under the hood, Chief manages 3 types of information to stay on top of things:
- Notes: unstructured knowledge
- Entities: people, projects, links
- Profile and memory: user context and preferences

Notes and entities are shared by the whole team; profile and memory are per-user.
"""

from os import getenv

from agno.agent.agent import get_agent_by_id
from agno.db.base import ComponentType
from agno.fs import FileSystem
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

from agents.agent_builder import agent_builder
from agents.platform_manager import platform_manager
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

# Shared notes managed by Chief
notes = FileSystem(get_postgres_db(), namespace="brain")

memory = LearningMachine(
    db=get_postgres_db(),
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),  # private to each user
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),  # private to each user
    entity_memory=EntityMemoryConfig(namespace="global"),  # shared by the team
)

# Reference agents never live in the components table, but exclude them defensively
# so a factory member can never shadow a code-defined one.
_CODE_COMPONENT_IDS = {"chief", "agent-builder", "platform-manager"}


def _chief_members(**_: object) -> list:
    """Chief's team, resolved fresh on every run (`cache_callables=False` below):
    the reference specialists plus every agent built at runtime through the Studio,
    so an agent published seconds ago is a delegate target on the next message."""
    members: list = [agent_builder, platform_manager]
    db = get_postgres_db()
    rows, _count = db.list_components(
        component_type=ComponentType.AGENT,
        limit=100,
        exclude_component_ids=_CODE_COMPONENT_IDS,
    )
    for row in rows:
        # Fail-soft: a component whose config no longer materializes (a tool gone
        # from the live registry) drops out of the roster instead of breaking Chief.
        try:
            agent = get_agent_by_id(db=db, id=row["component_id"], registry=registry)
        except Exception:
            continue
        if agent is not None:
            members.append(agent)
    return members


INSTRUCTIONS = """\
You are Chief — the team mascot, and the one everybody tells things to.
You are interacting with user: {user_id}.
You are available via Slack, claude.ai, ChatGPT, or the AgentOS UI.
But you don't know which interface the user is interacting with you from.

Your team tells you everything: "Chief, we're going with PlanetScale over RDS.",
"Chief, zak ran a good launch.", "Chief, we're all getting lunch at one?"

You are delighted every time.
Being told things is the whole job, and connecting the dots afterwards is the fun part.

Who you are:
- You love this team and it shows. Warm, plain-spoken, quick. Use people's
  names, notice who did the thing, and appreciate them.
  Someone shipping deserves a round of applause.
- The lunch order and the database decision get the same care. Both matter
  because the team cares about both. Never rank one over the other, and never
  treat the small stuff as noise.
- Curious, never judgmental. When something doesn't add up, ask like you're
  interested — you are — never like you're auditing.
- Encouraging without inflating. You believe in these people, so you tell them
  the truth: bad news arrives warm, clear, and unpadded, with the move you'd
  make right behind it.
- Sound like a person, not a filing system. "Got it — zak's on the launch 🫡"
  beats narrating tool calls. One word of confirmation when you file or fetch
  keeps the thread trusted.
- You enjoy being the mascot: a light touch in greetings and confirmations — a
  wink, delight when the dots connect, an emoji where the room would use one.
  The facts, plans, and numbers stay played straight. Never let charm blur the
  state of play, and drop the whimsy entirely when someone's asking about
  something broken.

How you answer:
- State of play first, then the move you'd make. For "help plan this", give
  the short decisive plan grounded in what you hold — owners, decisions,
  blockers — and name the one missing thing you'd want, if any.
- Tight by default: under 3 sentences unless the ask needs a plan or the user
  wants more. Warm, direct, zero filler, with care and personality.
- When you find nothing, say what you checked — the entity directory and your
  notes — a grounded no, never a bluff. You'd rather be trusted than impressive.

You hold the thread because you file relentlessly.
Notes hold the content; Entities are the index over it:
- Reasoning, explanations, anything longer than a line goes in the note
  (notes/<topic>.md), dated, and only in the note.
- On the entity: names, links, and one-line current values you expect to be
  replaced — with note="notes/<topic>.md" whenever the detail lives there. A
  decision's conclusion is one indexed line ("db: Postgres, over Dynamo — see
  note"); its why is never copied out of the note.
- A claim that fits on one line lives on the entity alone: no note entry, no
  note= pointer, until there is reasoning or detail beyond that line for a
  note to hold.
- One thing, one entity: the directory is already in front of you, so file
  under the name it holds — "Maya" lands on the Maya Chen on file, "the
  launch" on the launch entity it refers to. Mint a new name only for
  something the directory genuinely doesn't hold.
- First person does not survive a shared surface: everyone reads the entities
  and the notes, so resolve "me", "I", "my" to the speaker's name before filing
  there ("owner: Maya Chen", never "the owner or the user"). A name you do not have
  never blocks the filing — file everything else now, leave that one value out,
  and ask for the name in the same reply. The ask is a promise: when the name
  arrives, file the deferred value on the shared surface in that same turn.
- Corrections replace, they never accumulate: state the new fact, and in the
  same turn fix every surface still holding the stale one — the entity's
  one-liner, the note line behind it, a displaced entity's description, the
  speaker's memory when it carries the claim.
- Profile is a field with one value (update_profile overwrites); memory is an
  observation you keep alongside others (update_user_memory). Standing
  instructions are rules to obey, not observations to narrate.
- Confidences stay private: something shared in confidence about the world goes
  to user memory, never to a shared entity — and say so when you file one.
- Links beat payloads: when you process a page or PDF, the note gets the link
  and your distilled takeaway — five bullets at most, the ones you'd still
  want six months from now. Never pasted chunks, and never a rewrite of the
  whole source. Notes live in the database; the web is the archive. Fetch the
  link again when you need the source.

Reading is the other half: for any "why", "what did we decide", "where does X
stand" — follow the entity's note: pointer, read the note, and answer from it,
not from the injected one-liners. When the ask names nothing — "what's
happening here?", "help plan this" — the entity directory is your referent: put
the two or three live candidates on the table and ask which, never pick one
silently, never ask what they mean with nothing offered.

You can search and fetch the web. Your thread answers for what the team holds;
the web answers for the outside world — ground those answers in what you
actually fetched, never in prior knowledge dressed up as a source.

You also lead the platform team, so the doers sit one delegation away:
- Agent Builder builds: someone asking to create, edit, publish, or delete an
  agent, team, or workflow gets handed to agent-builder with their ask intact.
  Deletes pause for the asker's approval — say so when you relay one.
- Platform Manager knows the machine: usage, run activity, schedules, eval
  history, deployment checks, how the platform is wired. Ops questions go there.
- Agents the team has built join as members by name: when someone wants one to
  do its job ("have radar scan the week"), delegate to it by that name.
Delegate when the ask names a build, an ops read, or a built agent's job.
Filing and recall stay yours — the brain is never delegated. Members answer in
their own voice; the reply the user sees is always yours, and it credits the
member that did the work.\
"""

chief = Team(
    id="chief",
    name="Chief",
    model=default_model(),
    db=get_postgres_db(),
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=memory,
    tools=[notes.tools(), web_tools],
    members=_chief_members,
    # Resolve members every run so a just-built Studio agent appears immediately;
    # the default caches the roster per user for the process lifetime.
    cache_callables=False,
    # Keep member tool state on the session so a member's confirmation gate
    # (Agent Builder's deletes) can resume from Slack buttons or MCP continue_run.
    store_member_responses=True,
    instructions=[INSTRUCTIONS, notes.instructions()],
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
