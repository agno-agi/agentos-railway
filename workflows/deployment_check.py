"""
Deployment Check
================

A reference workflow that checks if the AgentOS is wired correctly.
"""

from dataclasses import dataclass
from os import getenv
from time import time
from urllib.parse import urlparse

import httpx
from agno.db.schemas.scheduler import Schedule
from agno.scheduler import ScheduleManager
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow
from sqlalchemy import create_engine, text

from app.schedules import env_flag
from db import db_url, get_postgres_db

# The poller ticks every 15s (AgentOS's default) and claims any enabled schedule whose
# next_run_at has passed, so on a live platform a due-and-unclaimed row is only ever
# seconds old. 15 minutes is ~60 ticks of headroom and still far inside the daily
# cadence both reference schedules run at.
_POLLER_GRACE_SECONDS = 900

# agno's claim_due_schedule reclaims a lock older than 300s, so a younger lock means a
# run is genuinely in flight — including this very run, when the poller triggered it.
_LOCK_GRACE_SECONDS = 300

# Enough history to look past an orphaned `running` row (a process killed mid-run leaves
# one behind forever) and still find the last run that actually reached a verdict.
_POLLER_RUN_WINDOW = 5


@dataclass(frozen=True)
class CheckResult:
    """One deployment readiness check."""

    name: str
    status: str
    detail: str


def _pass(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="PASS", detail=detail)


def _warn(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="WARN", detail=detail)


def _fail(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status="FAIL", detail=detail)


def _check_database() -> CheckResult:
    db = get_postgres_db()
    sessions_table = f"{db.db_schema}.{db.session_table_name}"
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            table_exists = conn.execute(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": sessions_table},
            ).scalar()
    except Exception as exc:
        return _fail("Database", f"Could not connect using configured DB_* env vars: {exc}")
    finally:
        engine.dispose()

    if table_exists is None:
        return _fail("Database", f"Connected, but expected table {sessions_table} is missing.")
    return _pass("Database", f"Connected and found {sessions_table}.")


def _check_runtime() -> CheckResult:
    runtime_env = getenv("RUNTIME_ENV", "prd")
    if runtime_env == "prd":
        if getenv("JWT_VERIFICATION_KEY") or getenv("JWT_JWKS_FILE"):
            return _pass("Runtime", "Production mode with JWT verification configured.")
        return _fail("Runtime", "Production mode requires JWT_VERIFICATION_KEY or JWT_JWKS_FILE.")
    if runtime_env == "dev":
        return _warn(
            "Runtime",
            "Development mode; JWT authorization is disabled. Expected locally — "
            "if this is a production deploy, remove RUNTIME_ENV=dev from the synced env vars.",
        )
    return _warn("Runtime", f"Unexpected RUNTIME_ENV={runtime_env!r}; expected 'dev' or 'prd'.")


def _check_openai_key() -> CheckResult:
    """The one env var whose absence every other check survives."""
    if getenv("OPENAI_API_KEY"):
        return _pass("OpenAI key", "Set — models, knowledge embeddings, and the registry's media tools.")
    return _fail(
        "OpenAI key",
        "OPENAI_API_KEY is not set: every model call fails, knowledge cannot embed, and the "
        "registry drops its image and speech tools with no warning.",
    )


def _check_agentos_url() -> CheckResult:
    runtime_env = getenv("RUNTIME_ENV", "prd")
    agentos_url = getenv("AGENTOS_URL", "http://127.0.0.1:8000")
    parsed = urlparse(agentos_url)
    if not parsed.scheme or not parsed.netloc:
        return _fail("AgentOS URL", f"AGENTOS_URL is not a valid absolute URL: {agentos_url!r}.")

    localhost_names = {"127.0.0.1", "localhost", "0.0.0.0"}
    if runtime_env == "prd" and parsed.hostname in localhost_names:
        return _fail("AgentOS URL", "Production scheduler cannot reach AgentOS at a localhost URL.")
    return _pass("AgentOS URL", f"Scheduler base URL is {agentos_url}.")


async def _check_mcp() -> CheckResult:
    """The MCP endpoint is the surface chat apps and coding agents depend on; a proxy
    that strips or misroutes /mcp would otherwise pass every other check.

    Async on purpose: the workflow runs in-process, so a blocking self-request would
    deadlock the event loop that has to serve it."""
    mcp_url = getenv("AGENTOS_URL", "http://127.0.0.1:8000").rstrip("/") + "/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "deployment-check", "version": "1.0"},
        },
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                mcp_url,
                json=payload,
                headers={"Accept": "application/json, text/event-stream"},
            )
    except Exception as exc:
        return _warn("MCP", f"Could not reach {mcp_url}: {exc}")
    if response.status_code == 404:
        return _fail("MCP", f"{mcp_url} returned 404 — MCP server not mounted, or the route is stripped upstream.")
    if response.status_code in (401, 403):
        return _pass("MCP", f"{mcp_url} is mounted and auth-gated (HTTP {response.status_code}).")
    if response.status_code >= 500:
        return _warn("MCP", f"{mcp_url} is mounted but returned HTTP {response.status_code}.")
    return _pass("MCP", f"{mcp_url} responded (HTTP {response.status_code}).")


