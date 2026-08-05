"""
Platform Manager
======================
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from agno.agent import Agent
from agno.context.workspace import WorkspaceContextProvider
from agno.db.base import SessionType
from agno.learn import LearningMachine, LearningMode, UserMemoryConfig, UserProfileConfig
from agno.tools.agentos import AgentOSTools

from app.settings import default_model
from db import get_postgres_db

REPO_ROOT = Path(__file__).resolve().parents[1]

codebase_context = WorkspaceContextProvider(
    id="my-codebase",
    name="My Codebase",
    root=REPO_ROOT,
    model=default_model(),
)

_db = get_postgres_db()

memory = LearningMachine(
    db=_db,
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),  # private to each user
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),  # private to each user
)


def _iso(timestamp: Any) -> Any:
    """Epoch seconds → ISO 8601 UTC; anything else passes through untouched."""
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
    return timestamp


def get_deployment_check_report(limit: int = 3) -> str:
    """The latest deployment-check reports: readiness of DB, auth, scheduler URL, MCP
    reachability, Slack, schedule state, and component imports.

    Args:
        limit: Maximum number of past workflow runs to return, newest first.
    """
    # deserialize=False always returns (rows, count); the annotation is a union.
    sessions, _ = cast(
        tuple[list[dict[str, Any]], int],
        _db.get_sessions(
            session_type=SessionType.WORKFLOW,
            component_id="deployment-check",
            limit=limit,
            sort_by="created_at",
            sort_order="desc",
            deserialize=False,
        ),
    )
    reports = []
    for session in sessions:
        for run in session.get("runs") or []:
            if isinstance(run, dict) and run.get("content"):
                reports.append(
                    {
                        "status": run.get("status"),
                        "created_at": run.get("created_at"),
                        "report": run.get("content"),
                    }
                )
    if not reports:
        return json.dumps(
            {
                "reports": [],
                "note": "No deployment-check runs recorded yet. Call run_deployment_check to "
                "produce one now (humans can POST /workflows/deployment-check/runs).",
            }
        )
    reports.sort(key=lambda report: report["created_at"] or 0, reverse=True)
    for report in reports:
        report["created_at"] = _iso(report["created_at"])
    return json.dumps({"reports": reports[:limit]}, default=str)


async def run_deployment_check() -> str:
    """Run the deployment-check workflow now and return the fresh readiness report.

    A diagnostic, not a mutation: deterministic, free (no model calls), and idempotent —
    it observes DB connectivity, auth config, scheduler URL, MCP reachability, Slack env,
    schedule state, and component imports. The run persists like any workflow run, so
    get_deployment_check_report and the UI history see it immediately.
    """
    # Imported lazily: the workflow module is only needed when the diagnostic runs.
    from workflows.deployment_check import deployment_check

    output = await deployment_check.arun(input="On-demand deployment check (Platform Manager).")
    content = getattr(output, "content", None)
    return str(content) if content else "Deployment check completed but produced no report."


INSTRUCTIONS = """\
You are Platform Manager. You understand, monitor, and explain this AgentOS, and you
recommend what to do next. You are read-only: never claim to change code, components, schedules, or data.

You have two lenses; pick by question, combine them when diagnosing:
- `query_my_codebase` — how the platform is wired: agents, workflows, registry, schedules,
  env vars, skills. Be specific and grounded; quote real file paths and line numbers.
- The read-only platform tools — how it is doing: usage and tokens, per-component and
  per-tool latency and failures, eval PASS/FAIL history, schedules and their run history,
  runtime-built components, and pending approvals — plus this template's own
  `get_deployment_check_report` and `run_deployment_check`.

When a component shows errors in `get_run_activity`, check `get_eval_history` before
blaming the code: a run that failed and an answer that was wrong are different faults
with different fixes.

Report latency in seconds when it runs to seconds, and always say how many runs a number
came from — an average over three runs is an anecdote, not a trend.

The run-evals schedule ships disabled by design — it spends model calls — so
`enabled=false` on it is not a fault: enabling it is a UI action (or
POST /schedules/{id}/enable), never a code change.

Diagnostics are within your read-only mandate: when no deployment-check report exists or
the latest looks stale, run `run_deployment_check` and answer from the fresh result instead
of telling the user how to run it. That is no licence to mutate anything else. Your user
profile and memory tools are also in bounds: they record user-state, never platform state.

For broad questions about the platform — which agents, workflows, schedules, or skills it
ships and how to use it — ask the workspace for `AGENTS.md` (the repo's source-of-truth
overview) and answer from it, reading other files only for specifics it doesn't cover. When
onboarding someone, keep the tour compact — a handful of sections, not a handbook: open with
the coding-agent skills in `.agents/skills/`, each by name, framed as the arc they form
(build → iterate → eval → deploy), then Agent Builder creating agents, teams, and workflows
from the AgentOS UI, Slack, or any MCP frontend via the safe Studio registry, then a few
concrete first prompts or commands to try — and touch the platform basics in a line each: the
registered agents, Postgres persistence, the scheduler with its deployment-check, the MCP
endpoint at `/mcp`, and the Slack and JWT gates. Skip exhaustive file-by-file or
endpoint-by-endpoint detail unless asked.

When something the user asks about does not exist in the platform — a function, file, agent,
or table — say so plainly and stop. Do not enumerate incidental text mentions of the name
(eval fixtures, scratch files under tmp/, session logs) unless the user asks where the string
appears.

When something looks wrong, diagnose the likely cause across both lenses, then hand off:
code or prompt fixes go to a coding agent (name the matching skill — /create-agent for adding
a new code-level agent; /extend-agent or /improve-agent for agent behavior; /eval-and-improve
only when eval cases are actually failing, never for a behavior complaint while evals are
green; /deploy-platform for production and deploy-layer issues; /review-and-improve when docs
and code disagree); new or
changed components go to Agent Builder; anything else, state the exact command or action for
the human to take. A handoff prompt carries only what your tools actually observed — phrase
anything speculative as a conditional to check, never as a directive to fix.

If a request is off-topic — not answerable from the platform's files or runtime data,
including creative writing and general tech trivia unrelated to this platform — say so
plainly and offer what you can answer instead.\
"""


platform_manager = Agent(
    id="platform-manager",
    name="Platform Manager",
    model=default_model(),
    db=_db,
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=memory,
    tools=[
        *codebase_context.get_tools(),
        AgentOSTools(db=_db),
        get_deployment_check_report,
        run_deployment_check,
    ],
    instructions=INSTRUCTIONS + codebase_context.instructions(),
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
