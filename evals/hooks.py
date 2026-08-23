"""
Eval Hooks
==========

The setup/teardown machinery behind `evals/cases.py`: pre-case snapshots and
post-case sweeps of Studio components, schedules, learning rows, and notes.
Capture and create/edit/publish are ungated, so a case's rows really land in
the shared stores — these hooks remove what the case created, and refuse
rather than guess when a snapshot looks incomplete.

Cases take the ready-made pairs:

- `**BUILDER_HOOKS` — any case whose component can reach the builder's ungated
  create/edit/publish tools: every `platform-builder` case, and any `agno` case
  one delegation away from a build. Sweeps components, schedules, and learnings.
- `**LEARNING_HOOKS` — every other case probing a learning-store component
  (`agno`, `platform-manager`, `platform-engineer`). Sweeps entities, memories,
  profiles, and notes.

The builder pair is a strict superset, so upgrading a borderline case is safe.
"""

import asyncio
import time
from typing import Any

from agno.eval import CaseResult
from agno.run.base import RunStatus
from agno.scheduler.manager import ScheduleManager

from app.notes import notes
from db import get_postgres_db

# Eval DB instance (where results are stored)
eval_db = get_postgres_db()

_COMMIT_GRACE_SECONDS = 10


async def _let_inflight_writes_land(result: CaseResult) -> None:
    """Wait out an in-flight write before sweeping, whenever the run was cut short.

    The cost is a pause on abort — Ctrl-C during a builder case takes this long to quit —
    and it buys back the leak that pause prevents: a published component nobody swept, or
    a case-created schedule that then fires daily."""
    if result.response is not None and result.response.status == RunStatus.completed:
        return
    await asyncio.sleep(_COMMIT_GRACE_SECONDS)


def snapshot_component_ids() -> set[str]:
    """`setup` hook for Studio-builder cases: Studio component ids present before
    the case runs. The runner passes the returned set to the teardown as context.
    Tombstones are included so a pre-existing archived component never reads as
    new to the diff (the sweep would hard-delete it)."""
    components, _ = eval_db.list_components(limit=1000, include_deleted=True)
    return {component["component_id"] for component in components}


def delete_new_components(pre_run_ids: set[str]) -> None:
    """Hard-deletes only components that did not exist before the case ran — a
    user's own components are never touched, whatever the eval run happened to
    name its creations. Also used standalone by the improve-agent skill to
    bracket probe loops against Studio-builder agents."""
    # include_deleted: a component the case created and then archived would
    # otherwise vanish from the listing and leak its tombstone. Workflows and
    # teams go before agents so dependent tracking never refuses a member's
    # delete mid-sweep.
    components, _ = eval_db.list_components(limit=1000, include_deleted=True)
    new = [component for component in components if component["component_id"] not in pre_run_ids]
    order = {"workflow": 0, "team": 1, "agent": 2}
    new.sort(key=lambda component: order.get(str(component.get("component_type", "")), 3))
    for component in new:
        eval_db.delete_component(component["component_id"], hard_delete=True)


async def cleanup_new_components(pre_run_ids: set[str], result: CaseResult) -> None:
    """`teardown` hook for cases whose run may create Studio components (create/edit/
    publish are ungated, so components really land in the DB). The runner invokes it
    on pass, fail, error, and timeout alike, with the `setup` snapshot as context."""
    await _let_inflight_writes_land(result)
    await asyncio.to_thread(delete_new_components, pre_run_ids)


def snapshot_learning_state() -> dict[str, set[str]]:
    """`setup` hook for cases probing a component with learning stores (agno,
    platform-builder, platform-manager, platform-engineer): the learning ids (entities,
    profiles, memories) and note paths present before the case runs, so the teardown
    can delete only what the case created.

    `taken_at` is the cutoff the teardown's refusal rests on: epoch seconds, the same
    clock and the same truncation the learnings table's own `created_at` is written with
    (`int(time.time())`, in the process that runs the agent — the eval runner's own, in
    both sanctioned paths). It rides in a one-element set so the whole snapshot stays a
    dict of string sets: the improve-agent skill round-trips this through JSON with
    `sorted()` on the way out and `set()` on the way back."""
    # The cutoff is read before the rows, never after — a row written between the two
    # would otherwise look older than the snapshot and trip the refusal for nothing.
    taken_at = int(time.time())
    return {
        "taken_at": {str(taken_at)},
        "learning_ids": {str(row["learning_id"]) for row in eval_db.get_learnings()},
        "note_paths": {meta.path for meta in notes.list()},
    }


