---
name: create-evals
description: Author eval coverage for an agent in this AgentOS — map what the agent promises, mine real sessions and eval history from Postgres for scenarios, propose capabilities worth testing, then write, run, and audit Case entries in evals/cases.py. Use when the user wants evals created, coverage added, or an agent's behavior pinned down as tests. To repair a failing suite, use eval-and-improve instead.
---

# Create Evals

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/create-evals`) or describe the task and it triggers automatically._

You're giving an agent eval coverage: turning what it promises into `Case` entries in [`evals/cases.py`](../../../evals/cases.py). The template's own cases cover the reference components only — an agent the user built is invisible to the suite until this skill writes one.

This is the **authoring** skill. If the suite is failing and needs diagnosis, that's [`eval-and-improve`](../eval-and-improve/SKILL.md); if the agent itself needs hardening against its instructions, that's [`improve-agent`](../improve-agent/SKILL.md). Preconditions match eval-and-improve's Step 0: Postgres on 5432, venv active, `.env` populated.

**Be self-driving:** the repo and the database answer most questions — read them instead of asking. The user's judgment is for what only they know: which jobs matter most and which failures would hurt. One pick per exchange, recommendation first.

## 1. Pick the agent

If the user named one, that's the pick. Otherwise compare what this platform actually runs against the cases already in `evals/cases.py` and recommend the least covered — the reference components come covered, so the answer is almost always one of the user's own. Two lanes hold components, and only one of them has files:

- **Source components** — a file under `agents/` (or `teams/`), imported into the case by name. Everything the template ships is here.
- **Studio-built components** — built at runtime through Platform Builder, so there is no file to read: they live in the Studio catalog (`eval_db.list_components()`, or ask Platform Builder to list them). `Agent.load("<id>", db=eval_db, registry=registry, published_only=True)` rehydrates the published config into a real `Agent` a case can run (`registry` from `app.registry`, so its tools and model resolve); `Team.load` does the same for a team. The load happens when `evals/cases.py` is imported, so the case tests whatever was published at that moment. Two consequences: `load` returns `None` for a component that was archived or never published, and a `Case` with neither field set raises — so an archived component takes the **whole suite** down at import rather than failing its own case. Guard the load and say so in a comment, or delete the case when the component goes. And the case is only as reachable as the database: on a machine with a different Postgres, that component doesn't exist. A workflow can't be a case target at all: `Case` takes an agent or a team.

Name your pick and why in one line; roll on unless they object.

## 2. Map what it promises

Read the agent's file — or, for a Studio-built component, its published config (Platform Builder's `get_component`, or `eval_db.get_config(component_id="<id>")["config"]`). Its instructions are a list of testable claims: every "always cite", "never fabricate", "use X for Y" is a case waiting to be written. Note the tools (reliability assertions), the model, and the pattern.

The check that decides the hooks: **can this run reach the ungated create/edit/publish Studio tools?** Look for `StudioTools` in the component's tools, directly or transitively through team members; in this repo that's `platform-builder`, and the `agno` team through it. For the builder itself the answer is always yes, so every builder case carries the builder hooks (shown in Step 5). For a team that merely *fronts* a builder, the prompt decides: a case whose ask is one delegation away from a build takes the builder hooks (`agno_dispatch_honest_roster` does — "have X run its job" against a name nobody built invites exactly that), and a case that only files or recalls takes the learning hooks (`agno_captures_project_fact` does). When the two readings are close, take the builder hooks — they are a strict superset: components, schedules, *and* learning state.

A second check: does the component carry **learning stores** (`learning=` — all four reference components do, and so does any Studio-built component with learning wired, by `learning_name` or `enable_learning`), or the **`shared_notes`** toolkit (it writes the same shared notebook the hooks snapshot and sweep)? Those cases take the learning hooks.

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

Real session inputs make the best case inputs. **A recorded answer is a scenario, never a golden answer**: the agent may have been wrong that day. The rubric states the timeless shape of a correct answer — versions, dates, counts, and today's news enter it as "a current X with a source", never as the value itself. A fresh platform with no sessions is fine: derive scenarios from `INSTRUCTIONS` instead.

## 4. Propose what to test

Offer 2–3 capabilities, grounded in the map and the mining: for each, a one-line scenario and what a pass proves. Lead with a recommendation — the capability closest to the agent's core job, or the one real sessions hit most. Skip proposals the suite already covers. One exchange: they pick, or their own words redirect you.

## 5. Write the case

Inside the `CASES` tuple of [`evals/cases.py`](../../../evals/cases.py) — after the marker the file already carries near the end of the tuple, `# --- Your cases — authored by /create-evals ---` (add it if missing). Case names must be unique across the file (grep for yours first — duplicates run without error and muddy the shared history). The shape:

```python
Case(
    name="<agent>_<capability>",
    agent=<the_agent>,   # a Team goes in team=<the_team> instead — separate fields, exactly one set
    input="<scenario — a real session ask, or one derived from INSTRUCTIONS>",
    tags=("<smoke|release|live>",),  # smoke rides the schedule — deterministic only
    timeout_seconds=90,
    criteria="<what a correct answer contains — specific, falsifiable>",
    expected_tool_calls=("<tool>",),
    # Reaches the ungated create/edit/publish Studio tools (Step 2)? This line is
    # mandatory (defined in evals/hooks.py):
    # **BUILDER_HOOKS,
    # Not a builder, but carries learning stores (`learning=` — platform-manager,
    # platform-engineer) or the `shared_notes` toolkit (Step 2)?
    # **LEARNING_HOOKS,
)
```

**Put a team in `team=`, never in `agent=`.** Nothing catches the mistake: `Case` only checks that exactly one is set, mypy sees `Case` as `Any` (`agno.eval` resolves it through a module-level `__getattr__`), and a team in `agent=` runs and passes — misfiled, with the team's id under `agent_id` and `team_id` null in `--json-output` and `--list`, and run errors labelled `agent:`.

**Pair the judge and the reliability check whenever the capability involves a tool**: `expected_tool_calls` proves the work happened, the rubric proves the answer used it. (If a tool's name depends on env — keyed SDK vs keyless fallback — mirror the file's existing conditional, like `_WEB_TOOL`.) Write criteria falsifiable ("cites at least one real URL from the fetched page"), not vibes ("gives a good answer") — and ask of every rubric: **could a stock model with no tools and none of this agent's instructions pass it?** If yes, the case tests nothing; tie the criteria to what only fresh tool output or this agent's `INSTRUCTIONS` can supply (for chat-only agents: scope, refusals, format, the rules they were given). Tags by cost and determinism: `smoke` for fast, deterministic checks — these ride the run-evals schedule; `release` for broader pre-release confidence; `live` when correctness depends on today's web — and live never shares a tag with smoke.

Two containment rules beyond the hooks. **Name every fixture something no real team would have on file** (`Wilhelmina Ashgrove-Petrov`, `Quillhawk-Meridian`, `Zephyrium QALM-9` are the house style): the hooks diff on row identity, so they delete a row the case *created* but cannot undo an edit *inside* a row that already existed — a distinctive name is what keeps the case from merging into somebody's real entity or note. And any other tool that mutates external state (messages, files, third-party APIs) needs its own containment — a scoped test target, a teardown, or don't write the case.

## 6. Run it, then audit both sides

```bash
python -m evals --name <case>
```

Check you are the only writer before the first run: the hooks sweep by snapshot diff, so anything that lands in the shared stores while the case is running reads as new and gets deleted — including a note or an entity a teammate filed through Agno in the same window.

Read both sides before trusting the verdict, pass or fail:

- **The agent's side:** the actual response, and which tools fired.
- **The judge's side:** its stated reason (`--json-output` carries `judge_reason`).

A case earns its place when a pass is *earned* — right answer, tools fired, rubric only satisfiable by real work — and a fail would be *diagnosable* from the judge's reason. Run the case at least twice (three times when the criteria lean on judgment words like "compact" or "clear") — a verdict that flips between identical runs means the rubric, not the agent, is undecided. If the audit shows the agent (not the case) is wrong, say so — fixing it is [`improve-agent`](../improve-agent/SKILL.md)'s job.

Then loop to Step 4 for the next capability, or finish.

## 7. Hand over

Close with what changed: the new cases by name and tag, `git diff evals/cases.py`, a suggested commit message (`eval(<agent>): <what's covered now>`). Then the watch: `smoke`-tagged cases run on the run-evals schedule, results land in eval history at os.agno.com, and when a scheduled run goes red, [`/eval-and-improve`](../eval-and-improve/SKILL.md) picks it up from there.

The schedule ships disabled, so enabling it is the user's call — hand it over with the only-writer condition attached (AGENTS.md, Scheduler: an unattended run's teardown sweeps whatever was filed during the case window).
