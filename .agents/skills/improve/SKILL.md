---
name: improve
description: Harden an existing AgentOS agent or team by finding weaknesses through realistic user simulations, diagnosing their causes, making targeted improvements and verifying more reliable behavior. Use for agent hardening, failing evals, simulation-driven improvement or turning useful scenarios into evals. Also support simulation-only requests. Use create-evals for coverage authoring alone and extend-agent for a specified capability change.
---

# Improve

Make the agent more reliable at its intended job. For an improvement or hardening request,
carry the work through finding weaknesses, diagnosing their causes, making focused fixes and
verifying the result. Simulations uncover failure modes; evals provide repeatable evidence
and can preserve useful regressions. Prioritize failures by their impact on the user's task.

Adapt this workflow to the request:

- **Harden the agent:** simulate realistic use, diagnose weaknesses, fix them and verify
  the fixes against the original failures, fresh variants and relevant regressions.
- **Investigate a failure:** reproduce an observed failure or failing eval and address its
  cause within the requested scope.
- **Run simulations only:** exercise behavior and report findings without requiring edits.
- **Save evals:** turn selected simulations into repeatable coverage using
  [create-evals](../create-evals/SKILL.md).

Infer the intended outcome from the request; clarify only when it materially changes the
work. A general hardening request includes targeted fixes, so do not stop at an analysis
report when those fixes are in scope and feasible. Retaining evals is optional unless
requested; recommend meaningful regression cases rather than saving every probe. Judge
success by more reliable behavior across scenarios, not just a higher eval score.

## Establish the target and execution context

Read [AGENTS.md](../../../AGENTS.md), inspect `git status`, and locate the target's
declaration or published Studio configuration. Capture its promised behavior, tools, model,
existing coverage and installed Agno version. Preserve explicit model choices.

Simulations supply user requests; the agent, tools and database are real unless explicitly
substituted. Runs and judge calls cost money, and sessions/results persist. State a small
initial batch and honor the user's budget. Use owned fixtures for mutations; unique fixture
users do not isolate global tools or external services. Externally mutating scenarios need
authorized, contained effects. Preserve historical sessions, notes, schedules and Company work.

Choose a supported execution path for the target. Native Agno agents and teams can use the
existing [eval CLI](../../../evals/__main__.py) and [cases](../../../evals/cases.py).
For external coding agents, workflows or HTTP/Company behavior, verify the runner supports that
path; do not force them into `Case` or add a template adapter. Exercise the actual path when
it matters to the question, and distinguish direct agent results from API/Company results.

The eval CLI uses the project venv, `.env` and PostgreSQL; it defaults to `dev` unless
configured otherwise. It imports the application without starting the API or scheduler.
Even `--help` and `--list` need PostgreSQL because knowledge storage initializes on import.
MCP connections in the API do not carry into the CLI: check the existing entrypoint connects
the target's required tools using the pinned framework's helpers.
For custom native probes, load this same environment explicitly, for example
`uv run --no-project --env-file .env .venv/bin/python tmp/probe.py`.

## Find weaknesses with simulations

Inspect instructions and, when relevant, recent sessions and eval history read-only in the
configured environment or [os.agno.com](https://os.agno.com/?ref=railway-template).
Sanitize private details before making fixtures. Recorded answers suggest scenarios; they
are not ground truth. Without history, derive scenarios from the agent's job and tool contracts.

Start with a small batch, typically 4–6 scenarios, covering relevant normal requests,
ambiguity, missing evidence, tool selection and adversarial inputs. For each, identify the
user goal, input, expected behavior and evidence needed to judge it. Do not invent a product
requirement and label its absence a failure.

Run through the selected supported path. Simulation probes do not have to become committed
evals. If the existing eval runner helps, use uniquely named temporary `Case` entries with a
campaign tag and fixture user, preserving existing cases. Use `agent=` or `team=` correctly
and require tool calls only where they are part of the behavior being tested.

Adapt follow-up scenarios to observed answers: clarify ambiguity, challenge an unsupported
claim or vary a boundary condition. For conversation tests, keep the same explicit fixture
`user_id` and `session_id` across an episode and inspect each answer before writing the next
turn. Verify history is configured. Rerun whole episodes with fresh session IDs; use fresh
fixture users when learned state could contaminate comparisons, without deleting prior state.

## Diagnose from evidence

For an existing failing eval, reproduce the selected case before broadening the run:

```sh
source .venv/bin/activate
python -m evals --tag smoke --list
python -m evals --name <case> --json-output tmp/eval-before.json
```

Inspect responses, tool payloads, persisted effects, run status and judge reasons. Separate
incorrect expectations, application defects, missing data/tools, infrastructure failures,
framework behavior and judge variance. If tool arguments contradict the intended contract,
inspect the model-facing tool schema, including required fields and nullable types; Python
annotations alone do not prove what the model receives. Authentication errors or timeouts do not establish
that instructions need strengthening. HTTP success and tool invocation alone do not prove
the requested outcome; a read-only prompt does not enforce read-only execution.

Paused, errored and cancelled runs do not pass the built-in suite. When approval is the
expected behavior, report the correct pause and the runner's limitation; do not bypass
approval or weaken expectations to obtain a passing score. Treat unstable verdicts as
uncertainty and inspect the rubric before spending more calls.

## Make and verify targeted improvements

When changes are in scope, save the baseline first: component version/commit, model/settings,
scenario and rubric, relevant knowledge versions, observed results and run/eval IDs. Change
the responsible layer: knowledge, instructions, tools, code or workflow. Keep each change
specific to the evidence, and correct expectations only when they are demonstrably wrong.

OS Manager, Company Manager, their internal members and generic behavior belong to Agno.
For a framework defect, report the reproducer and required upstream change; do not recreate
internal agents, weaken authorization or add template prompt workarounds. Database/schema,
deployment and new-capability work must fit the user's scope. For Studio components, use
supported edit/publish tools rather than shadowing their IDs with files.

Compare baseline and candidate on the same scenarios with fresh histories, plus fresh
variants and relevant existing regressions. Replay complete multi-turn episodes. Use the
applicable existing suite when behavior changes warrant it; direct eval invocations import
fresh code and do not need an API restart. Keep failed candidates and unresolved cases in
the evidence instead of presenting only successes.

For hardening, stop when the selected weaknesses are addressed and verified, the budget
is reached or a concrete blocker requires a new decision. For simulation-only or diagnostic
requests, stop when the requested investigation is complete. Do not keep changing prompts to make a suite green.
For open-ended hardening, start with one small batch and a targeted candidate; extend the
work only when the findings and remaining budget justify it.

## Retain useful evals and report

When the user wants simulations saved as evals, select stable, meaningful scenarios and use
[create-evals](../create-evals/SKILL.md) to add `Case` entries with observable `criteria` and
appropriate `expected_tool_calls`. Preserve existing coverage. Remove only disposable case
entries introduced by this hardening pass, keeping all recorded run history and concurrent edits.
Do not introduce a custom simulator service, scorer or cleanup framework into the starter.

Report what was requested, scenarios tried, findings, changes if any, retained evals if any,
and unresolved questions. Separate observed improvement from untested paths and uncertainty.
Record local checks in `tmp/VERIFY.md` without private transcripts or secrets. Keep essential
before/after evidence with the change in the PR and saved eval records; no dated report needs
to ship in the template. A measured local improvement does not establish hosted reliability
or authorize deployment, automatic adoption or unrelated Company task execution.