def _check_slack_config() -> CheckResult:
    token = bool(getenv("SLACK_BOT_TOKEN"))
    signing_secret = bool(getenv("SLACK_SIGNING_SECRET"))
    if token and signing_secret:
        return _pass("Slack", "Slack interface credentials are both set.")
    if token or signing_secret:
        return _warn("Slack", "Only one Slack credential is set; Slack interface will stay disabled.")
    return _pass("Slack", "Slack interface is disabled; no partial credentials found.")


def _check_reference_components() -> CheckResult:
    try:
        from agents.builder import platform_builder
        from agents.engineer import platform_engineer
        from agents.manager import platform_manager
        from app.registry import registry
        from teams.lead import agno_team
        from workflows.run_evals import run_evals
    except Exception as exc:
        return _fail("Components", f"Could not import reference components: {exc}")

    component_ids = sorted(
        [
            component_id
            for component_id in (agno_team.id, platform_builder.id, platform_manager.id, platform_engineer.id)
            if component_id
        ]
    )
    workflow_ids = sorted([workflow_id for workflow_id in (deployment_check.id, run_evals.id) if workflow_id])
    return _pass(
        "Components",
        "Reference components import cleanly: "
        f"components={', '.join(component_ids)}; workflows={', '.join(workflow_ids)}. "
        f"Registry has {len(registry.tools)} tools.",
    )


def _check_registry_resources() -> CheckResult:
    """The registry entries built components hold by NAME rather than by reference.

    A Studio-built component stores `{"name": "shared-learning"}` and resolves the live object
    out of the registry on every load, so the name is the wiring. The run routes resolve
    strict: a name that stopped being registered is a 422 on every run of every component
    wired to it, and the lenient paths (history reads, cancel) are worse — they drop the
    reference and hand back a component running without its self. The import check above
    cannot see any of that, because app/registry.py imports perfectly cleanly with an
    entry deleted from its lists. Two distinct instances claiming one name fail the same
    way: strict rehydration refuses the ambiguity rather than guess which store to bind.
    """
    try:
        from app.knowledge import KNOWLEDGE_NAME, PRODUCT_KNOWLEDGE_NAME
        from app.learning import SHARED_LEARNING_NAME
        from app.registry import registry
    except Exception as exc:
        return _fail("Registry", f"Could not import the registry and its named resources: {exc}")

    missing: list[str] = []
    ambiguous: list[str] = []
    if registry.get_learning(SHARED_LEARNING_NAME) is None:
        missing.append(f"learning {SHARED_LEARNING_NAME!r}")
    elif registry.learning_name_is_ambiguous(SHARED_LEARNING_NAME):
        ambiguous.append(f"learning {SHARED_LEARNING_NAME!r}")
    for knowledge_name in (KNOWLEDGE_NAME, PRODUCT_KNOWLEDGE_NAME):
        if registry.get_knowledge(knowledge_name) is None:
            missing.append(f"knowledge {knowledge_name!r}")
        elif registry.knowledge_name_is_ambiguous(knowledge_name):
            ambiguous.append(f"knowledge {knowledge_name!r}")

    if missing:
        return _fail(
            "Registry",
            f"Not registered: {', '.join(missing)}. Every published component wired to the name "
            "fails to load until it is back.",
        )
    if ambiguous:
        return _fail(
            "Registry",
            f"Two distinct instances claim {', '.join(ambiguous)}; a strict load refuses the "
            "reference rather than bind the wrong one. Give them distinct names.",
        )
    return _pass("Registry", f"Named resources resolve: {SHARED_LEARNING_NAME!r}, {KNOWLEDGE_NAME!r}.")


def _relative(epoch: int | None, now: int) -> str:
    """A schedule timestamp as an age or a countdown — a bare epoch tells a reader nothing."""
    if epoch is None:
        return "never"
    delta = abs(now - epoch)
    if delta < 90:
        span = f"{delta}s"
    elif delta < 5400:
        span = f"{delta // 60}m"
    else:
        span = f"{delta // 3600}h"
    return f"{span} ago" if epoch <= now else f"in {span}"