# Second line of defence behind the predating-row refusal in delete_new_learning_state:
# one case writes a handful of learning rows, so far more than this is worth a human look
# even when every new row does postdate the snapshot — a capture loop that ran away, or a
# second writer on the platform during the case window.
_MAX_SWEPT_LEARNINGS = 25


def _snapshot_cutoff(pre_run: dict[str, set[str]]) -> int:
    """The `taken_at` epoch second out of a learning snapshot.

    A snapshot without exactly one is hand-built or from an older shape, and cannot carry
    the refusal below. Say so rather than sweeping with the guard silently disabled."""
    stamps = pre_run.get("taken_at") or set()
    if len(stamps) != 1:
        raise RuntimeError(
            "refusing to sweep learning rows: this snapshot carries no single 'taken_at' cutoff, "
            "so a row cannot be told apart from one that predates the case. Re-take it with "
            "snapshot_learning_state()."
        )
    return int(next(iter(stamps)))


def delete_new_learning_state(pre_run: dict[str, set[str]], max_swept: int | None = None) -> None:
    """Hard-deletes learnings (entities, profiles, memories) and notes that did not exist
    before the case ran. Also used standalone by the improve-agent skill to bracket
    probe loops against learning-store agents (uncapped there — a probe campaign
    legitimately creates many rows)."""
    # Read before anything is deleted, so a snapshot of the wrong shape refuses first.
    taken_at = _snapshot_cutoff(pre_run)
    # Notes first: their snapshot cannot be silently empty (notes.list() raises on DB
    # failure, failing the setup), so they are safe to sweep even when the learnings
    # guard below refuses.
    for meta in notes.list():
        if meta.path not in pre_run["note_paths"]:
            notes.delete(meta.path)
    new = [row for row in eval_db.get_learnings() if str(row["learning_id"]) not in pre_run["learning_ids"]]
    # The guard that matters, and the reason it is structural rather than a count: this is
    # the only path in the repo that hard-deletes user data, and get_learnings swallows DB
    # errors into an empty list, so one transient failure during `setup` makes every
    # pre-existing row read as new. A row created before the snapshot was taken cannot be a
    # row this case created, so one appearing here is proof the snapshot missed rows — and
    # that proof shows up at any platform size, which a count never does: at a dozen rows —
    # a platform a few conversations old — `12 > 25` is False, no cap fires, and every user
    # profile, memory, and shared entity goes. A NULL created_at counts as predating too:
    # unattributable is precisely what the refusal is for.
    predating = sorted(str(row["learning_id"]) for row in new if int(row.get("created_at") or 0) < taken_at)
    if predating:
        raise RuntimeError(
            f"refusing to sweep learning rows: {len(predating)}/{len(new)} rows missing from the "
            f"pre-case snapshot were created before it was taken (e.g. {predating[0]}) — the "
            "snapshot is incomplete, so none of them are safely attributable to the case. Inspect "
            "them and delete by hand: eval_db.delete_learning(<id>)."
        )
    if max_swept is not None and len(new) > max_swept:
        raise RuntimeError(
            f"refusing to sweep {len(new)} learning rows (cap {max_swept}): that is far more than a "
            "case writes, so these rows are not safely attributable to it. "
            "Inspect them and delete by hand: eval_db.delete_learning(<id>)."
        )
    for row in new:
        eval_db.delete_learning(str(row["learning_id"]))


async def cleanup_new_learning_state(pre_run: dict[str, set[str]], result: CaseResult) -> None:
    """`teardown` hook for cases whose run may write to the learning stores (capture is
    ungated, so entities, memories, and notes really land in the DB). The runner invokes it
    on pass, fail, error, and timeout alike, with the `setup` snapshot as context."""
    await _let_inflight_writes_land(result)
    await asyncio.to_thread(delete_new_learning_state, pre_run, _MAX_SWEPT_LEARNINGS)


