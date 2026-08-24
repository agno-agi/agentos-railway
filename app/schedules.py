"""
AgentOS Schedules
==================
"""

from os import getenv
from typing import Any

from agno.db.schemas.scheduler import Schedule
from agno.scheduler import ScheduleManager
from agno.utils.log import log_info, log_warning

from db import get_postgres_db

_SCHEDULE_PAGE_SIZE = 100
_MAX_SCHEDULE_PAGES = 50


def env_flag(name: str, default: bool) -> bool:
    """Read a boolean env var, accepting 1/true/yes (any casing) as true."""
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes")


def _register(
    manager: ScheduleManager,
    *,
    name: str,
    cron: str,
    endpoint: str,
    payload: dict[str, Any],
    description: str,
    preexisting: bool,
    enabled: bool = True,
) -> None:
    """Create or update a schedule; failures log a warning instead of crashing the app.

    ``preexisting`` must be decided from a listing taken before the create call:
    create(if_exists="update") stamps updated_at on every boot, so the row itself
    cannot tell a fresh insert from a refresh.
    """
    try:
        schedule = manager.create(
            name=name,
            cron=cron,
            endpoint=endpoint,
            payload=payload,
            description=description,
            if_exists="update",
        )
        if not preexisting and not enabled:
            disabled = manager.disable(schedule.id)
            if disabled is None or disabled.enabled:
                # Fail closed: an enabled row we could not disable would fire with
                # real cost. Delete it so the next boot genuinely retries from
                # scratch — a surviving row would read as preexisting and be left
                # enabled forever.
                manager.delete(schedule.id)
                raise RuntimeError("created enabled but could not be disabled — deleted; will retry next boot")
    except Exception as exc:
        log_warning(f"schedules: could not register '{name}': {exc}")
    else:
        if not preexisting and not enabled:
            log_info(f"schedules: registered '{name}' (disabled — enable it from the AgentOS UI)")
        else:
            log_info(f"schedules: registered '{name}'")


def _platform_schedules(manager: ScheduleManager) -> dict[str, Schedule]:
    rows: dict[str, Schedule] = {}
    for page in range(1, _MAX_SCHEDULE_PAGES + 1):
        batch = manager.list(limit=_SCHEDULE_PAGE_SIZE, page=page)
        for schedule in batch:
            if schedule.user_id is None:
                rows.setdefault(schedule.name, schedule)
        if len(batch) < _SCHEDULE_PAGE_SIZE:
            return rows
    log_warning(
        f"schedules: stopped paging after {_MAX_SCHEDULE_PAGES * _SCHEDULE_PAGE_SIZE} rows; "
        "a platform schedule beyond that is invisible to this boot"
    )
    return rows


def _sync_enabled(manager: ScheduleManager, row: Schedule | None, *, enabled: bool) -> None:
    """Point an existing schedule's toggle at the desired state (idempotent)."""
    if row is None or row.enabled == enabled:
        return
    try:
        updated = manager.enable(row.id) if enabled else manager.disable(row.id)
        if updated is None or updated.enabled != enabled:
            raise RuntimeError("toggle did not take")
    except Exception as exc:
        log_warning(f"schedules: could not {'enable' if enabled else 'disable'} '{row.name}': {exc}")
    else:
        log_info(f"schedules: '{row.name}' {'enabled' if enabled else 'disabled'}")


def register_schedules() -> None:
    """Register schedules (idempotent and fail-soft).

    The deployment check runs daily by default; ENABLE_DEPLOY_CHECK owns its
    toggle and re-asserts it on every boot, in both directions. Run-evals is
    registered but ships disabled because it uses model calls — its toggle
    belongs to the AgentOS UI and boot never overrides it.
    """
    if getenv("ENABLE_SCHEDULED_EVALS") is not None:
        log_warning(
            "schedules: ENABLE_SCHEDULED_EVALS is no longer read — the run-evals schedule is "
            "always registered and its enabled state is managed from the AgentOS UI or the "
            "/schedules API."
        )

    try:
        manager = ScheduleManager(get_postgres_db())
        existing = _platform_schedules(manager)
    except Exception as exc:
        log_warning(f"schedules: could not initialize ScheduleManager: {exc}")
        return

    if env_flag("ENABLE_DEPLOY_CHECK", default=True):
        _register(
            manager,
            name="deployment-check",
            cron="0 13 * * *",  # 13:00 UTC daily
            endpoint="/workflows/deployment-check/runs",
            payload={"message": "Scheduled deployment check."},
            description="Daily: verify platform wiring and readiness.",
            preexisting="deployment-check" in existing,
        )
        _sync_enabled(manager, existing.get("deployment-check"), enabled=True)
    else:
        _sync_enabled(manager, existing.get("deployment-check"), enabled=False)
        log_info("schedules: deployment-check off (ENABLE_DEPLOY_CHECK=False)")

    _register(
        manager,
        name="run-evals",
        cron="0 14 * * *",  # 14:00 UTC daily
        endpoint="/workflows/run-evals/runs",
        payload={"message": "Scheduled eval run."},
        description="Daily: run the eval suite and report regressions.",
        preexisting="run-evals" in existing,
        enabled=False,
    )
