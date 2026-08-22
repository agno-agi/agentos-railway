---
name: create-evals
description: Author eval coverage for an agent in this AgentOS — map what the agent promises, mine real sessions and eval history from Postgres for scenarios, propose capabilities worth testing, then write, run, and audit Case entries in evals/cases.py. Use when the user wants evals created, coverage added, or an agent's behavior pinned down as tests. To repair a failing suite, use eval-and-improve instead.
---

# Create Evals

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/create-evals`) or describe the task and it triggers automatically._

You're giving an agent eval coverage: turning what it promises into `Case` entries in [`evals/cases.py`](../../../evals/cases.py) that catch regressions from now on. The suite only watches what someone wrote down — the template ships cases for its reference agents, but a user's own agents are invisible to it until this skill runs. Once a case is tagged `smoke`, the run-evals schedule covers it on every scheduled run, and the eval history lands in Postgres where the AgentOS UI and Platform Manager can see it. That's the payoff: an agent built this morning is being watched by tonight.

This is the **authoring** skill. If the suite is failing and needs diagnosis, that's [`eval-and-improve`](../eval-and-improve/SKILL.md); if the agent itself needs hardening against its instructions, that's [`improve-agent`](../improve-agent/SKILL.md). Preconditions match eval-and-improve's Step 0: Postgres on 5432, venv active, `.env` populated.

**Be self-driving:** the repo and the database answer most questions — read them instead of asking. The user's judgment is for what only they know: which jobs matter most and which failures would hurt. One pick per exchange, recommendation first.

## 1. Pick the agent

If the user named one, that's the pick. Otherwise compare `agents/` against the cases in `evals/cases.py` and recommend the agent with the least coverage — usually the one they built themselves, since template agents come covered. Name your pick and why in one line; roll on unless they object.

## 2. Map what it promises

Read the agent's file. Its `INSTRUCTIONS` are a list of testable claims — every "always cite", "never fabricate", "use X for Y" is a case waiting to be written. Note the tools (reliability assertions), the model, and the pattern. One check has teeth: **is this a studio-builder?** Detect it operationally — `StudioTools` in the component's tools, directly or transitively through team members; in this repo that's `platform-builder` and the `agno` team. Builder cases write real DB rows — components, schedules, learnings — so they carry the builder hooks (shown in Step 5), no exceptions; when in doubt, add the hooks anyway — they're free on a run that creates nothing. A second check: does the agent carry **learning stores** (`learning=` — all four reference components do, and so does any Studio-built component wired to a registered machine with `learning_name`)? Those cases take the learning hooks; the builder hooks already include them.

## 3. Mine the platform

The platform records how the agent actually gets used — read it before inventing scenarios:

```python
from db import get_postgres_db
db = get_postgres_db()
# deserialize=False keeps the (rows, total) tuple shape and returns plain dicts
sessions, _ = db.get_sessions(component_id="<agent-id>", limit=20, deserialize=False)
asks = [run["input"]["input_content"] for s in sessions for run in (s.get("runs") or []) if run.get("input")]
evals, _ = db.get_eval_runs(limit=20, deserialize=False)   # what's already covered, what's flaky
```

Real session inputs make the best case inputs — they're what the agent will face again. Two rules: **a recorded answer is a scenario, never a golden answer** (the agent may have been wrong that day; the rubric states what a correct answer looks like, not what yesterday's said — and keep only the timeless shape of correctness: versions, dates, counts, and today's news enter the rubric as "a current X with a source", never as the value itself), and a fresh platform with no sessions is fine — derive scenarios from `INSTRUCTIONS` instead, the same fallback improve-agent's probes use.

## 4. Propose what to test

Offer 2–3 capabilities, grounded in the map and the mining: for each, a one-line scenario and what a pass proves. Lead with a recommendation — the capability closest to the agent's core job, or the one real sessions hit most. Skip proposals the suite already covers. One exchange: they pick, or their own words redirect you.

## 5. Write the case

Inside the `CASES` tuple of [`evals/cases.py`](../../../evals/cases.py), before its closing paren — add the marker comment there if this is the first: `# --- Your cases — authored by /create-evals ---`. Case names must be unique across the file (grep for yours first — duplicates run without error and muddy the shared history). The shape:

```python
Case(
    name="<agent>_<capability>",
    agent=<the_agent>,
    input="<scenario — a real session ask, or one derived from INSTRUCTIONS>",
    tags=("<smoke|release|live>",),  # smoke rides the schedule — deterministic only
    timeout_seconds=90,
    criteria="<what a correct answer contains — specific, falsifiable>",
    expected_tool_calls=("<tool>",),
    # Studio-builder component (Step 2)? These two lines are mandatory — both live in this file:
    # setup=snapshot_builder_state,
    # teardown=cleanup_new_builder_state,
    # Not a builder, but carries learning stores (`learning=` — platform-manager, platform-engineer)?
    # setup=snapshot_learning_state,
    # teardown=cleanup_new_learning_state,
)
```

The judge and the reliability check answer different questions — **pair them whenever the capability involves a tool**. A rubric alone is gameable: an agent that answers from stale memory without searching can read *correct*; `expected_tool_calls` proves the work happened, the rubric proves the answer used it. (If a tool's name depends on env — keyed SDK vs keyless fallback — mirror the file's existing conditional, like `_WEB_TOOL`.) Write criteria falsifiable ("cites at least one real URL from the fetched page"), not vibes ("gives a good answer") — and ask of every rubric: **could a stock model with no tools and none of this agent's instructions pass it?** If yes, the case tests nothing; tie the criteria to what only fresh tool output or this agent's `INSTRUCTIONS` can supply (for chat-only agents: scope, refusals, format, the rules they were given). Tags by cost and determinism: `smoke` for fast, deterministic checks — these ride the run-evals schedule; `release` for broader pre-release confidence; `live` when correctness depends on today's web. If the right answer can change with the outside world, the case is `live` — and live never shares a tag with smoke.

Two containment rules: studio-builder cases get the snapshot hooks, every time — that's also why build prompts that are unsafe as ad-hoc smoke tests are safe here. And any other tool that mutates external state (messages, files, third-party APIs) needs its own containment — a scoped test target, a teardown, or don't write the case.

## 6. Run it, then audit both sides

```bash
python -m evals --name <case>
```

Don't stop at the verdict — read both sides before trusting it, pass or fail:

- **The agent's side:** the actual response, and which tools fired.
- **The judge's side:** its stated reason (`--json-output` carries `judge_reason`).

A case earns its place when a pass is *earned* — right answer, tools fired, rubric only satisfiable by real work — and a fail would be *diagnosable* from the judge's reason. A pass earned once isn't earned: run the case at least twice (three times when the criteria lean on judgment words like "compact" or "clear") — a verdict that flips between identical runs means the rubric, not the agent, is undecided. First rubrics rarely survive this audit; expect one tightening round. If the audit shows the agent (not the case) is wrong, say so — fixing it is [`improve-agent`](../improve-agent/SKILL.md)'s job, and the failing case you just wrote is exactly the regression test that proves the fix.

Then loop to Step 4 for the next capability, or finish.

## 7. Hand over

Close with what changed and the loop the user now owns: the new cases by name and tag, `git diff evals/cases.py`, a suggested commit message (`eval(<agent>): <what's covered now>`). Then the watch: `smoke`-tagged cases run on the run-evals schedule — enable it from the AgentOS UI if they haven't — results land in eval history at os.agno.com, and when a scheduled run goes red, [`/eval-and-improve`](../eval-and-improve/SKILL.md) picks it up from there.
