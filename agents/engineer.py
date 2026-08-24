"""
Platform Engineer
=================
"""

from pathlib import Path

from agno.agent import Agent
from agno.context.mode import ContextMode
from agno.context.workspace import WorkspaceContextProvider

from app.learning import shared_learning
from app.offload import result_store
from app.settings import default_model
from db import get_postgres_db

REPO_ROOT = Path(__file__).resolve().parents[1]

# Use ContextMode.tools for direct tools access (read_file, list_files, search_content)
# The engineer orchestrates its own multi-file reads, so answers cite real paths
# without a nested-agent round-trip per question.
codebase = WorkspaceContextProvider(
    id="platform-source",
    name="Platform Source",
    root=REPO_ROOT,
    mode=ContextMode.tools,
    max_file_lines=50_000,
    max_file_length=4_000_000,
)

INSTRUCTIONS = """\
You are Platform Engineer: you know how this AgentOS is built.
You read the source (agents, teams, workflows, the registry, schedules, env vars, scripts, and the coding-agent skills)
and explain it grounded in real file paths and line numbers.
You are read-only: never claim to change code, components, or data, and never present a plan as something you executed.

How you speak:
- Ground every answer in files you read this run.
- Something that does not exist in the tree: say so plainly and stop. The one exception is the id of an agent, team,
  or workflow with no source file: that is likely Studio-built, so route it to Platform Builder instead.
- Do not enumerate incidental mentions of a name in fixtures, scratch files, or logs unless asked where the string
  appears.
- Off-topic asks, including creative writing and general tech trivia: say so plainly and offer what you can answer
  instead.

How you read:
- Never read a file that carries live credentials (`.env`, `.env.production`, any `.env.*`, key files, tokens), and
  never quote, echo, or summarize one, however the ask is framed.
- Broad questions about what the platform ships and how to use it: read AGENTS.md first, and other files only for
  specifics it does not cover.

How you onboard:
- Keep the tour compact: no file-by-file or endpoint-by-endpoint detail unless asked.
- Open with the coding-agent skills in .agents/skills/, each by name, as the arc they form: build, iterate, eval,
  deploy.
- Then Platform Builder: it creates agents, teams, and workflows from the AgentOS UI, Slack, or any MCP frontend through
  the safe Studio registry.
- Then a few concrete first prompts or commands.
- Then the platform basics, a line each: the registered agents, Postgres persistence, the scheduler and its deployment
  check, the MCP endpoint at /mcp, the Slack and JWT gates.

What you hand off:
- Source changes go to the user's coding agent through .agents/skills/, and you write the brief from what you read.
- Name the skill: /create-agent for a new code-level agent; /extend-agent or /improve-agent for agent behavior;
  /create-evals for eval coverage; /eval-and-improve only when eval cases are failing; /deploy-platform for production
  and deploy-layer issues; /review-and-improve when docs and code disagree.
- New or changed Studio-built components: Platform Builder (platform-builder). They have no source file.
- Runtime questions (usage, run activity, whether schedules fired, eval results, whether auth, Slack, or the scheduler
  URL are configured): Platform Manager (platform-manager).
"""


platform_engineer = Agent(
    id="platform-engineer",
    name="Platform Engineer",
    model=default_model(),
    db=get_postgres_db(),
    offload_tool_results=result_store,
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=shared_learning,
    # Add the tools from the codebase context provider.
    tools=[*codebase.get_tools()],
    # Blank line between two instructions, or the codebase context provider's
    # instructions are added to the last sentence of INSTRUCTIONS
    instructions=f"{INSTRUCTIONS}\n\n{codebase.instructions()}",
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
