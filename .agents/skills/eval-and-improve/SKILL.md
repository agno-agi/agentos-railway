---
name: eval-and-improve
description: Run the eval suite (python -m evals), diagnose every failure, fix what's in scope, and loop until all cases pass. Use when evals are failing — including overnight run-evals schedule failures — or when the user wants to run, diagnose, or repair the eval suite. To author new coverage, use create-evals instead.
---

# Eval and Improve

> _Coding-agent workflow: run as `/eval-and-improve` or by describing the task._

Run the suite, diagnose every failure, fix what's in scope, stop when green. Cases live in [`evals/cases.py`](../../../evals/cases.py) (`agno.eval.Case`), the setup/teardown sweeps in [`evals/hooks.py`](../../../evals/hooks.py), the entrypoint in [`evals/__main__.py`](../../../evals/__main__.py). Each case uses an LLM judge (`criteria`), a tool-call assertion (`expected_tool_calls`), and/or a deterministic `scorer`.

## 0. Preconditions

- Postgres on 5432 (`nc -z localhost 5432`; else `docker compose up -d agentos-db`).
- Venv active (`source .venv/bin/activate`; `./scripts/venv_setup.sh` if missing). No server needed — cases import the components directly.
- `.env` has `OPENAI_API_KEY` (and `PARALLEL_API_KEY` if you use one — it pins Agno's expected web tool name at import). Worktrees don't inherit `.env`.

## 1. Run

```bash
python -m evals --tag smoke            # fast template checks
python -m evals --tag release          # broader pre-release checks
python -m evals --tag live             # current web/source checks
python -m evals --name <case>          # one case
python -m evals --tag smoke --list     # what a selector picks, without running
python -m evals --json-output out.json # machine-readable (carries judge_reason)
python -m evals -v                     # stream the runs
```

Exit 0 = all passed. **Be the only writer:** teardowns sweep by snapshot diff, so a note or entity a teammate files during a case gets deleted. Coming from a scheduled failure? Find the case in eval history (`db.get_eval_runs()`, os.agno.com, or Platform Manager) and reproduce it with `--name` first; one that won't reproduce is usually environment. Stderr noise at the end of a run (`Event loop is closed`, httpx timeouts) is harmless.

## 2. Diagnose

| Symptom | Likely cause | Fix |
|---|---|---|
| Judge: right answer, missing X | Instructions don't push for X | `agents/<slug>.py` — tighten the rule |
| Judge: fabricated | Should have said it didn't know | Add a "say so plainly" rule |
| Reliability: missing tool | Routing rule weak, or the case too narrow | Strengthen the rule, or broaden `expected_tool_calls` |
| Reliability: additional tool with `allow_additional_tool_calls=False` | Agent fanned out | Tighten instructions or allow it |
| Agno web tool name mismatch (`parallel_search` ↔ `web_search`) | `PARALLEL_API_KEY` differs between `.env` and shell | Sync and re-run |
| Flips PASS/FAIL across runs, no change | Judge variance | Re-run 2–3×; still flipping → make `criteria` more falsifiable |
| Fails in the suite, passes alone | Transient flake / 429 | Re-run alone, then the suite; persistent 429s → back off |
| Many fail at once | Broad regression (model, MCP down, tool removed) | Find the root cause; no prompt edits |
| `run paused awaiting user input` | Hit a HITL gate (Builder archive/delete) — never graded | Keep the case input on the ungated side |
| `cleanup:` in the error | A teardown couldn't delete what the case created | Hard-delete by id (`eval_db.delete_component(id, hard_delete=True)`, `ScheduleManager(eval_db).delete(id)`, `eval_db.delete_learning(id)`, `notes.delete(path)`); don't touch the agent or case |
| `refusing to sweep …` | A guard tripped: rows predate the snapshot, or more rows than a case plausibly creates | Don't loosen the guard; inspect, delete the case's rows by hand, re-run |

**Never weaken a case to make it green.** Edit a case only when the assertion was wrong. Read both sides — the response and `judge_reason` — before deciding which. When you do edit one, make sure the green is earned: the tool fired, and the rubric can't be met by a shortcut.

## 3. Scope

In: `agents/<slug>.py` / `teams/lead.py` (instructions, tools, model); `evals/cases.py` when an assertion was wrong; a one-line `app/main.py` flip if a case needs it. Out (flag, don't do): removing cases, editing `db/` or `app/` to pass, editing agno. Fast iteration on agent quality is [`improve-agent`](../improve-agent/SKILL.md); a user-driven change is [`extend-agent`](../extend-agent/SKILL.md).

## 4. Re-run and stop

`python -m evals --name <case>` after each fix; then `python -m evals --tag release`. Stop when it exits 0 **and** prints the `Eval Summary` — an aborted run is inconclusive.

## 5. Add a case (if needed)

When a diagnosis reveals a missing assertion, add it to `evals/cases.py`; coverage work belongs to [`create-evals`](../create-evals/SKILL.md).

```python
Case(
    name="<short_id>",
    agent=<the_agent>,           # a Team goes in team= — exactly one of the two
    input="<prompt>",
    tags=("release",),           # smoke = fast core checks; live = depends on today's web
    criteria="<rubric>",
    expected_tool_calls=("<tool_name>",),
    **BUILDER_HOOKS,             # any case that can reach the ungated Studio tools; else **LEARNING_HOOKS for a learning component
)
```

Only a completed run is graded; a paused, cancelled, or errored run fails with that status. Hooks diff on row identity: they delete rows a case created and cannot undo an edit inside an existing row — fixtures use names no real team has.

## 6. Over time

Cases log to Postgres (`db=eval_db`); history shows at os.agno.com. The daily [`workflows/run_evals.py`](../../../workflows/run_evals.py) schedule ships disabled — enabling it carries the only-writer rule into an unattended run; name an hour nobody is on the platform, or leave it off on a busy one.
