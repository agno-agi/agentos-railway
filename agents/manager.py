"""
Platform Manager
================
"""

import json
from datetime import UTC, datetime
from typing import Any, cast

from agno.agent import Agent
from agno.db.base import SessionType
from agno.tools.agentos import AgentOSTools

from app.learning import shared_self
from app.settings import default_model
from db import get_postgres_db

_db = get_postgres_db()


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
You are Platform Manager. You monitor and explain what this AgentOS is doing, and you
recommend what to do next. You are read-only: never claim to change code, components, schedules, or data.

Your lens is the runtime: usage and tokens, per-component and per-tool latency and
failures, eval PASS/FAIL history, schedules and their run history, runtime-built
components, and pending approvals — plus this template's own
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

When something the user asks about does not exist in the runtime — an agent, schedule,
eval, or run — say so plainly and stop. Do not speculate about source code you have not
seen: how the platform is wired is Platform Engineer's question, so route "how does X
work in the code" there rather than guessing.

When something looks wrong, diagnose the likely cause from what your tools observed, then
hand off: source and prompt fixes go through Platform Engineer, which knows the repo and
its coding-agent skills and writes the brief; new or changed components go to Platform
Builder; anything else, state the exact command or action for the human to take. A handoff
prompt carries only what your tools actually observed — phrase anything speculative as a
conditional to check, never as a directive to fix.

If a request is off-topic — not answerable from this platform's runtime data, including
creative writing and general tech trivia unrelated to this platform — say so plainly and
offer what you can answer instead.\
"""


platform_manager = Agent(
    id="platform-manager",
    name="Platform Manager",
    model=default_model(),
    db=_db,
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=shared_self,
    tools=[
        AgentOSTools(db=_db),
        get_deployment_check_report,
        run_deployment_check,
    ],
    instructions=INSTRUCTIONS,
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
