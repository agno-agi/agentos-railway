---
name: eval-and-improve
description: Evaluate and improve an existing AgentOS agent or team. Repair failing eval cases, or explore behavior by generating simulated user scenarios from instructions and sanitized usage, running probes, inspecting evidence and iterating within a bounded budget. Use for failing evals, autonomous hardening or simulation-driven improvement. Use create-evals for coverage authoring alone and extend-agent for a requested new capability.
---

# Eval and Improve

Choose the mode from the user's request; do not ask them to supply test cases for hardening.

- **Repair:** reproduce and diagnose existing failing cases, then fix the responsible behavior.
- **Explore:** generate realistic user scenarios, probe the agent, adapt follow-up scenarios
  to observed failures, improve it, and retain useful regression cases. This preserves the
  exploratory workflow formerly provided by `improve-agent`.

Both modes use [evals/cases.py](../../../evals/cases.py) and
[evals/__main__.py](../../../evals/__main__.py), with Agno's `Case`, `criteria` and
`expected_tool_calls`. Explore mode simulates user requests; the agent, tools and database
are real unless explicitly substituted. Do not describe these probes as a side-effect-free
simulator, a separate simulator agent, or proof of production behavior.

## 1. Establish the target and execution context

Read [AGENTS.md](../../../AGENTS.md), inspect `git status`, and locate the target's
declaration or published Studio configuration. Infer the target from the request when clear.
Capture its promised behavior, tools, model and existing coverage. Confirm the installed
Agno version matches `pyproject.toml` before relying on its APIs.

Use the project venv and configured PostgreSQL database. The CLI loads `.env` and defaults
to `dev` unless configured otherwise. It imports the application but does not start its API
or scheduler. Even `--help` and `--list` need PostgreSQL because knowledge storage initializes
on import. Do not start an API container just to run native agent/team cases.

Runs and judge calls cost money; sessions and results persist. State the selected cases or
small initial scenario batch and honor the user's budget. Use unique fixture users and owned
resources for mutations; a unique user does not isolate global tools or external services.
Do not run externally mutating scenarios unless their effects are authorized and contained.
Never sweep database rows or delete historical sessions, notes, schedules or Company records.

The built-in Case contract targets native Agno agents and teams. For Claude/Codex engineers,
workflows or HTTP/Company execution, verify support before choosing a runner; do not force an
unsupported target into Case or add an adapter here. Report the unsupported verification path
and route a specific change through [extend-agent](../extend-agent/SKILL.md).

Before cases that use MCP, inspect `evals/__main__.py`: it currently collects MCP tools
from OS Manager. Ensure the target's required MCP tools are connected in the eval loop;
API-side connections do not carry into a separate CLI process. Use the pinned framework
collection helpers in the existing entrypoint when additional target tools are needed.

## 2. Repair existing cases

Select the named failure first. Inspect available names/tags before choosing a wider run:

```sh
source .venv/bin/activate
python -m evals --tag smoke --list
python -m evals --name <case> --json-output tmp/eval-repair-before.json
```

Read the response, tool results, run status and judge reason. Classify the failure before
editing: incorrect expectation, application behavior, missing data/tool, infrastructure,
framework behavior or judge variance. A timeout, auth error or unavailable MCP server is not
evidence that the agent's instructions need strengthening.

## 3. Explore with simulated user scenarios

Review eval history in [os.agno.com](https://os.agno.com/?ref=railway-template).
Read the target's instructions and sample recent sessions and eval history read-only, using
the configured environment and `get_postgres_db()`. Sanitize private details before turning
usage into fixtures. Recorded answers supply scenarios, never the expected answer. With no
history, derive scenarios from the stated job and tool contracts.

Start with a small batch, typically 4–6 scenarios: a normal request, an ambiguous request,
a missing-evidence/refusal case, a tool-selection case and a relevant adversarial input.
For each, write the user goal, input, expected behavior and evidence needed to judge it.
Do not invent a new product requirement and then label its absence a failure.

Add uniquely named exploratory `Case` entries to `evals/cases.py`, preserving existing cases,
with a campaign-specific tag, timeout and fixture `user_id`. Use a Team in `team=`, an Agent
in `agent=`, and choose `expected_tool_calls` only where a tool is required. Run via
`python -m evals --name <case> --json-output tmp/<case>.json`.

After inspecting a response, derive the next scenario from what happened: clarify an
ambiguous request, challenge an unsupported claim, vary a boundary condition, or exercise
the same capability with different wording. Test the revised agent against fresh variants
as well as the exact failure so it does not merely memorize a test phrasing.

For conversational behavior, execute one turn at a time with the same explicit fixture
`user_id` and `session_id` across that episode's cases. Inspect each answer before writing
the next user turn; verify history is configured on the target. Use new episode session IDs
for independent reruns. Use a new fixture user too when learned state would contaminate the
comparison; do not erase prior learning to reset a test. Replay the complete episode when
assessing a multi-turn fix, not just its last message.

Keep useful regression cases through [create-evals](../create-evals/SKILL.md). At wrap-up,
identify retained cases and remove only disposable case entries introduced in this campaign;
preserve pre-existing coverage, concurrent edits and all recorded run history. Do not add
a custom simulator service, scorer, isolation layer or cleanup hooks to the starter.

## 4. Judge and improve

Judge the observed behavior against the expectation, not answer length or tool count.
`expected_tool_calls` proves invocation; inspect returned payloads and persisted effects
when those matter. Additional calls are allowed by default. A read-only request in a case
does not enforce read-only execution. A successful HTTP response or fluent text alone is
not a behavioral pass.

Paused, errored and cancelled runs do not pass the built-in suite. If pausing for approval
was the expected behavior, record that distinction and the runner's limitation; do not
bypass approval or weaken the scenario to manufacture a passing score. Treat unstable
judge verdicts as uncertainty and inspect the rubric before repeating paid calls.

Change one relevant decision at a time in application-owned agents/teams or their existing
application configuration. This may include a necessary wiring change in `app/main.py`,
`app/registry.py` or `app/settings.py`; keep it specific to the demonstrated defect.
Preserve explicit model choices unless the user authorizes changing them. Correct a case
only when its expectation is demonstrably wrong; never remove a required assertion to pass.

OS Manager, Company Manager, their internal members and generic behavior are Agno-owned.
Do not patch framework files, weaken authorization, recreate internal agents, or add template
prompt overrides to compensate for a framework defect. Report the reproducer and boundary.
Database/schema, deployment and new-capability changes require their own requested scope.
For Studio components use supported edit/publish tools; do not shadow their IDs with files.

## 5. Re-run and stop

After a fix, rerun failed cases or complete episodes plus relevant passing regressions.
For explore mode, also run fresh scenario variants. Then run the applicable existing suite,
normally `python -m evals --tag smoke`; use other tags only if that coverage exists.
Direct evals import fresh code each invocation; they do not require an API restart.

Stop when the selected cases complete and pass, the user's budget is reached, or meaningful
progress requires a new decision. Default to at most five fix-and-reprobe iterations and
stop sooner when the same failure persists through three attempts at the same kind of fix.
An environmental block or framework defect is a reason to report evidence, not loop until
green. A broader campaign needs an explicit larger scope/budget from the user.

## 6. Report

Report the mode, scenarios generated, initial and final results, changes, retained coverage,
unresolved failures and limits. Distinguish existing-case passes, fresh-scenario passes,
environment failures and untested runtime paths. Record evidence in `tmp/VERIFY.md` without
private session content or credentials. Do not claim all behavior is reliable from a finite batch.

Link to [os.agno.com](https://os.agno.com/?ref=railway-template) when handing over saved eval results.