def snapshot_schedule_ids() -> set[str]:
    """Schedule ids present before a builder case runs — the builder can create
    schedules, and a case-created schedule left behind would fire daily."""
    return {schedule.id for schedule in ScheduleManager(eval_db).list(limit=1000)}


# Registered by app/schedules.py on every boot. Spared by name because sweeping one
# costs real state: deployment-check stops running until the next boot, and run-evals
# returns disabled, silently reverting whoever enabled it. On a booted DB the spare is
# belt-and-braces (their ids pre-exist, and the boot registration's if_exists="update"
# refreshes the unowned rows in place rather than minting new ones); the guard in
# delete_new_schedules below covers the one case where name and id evidence disagree.
_CODE_REGISTERED_SCHEDULES = frozenset({"deployment-check", "run-evals"})

# A builder case creates a schedule or two. Far more looks like the same failure the
# learnings cap guards: get_schedules swallows DB errors into an empty list, so a
# transient failure during `setup` makes every existing schedule read as new.
_MAX_SWEPT_SCHEDULES = 5


def delete_new_schedules(pre_run_ids: set[str]) -> None:
    """Hard-deletes schedules that did not exist before the case ran, sparing the
    template's own two."""
    manager = ScheduleManager(eval_db)
    schedules = manager.list(limit=1000)
    # A reserved-named schedule the snapshot doesn't know is ambiguous: either the
    # snapshot silently failed (get_schedules swallows DB errors into an empty list)
    # and this is the real one, or the DB never booted and a case minted an impostor
    # that would outlive the sweep and stay enabled once a boot absorbs the name.
    # Neither should be resolved silently — refuse and let a human look.
    if not pre_run_ids and any(schedule.name in _CODE_REGISTERED_SCHEDULES for schedule in schedules):
        raise RuntimeError(
            "refusing to sweep schedules: the pre-case snapshot is empty but code-registered "
            "schedule names exist, so the real deployment-check/run-evals cannot be told apart "
            "from case-created rows. Inspect and delete by hand: ScheduleManager(eval_db).delete(<id>)."
        )
    new = [
        schedule
        for schedule in schedules
        if schedule.id not in pre_run_ids and schedule.name not in _CODE_REGISTERED_SCHEDULES
    ]
    if len(new) > _MAX_SWEPT_SCHEDULES:
        raise RuntimeError(
            f"refusing to sweep {len(new)} schedules (cap {_MAX_SWEPT_SCHEDULES}): the pre-case "
            "snapshot looks incomplete, so these are not safely attributable to the case. "
            "Inspect them and delete by hand: ScheduleManager(eval_db).delete(<id>)."
        )
    for schedule in new:
        manager.delete(schedule.id)


def snapshot_builder_state() -> dict[str, Any]:
    """`setup` hook for Studio-builder cases: Studio component ids, schedule ids, and
    learning/note state — the builder carries the shared per-user profile/memory
    stores, so a run can write learnings as well as components and schedules."""
    return {
        "component_ids": snapshot_component_ids(),
        "schedule_ids": snapshot_schedule_ids(),
        "learning_state": snapshot_learning_state(),
    }


def delete_new_builder_state(pre_run: dict[str, Any]) -> None:
    """Hard-deletes components, schedules, and learning/note rows that did not exist
    before the case ran."""
    # Any sweep can refuse (see the caps) or hit a transient DB error; run each
    # regardless of how the others went, so one failure never strands another's rows.
    try:
        delete_new_components(pre_run["component_ids"])
    finally:
        try:
            delete_new_schedules(pre_run["schedule_ids"])
        finally:
            delete_new_learning_state(pre_run["learning_state"], _MAX_SWEPT_LEARNINGS)


async def cleanup_new_builder_state(pre_run: dict[str, Any], result: CaseResult) -> None:
    """`teardown` hook for builder cases: sweeps new components, schedules, and learning
    rows alike. The runner invokes it on pass, fail, error, and timeout alike."""
    await _let_inflight_writes_land(result)
    await asyncio.to_thread(delete_new_builder_state, pre_run)


BUILDER_HOOKS: dict[str, Any] = {"setup": snapshot_builder_state, "teardown": cleanup_new_builder_state}
LEARNING_HOOKS: dict[str, Any] = {"setup": snapshot_learning_state, "teardown": cleanup_new_learning_state}
