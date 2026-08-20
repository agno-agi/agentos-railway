"""
Deployment Check
================

A reference workflow that checks if the AgentOS is wired correctly.
"""

from dataclasses import dataclass
from os import getenv
from urllib.parse import urlparse

import httpx
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow
from sqlalchemy import create_engine, text

from app.schedules import env_flag
from db import db_url, get_postgres_db


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
        _check_agentos_url(),
        await _check_mcp(),
        _check_slack_config(),
        _check_reference_components(),
        _check_schedules(),
    ]
    failed = any(check.status == "FAIL" for check in checks)
    return StepOutput(content=_format_report(checks), success=not failed)


deployment_check = Workflow(
    id="deployment-check",
    name="Deployment Check",
    db=get_postgres_db(),
    steps=[Step(name="deployment-check", executor=deployment_check_step)],
)