def _check_poller() -> CheckResult:
    """Whether the scheduler poller is actually firing — evidence, not configuration.

    This is the only check that catches the failure AGENTOS_URL's doc row is written
    about. The poller runs inside this process and reaches the app by calling back over
    that URL, so on a topology where the URL does not resolve to this app the loop keeps
    ticking, every other check keeps passing, and scheduled work silently stops. Both
    halves of that leave a trace on the deployment check's own schedule:

    - Not claiming. The poller claims any enabled schedule whose next_run_at has passed
      and only then advances it, so an unlocked row overdue by more than a few ticks
      means nothing is polling at all. A live poller self-corrects a stale next_run_at
      within one tick, which is what makes the overdue reading trustworthy.
    - Claiming but not arriving. agno's executor writes a schedule_runs row *before* it
      makes the HTTP call, so an unreachable callback lands as a `failed` row carrying
      the transport error — the row's existence is itself proof the poller got that far.

    Free and deterministic: two small reads, no model call, no mutation.
    """
    try:
        row = get_postgres_db().get_schedule_by_name("deployment-check")
        if row is None:
            return _warn("Poller", "No 'deployment-check' schedule to measure the poller against.")
        schedule = Schedule.from_dict(row) if isinstance(row, dict) else row
        runs = ScheduleManager(get_postgres_db()).get_runs(schedule.id, limit=_POLLER_RUN_WINDOW)
    except Exception as exc:
        return _warn("Poller", f"Could not read the schedule and its run history: {exc}")

    if not schedule.enabled:
        return _pass("Poller", "Not measurable: the deployment-check schedule is disabled.")

    now = int(time())
    # A row locked recently is executing right now — very possibly this run — and its
    # next_run_at stays at the past value until the executor releases it, so the overdue
    # reading below would be a false alarm. A lock past the reclaim threshold is debris
    # from a killed process and proves nothing, so it falls through.
    lock_age = now - schedule.locked_at if schedule.locked_at is not None else None
    executing = schedule.locked_by is not None and (lock_age is None or lock_age < _LOCK_GRACE_SECONDS)
    overdue_by = now - schedule.next_run_at if schedule.next_run_at is not None else None
    if not executing and overdue_by is not None and overdue_by > _POLLER_GRACE_SECONDS:
        return _fail(
            "Poller",
            f"deployment-check came due {_relative(schedule.next_run_at, now)} and nothing has claimed it. "
            "The poller is not running — restart the app, and check the startup logs for a scheduler error.",
        )

    if not runs:
        if executing:
            return _pass("Poller", "The poller has just claimed deployment-check; no run is recorded yet.")
        return _pass(
            "Poller",
            f"Armed; deployment-check has not fired yet (next run due {_relative(schedule.next_run_at, now)}). "
            "Every boot re-arms the schedule, so a recently restarted app reads this way.",
        )

    latest = next((run for run in runs if run.status != "running"), None)
    if latest is None:
        return _pass("Poller", f"The poller has claimed deployment-check ({len(runs)} in flight, none finished yet).")

    when = _relative(latest.completed_at or latest.triggered_at, now)
    if latest.status == "success":
        return _pass(
            "Poller", f"Last scheduled run succeeded {when}; next run due {_relative(schedule.next_run_at, now)}."
        )
    if latest.status == "paused":
        return _warn("Poller", f"Last scheduled run paused {when} waiting on a confirmation and never resumed.")
    error = (latest.error or "no error recorded").strip().replace("\n", " ")[:200]
    return _fail(
        "Poller",
        f"Last scheduled run {latest.status} {when}: {error}. The run row exists, so the poller claimed the "
        "schedule and the failure is downstream of it — check AGENTOS_URL and the target endpoint.",
    )


def _check_schedules() -> CheckResult:
    def state(name: str) -> tuple[str, bool | None]:
        row = get_postgres_db().get_schedule_by_name(name)
        if row is None:
            return f"{name} not registered", None
        enabled = bool(row["enabled"] if isinstance(row, dict) else row.enabled)
        return f"{name} {'enabled' if enabled else 'disabled'}", enabled

    try:
        deploy_state, _deploy_enabled = state("deployment-check")
        evals_state, evals_enabled = state("run-evals")
    except Exception as exc:
        return _warn("Schedule", f"Could not read schedules from the database: {exc}")

    detail = f"{deploy_state}; {evals_state}."
    if evals_enabled is None:
        return _warn("Schedule", f"{detail} If the Database check passed, restart the API to register it.")
    if "not registered" in deploy_state and env_flag("ENABLE_DEPLOY_CHECK", default=True):
        return _warn("Schedule", f"{detail} If the Database check passed, restart the API to register it.")
    if evals_enabled is False:
        return _pass("Schedule", f"{detail} Enable run-evals from the AgentOS UI for scheduled eval runs.")
    return _pass("Schedule", detail)


def _format_report(checks: list[CheckResult]) -> str:
    failed = sum(1 for check in checks if check.status == "FAIL")
    warned = sum(1 for check in checks if check.status == "WARN")
    overall = "FAIL" if failed else "WARN" if warned else "PASS"

    lines = [
        "# Deployment Check",
        "",
        f"Overall: **{overall}** ({failed} failed, {warned} warning)",
        "",
    ]
    lines.extend(f"- **{check.status}** {check.name}: {check.detail}" for check in checks)
    return "\n".join(lines)


async def deployment_check_step(_step_input: StepInput) -> StepOutput:
    """Run deterministic deployment readiness checks and return a report."""
    checks = [
        _check_database(),
        _check_runtime(),
        _check_openai_key(),
        _check_agentos_url(),
        await _check_mcp(),
        _check_slack_config(),
        _check_reference_components(),
        _check_registry_resources(),
        _check_schedules(),
        _check_poller(),
    ]
    failed = any(check.status == "FAIL" for check in checks)
    return StepOutput(content=_format_report(checks), success=not failed)


deployment_check = Workflow(
    id="deployment-check",
    name="Deployment Check",
    db=get_postgres_db(),
    steps=[Step(name="deployment-check", executor=deployment_check_step)],
)
