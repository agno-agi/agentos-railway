---
name: create-evals
description: Author eval coverage for an agent in this AgentOS — map what the agent promises, mine real sessions and eval history from Postgres for scenarios, propose capabilities worth testing, then write, run, and audit Case entries in evals/cases.py. Use when the user wants evals created, coverage added, or an agent's behavior pinned down as tests. For failing suites or exploratory simulation-driven hardening, use eval-and-improve instead.
---

# Create Evals

> _Coding-agent workflow: run as `/create-evals` or by describing the task._

Turn what an agent promises into `Case` entries in [`evals/cases.py`](../../../evals/cases.py). The template's cases cover the reference components only; a user-built agent is invisible to the suite until this skill writes one. Failing suite → [`eval-and-improve`](../eval-and-improve/SKILL.md); agent needs hardening → [`eval-and-improve`](../eval-and-improve/SKILL.md).

Preconditions: configured PostgreSQL reachable, venv active (`source .venv/bin/activate`; `./scripts/venv_setup.sh` if missing), `.env` populated. Even CLI `--help`/`--list` imports application knowledge storage and requires PostgreSQL; no API server is needed for native agent/team cases.

**Be self-driving:** the repo and the database answer most questions. Ask the user only what they alone know — which jobs matter and which failures would hurt. One pick per exchange, recommendation first.

## 1. Pick the agent

The user's choice, or the least-covered component — almost always one of theirs. Source components have a file under `agents/` or `teams/`. Studio-built components have none: `Agent.load("<id>", db=get_postgres_db(), registry=registry, published_only=True)` (or `Team.load`) rehydrates the published config at import time; it returns `None` for an archived or unpublished component, and a `Case` with neither field set raises — guard the load or the whole suite fails at import. Workflows cannot be case targets.

Before cases that use MCP, inspect `evals/__main__.py`: it currently collects MCP tools
from OS Manager. Ensure the target's required MCP tools are connected in the eval loop;
API-side connections do not carry into a separate CLI process. Use the pinned framework
collection helpers in the existing entrypoint when additional target tools are needed.

## 2. Map what it promises

Read the file (or the published config: `get_postgres_db().get_config(component_id="<id>")["config"]`). Every "always", "never", "use X for Y" is a case. Note the tools for reliability assertions.

Run every case through `python -m evals`, which uses the application's `.env`,
database and workspace. Sessions and results persist. Do not mutate existing user
components as fixtures; mutating cases need explicitly owned fixtures.
Use Agno's built-in `criteria` and `expected_tool_calls`. Keep generic Agno behavior
in framework coverage; do not add custom scorers, isolation or cleanup machinery
to the starter by default.

## 3. Mine the platform

```python
from db import get_postgres_db
db = get_postgres_db()
sessions, _ = db.get_sessions(component_id="<agent-id>", limit=20, deserialize=False)
asks = [run["input"]["input_content"] for s in sessions for run in (s.get("runs") or []) if run.get("input")]
evals, _ = db.get_eval_runs(limit=20, deserialize=False)
```

Sanitize private details before using session content in fixtures. Real asks make useful inputs. A recorded answer is a scenario, never a golden answer — the rubric states the timeless shape of a correct answer (a version or date enters as "a current X with a source", never as the value). No sessions is fine: derive from `INSTRUCTIONS`.

## 4. Propose what to test

2–3 capabilities, each with a one-line scenario and what a pass proves; lead with the one closest to the core job or hit most in sessions. Skip what the suite already covers. One exchange.

## 5. Write the case

Inside `CASES` after the marker `# --- Your cases — authored by /create-evals ---` (add it if missing). Names must be unique across the file.

```python
Case(
    name="<agent>_<capability>",
    agent=<the_agent>,   # a Team goes in team= — nothing catches a team in agent=; it runs, misfiled
    input="<scenario>",
    tags=("<smoke|release|live>",),  # model calls; choose smoke, release or live deliberately
    timeout_seconds=90,
    user_id="<unique-fixture-user>",
    criteria="<specific, falsifiable>",
    expected_tool_calls=("<tool>",),
)
```

Pair answer criteria with `expected_tool_calls` when a tool is required.
Tool-call checks verify invocation, not successful payloads or persisted state;
inspect those when auditing a run rather than claiming the built-in check proves them.

Use unique fixture names and users. A fixture user does not isolate global tools or external services. External mutations (messages, files, third-party APIs) require authorization and containment or must stay outside the suite. Additional tool calls are allowed by default; a read-only prompt is not an execution restriction.

## 6. Run and audit

```bash
python -m evals --name <case>
```

Run through `python -m evals`; results persist in the application's database for the UI. Read both sides of the verdict: the response and tools fired, and `judge_reason` (`--json-output`). Repeat when a changed prompt, an unstable verdict or a specific reliability question justifies the extra calls. Replace vague criteria such as "compact" with observable expectations; investigate conflicting verdicts. If the agent, not the case, is wrong, say so — that's [`eval-and-improve`](../eval-and-improve/SKILL.md).

Loop to Step 4 or finish.

## 7. Hand over

New cases by name and tag, `git diff evals/cases.py`, suggested commit `eval(<agent>): …`. `smoke` cases run on demand through `python -m evals`; failures go to [`/eval-and-improve`](../eval-and-improve/SKILL.md).
