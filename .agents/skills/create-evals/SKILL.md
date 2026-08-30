---
name: create-evals
description: Author eval coverage for an agent in this AgentOS — map what the agent promises, mine real sessions and eval history from Postgres for scenarios, propose capabilities worth testing, then write, run, and audit Case entries in evals/cases.py. Use when the user wants evals created, coverage added, or an agent's behavior pinned down as tests. To repair a failing suite, use eval-and-improve instead.
---

# Create Evals

> _Coding-agent workflow: run as `/create-evals` or by describing the task._

Turn what an agent promises into `Case` entries in [`evals/cases.py`](../../../evals/cases.py). The template's cases cover the reference components only; a user-built agent is invisible to the suite until this skill writes one. Failing suite → [`eval-and-improve`](../eval-and-improve/SKILL.md); agent needs hardening → [`improve-agent`](../improve-agent/SKILL.md).

Preconditions: Postgres on 5432, venv active (`source .venv/bin/activate`; `./scripts/venv_setup.sh` if missing), `.env` populated.

**Be self-driving:** the repo and the database answer most questions. Ask the user only what they alone know — which jobs matter and which failures would hurt. One pick per exchange, recommendation first.

## 1. Pick the agent

The user's choice, or the least-covered component — almost always one of theirs. Source components have a file under `agents/` or `teams/`. Studio-built components have none: `Agent.load("<id>", db=eval_db, registry=registry, published_only=True)` (or `Team.load`) rehydrates the published config at import time; it returns `None` for an archived or unpublished component, and a `Case` with neither field set raises — guard the load or the whole suite fails at import. Workflows cannot be case targets.

## 2. Map what it promises

Read the file (or the published config: `eval_db.get_config(component_id="<id>")["config"]`). Every "always", "never", "use X for Y" is a case. Note the tools for reliability assertions.

Two checks decide the hooks:

- **Can the run reach the ungated create/edit/publish Studio tools?** `StudioTools` directly or through a team member — `platform-builder` always, and an `agno` case one delegation from a build. Those take `**BUILDER_HOOKS`.
- **Does it carry learning stores (`learning=`) or the `shared_notes` toolkit?** Those take `**LEARNING_HOOKS`. Builder hooks are a strict superset; when in doubt, take them.

## 3. Mine the platform

```python
from db import get_postgres_db
db = get_postgres_db()
sessions, _ = db.get_sessions(component_id="<agent-id>", limit=20, deserialize=False)
asks = [run["input"]["input_content"] for s in sessions for run in (s.get("runs") or []) if run.get("input")]
evals, _ = db.get_eval_runs(limit=20, deserialize=False)
```

Real asks make the best inputs. A recorded answer is a scenario, never a golden answer — the rubric states the timeless shape of a correct answer (a version or date enters as "a current X with a source", never as the value). No sessions is fine: derive from `INSTRUCTIONS`.

## 4. Propose what to test

2–3 capabilities, each with a one-line scenario and what a pass proves; lead with the one closest to the core job or hit most in sessions. Skip what the suite already covers. One exchange.

## 5. Write the case

Inside `CASES` after the marker `# --- Your cases — authored by /create-evals ---` (add it if missing). Names must be unique across the file.

```python
Case(
    name="<agent>_<capability>",
    agent=<the_agent>,   # a Team goes in team= — nothing catches a team in agent=; it runs, misfiled
    input="<scenario>",
    tags=("<smoke|release|live>",),  # smoke rides the schedule — deterministic only; live never shares with smoke
    timeout_seconds=90,
    criteria="<specific, falsifiable>",
    expected_tool_calls=("<tool>",),
    **BUILDER_HOOKS,   # or **LEARNING_HOOKS — see Step 2; from evals/hooks.py
)
```

Pair the judge with `expected_tool_calls` whenever a tool is involved. Ask of every rubric: **could a stock model with no tools and none of these instructions pass it?** If yes, it tests nothing. Env-dependent tool names mirror the file's `_WEB_TOOL` conditional.

Fixtures must be names no real team would have on file (`Wilhelmina Ashgrove-Petrov`, `Quillhawk-Meridian`): the hooks delete rows a case *created* and cannot undo an edit inside an existing row. A tool that mutates external state (messages, files, third-party APIs) needs its own containment or no case.

## 6. Run and audit

```bash
python -m evals --name <case>
```

Be the only writer — the hooks sweep by snapshot diff, so a teammate's note filed during the run gets deleted. Read both sides of the verdict: the response and tools fired, and `judge_reason` (`--json-output`). Run at least twice (three times for judgment words like "compact"); a flipping verdict means the rubric is undecided. If the agent, not the case, is wrong, say so — that's [`improve-agent`](../improve-agent/SKILL.md).

Loop to Step 4 or finish.

## 7. Hand over

New cases by name and tag, `git diff evals/cases.py`, suggested commit `eval(<agent>): …`. `smoke` cases ride the run-evals schedule (ships disabled; enabling is the user's call, with the only-writer condition attached); failures go to [`/eval-and-improve`](../eval-and-improve/SKILL.md).
