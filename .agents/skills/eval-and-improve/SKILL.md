---
name: eval-and-improve
description: Run the eval suite (python -m evals), diagnose every failure, fix what's in scope, and loop until all cases pass. Use when evals are failing — including overnight run-evals schedule failures — or when the user wants to run, diagnose, or repair the eval suite. To author new coverage, use create-evals instead.
---

# Eval and Improve

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/eval-and-improve`) or describe the task and it triggers automatically._

You're running the platform's eval suite, diagnosing every failure, fixing what's in scope, and stopping when all cases pass. The eval wiring lives in [`evals/cases.py`](../../../evals/cases.py) (declares `agno.eval.Case`s) and [`evals/__main__.py`](../../../evals/__main__.py) (a thin entrypoint over agno's eval suite runner, `agno.eval.cli`), while fixes may also touch `agents/<slug>.py`, `teams/lead.py`, or rare one-line config flips in `app/main.py` per Step 3. Each case uses agno's built-in [`AgentAsJudgeEval`](https://docs.agno.com/evals/agent-as-judge) (LLM judge against a `criteria` rubric, binary pass/fail) and/or [`ReliabilityEval`](https://docs.agno.com/evals/reliability) (asserts which tools fired) — no custom DSL.

## 0. Preconditions

- Postgres reachable on 5432: `nc -z localhost 5432` returns 0. If not, `docker compose up -d agentos-db` from the source repo. (`docker compose ps` is unreliable from worktrees or alternate clones.)
- Venv active: `source .venv/bin/activate`. If `.venv` doesn't exist (fresh checkout or worktree), run `./scripts/venv_setup.sh` first. `evals/cases.py` imports the components directly from `agents/` and `teams/`, so no AgentOS server has to be running.
- `.env` populated with `OPENAI_API_KEY` (and `PARALLEL_API_KEY` if you have one — the runner pins Agno's expected web tool name based on it). `evals/__main__.py` loads `.env` at startup (via `python-dotenv`), so you do not need to source `.env` first. Worktrees don't inherit `.env` (it's gitignored) — copy it from the source repo if missing.

## 1. Run the suite

```bash
python -m evals --tag smoke            # fast template smoke checks
python -m evals --tag release          # broader pre-release checks
python -m evals --tag live             # current web/source checks
python -m evals --name <case>          # single case while iterating
python -m evals --json-output out.json # machine-readable results
python -m evals -v                     # stream the full agent run with rich panels
```

Output ends with a summary block. Exit code is 0 on all-pass, non-zero on any failure or error.

**Arriving from a scheduled failure?** If the trigger is "last night's run-evals went red" rather than a local run, start from the recorded history: eval runs live in Postgres (`db.get_eval_runs()` — also visible at os.agno.com, or ask Platform Manager), so find which case failed and when, then reproduce it locally with `python -m evals --name <case>` before diagnosing. A scheduled failure that won't reproduce locally is usually environment (rate limits, a live source that moved) — note it, don't chase it with prompt edits.

Stderr noise around MCP teardown (`RuntimeError: Event loop is closed`, httpx timeouts) at the end of a run is harmless — only the `Eval Summary` table and exit code count.

## 2. Diagnose each failure

For every failed case, decide which kind of failure it is and fix at the appropriate layer:

| Symptom | Likely cause | Where to fix |
|---|---|---|
| Judge fails, "answer is right but missing X" | Agent's instructions don't push for X | `agents/<slug>.py` — tighten the rule |
| Judge fails, response is fabricated | Agent hallucinated when it should have said it didn't know | Add a "if you can't find a real source, say so plainly" rule to the agent's instructions |
| Reliability fails: "missing tool X" | Agent didn't call the expected tool on this prompt | (a) Strengthen the routing rule in instructions, OR (b) the case is too narrow — broaden `expected_tool_calls` or drop the assertion |
| Reliability fails: "additional tool Y called" with `allow_additional_tool_calls=False` | Agent fanned out beyond the case's expectation | Tighten the agent's instructions OR set `allow_additional_tool_calls=True` |
| Reliability fails on Agno's web tool name (`parallel_search` ↔ `web_search`) | `PARALLEL_API_KEY` mismatch between `.env` and your shell — `evals/cases.py` pins `_WEB_TOOL` at import time | Sync the var in both places, then re-run |
| Same case flips PASS/FAIL across consecutive runs with no code change | Judge variance — rubric is too loose | Re-run 2-3 times to confirm; if it keeps flipping, tighten the case's `criteria` (more specific, more falsifiable) |
| Single case fails on full suite but passes alone | Transient flake or upstream rate limit (429s, MCP shutdown traceback) | Re-run the case in isolation. If it passes, re-run the full suite. If 429s persist, back off — don't fix the agent. |
| Many cases fail at once | Broad regression — model swap, MCP server down, tool removed | Diagnose the root cause first; do NOT paper over with prompt edits |
| `eval_db` write errors | Postgres down or migration missing | Bring DB up; check `docker logs agentos-db` |
| `cleanup:` in a case's error | A snapshot-diff `teardown` hook couldn't delete what the case created — Studio components and schedules (builder cases) or Agno writes (agno cases: entities, memories, notes). Both surfaces are ungated, so cases write real DB rows (a timeout does not mean nothing was created; the hooks wait 10s then delete what landed) | Check Postgres, then hard-delete the leftovers by id: `eval_db.delete_component(<id>, hard_delete=True)` for components, `ScheduleManager(eval_db).delete(<id>)` for schedules, `eval_db.delete_learning(<id>)` / `notes.delete(<path>)` for brain state; don't edit the agent or the case |

**Rule:** never weaken a case to make it green. Edit a case only when the assertion was wrong (overspecified rubric, wrong tool name, mismatch with how the agent's tools are named today). Catching a real regression is the whole point.

Quick test for "wrong assertion vs. real regression": read both sides — the agent's actual response next to the judge's stated reason (`--json-output` carries `judge_reason`). If the response looks correct against the user's intent but the rubric flagged a missing detail, the rubric was overspecified. If the response is genuinely wrong, the agent's instructions need work.

And when you touch a case, check the green is earned, not just present: the expected tool actually fired, and the rubric can't be satisfied by a shortcut (answering from memory without searching, citing sources it never fetched). Repair means making red green *and* making green honest.

## 3. Fix scope

In scope from this prompt:

- `agents/<slug>.py` (or `teams/lead.py` for the Agno team) — instructions, tools, model.
- `evals/cases.py` — when an assertion was genuinely wrong.
- One-line config flips in `app/main.py` if a case requires it (rare).

Out of scope (flag for the user, don't do):

- Removing cases.
- Editing `db/` or `app/` to make a case pass.
- Editing agno itself.

For agent quality issues that need fast iteration against a live container (cURL probes, instruction tweaks), hand off to [`improve-agent`](../improve-agent/SKILL.md) — its autonomous probe loop is faster than running the full eval suite per change. If the change is user-driven (add a tool, fix a known bug), use [`extend-agent`](../extend-agent/SKILL.md) instead.

## 4. Re-run and stop

After each fix, re-run the failing case:

```bash
python -m evals --name <case>
```

When all targeted cases pass, run the release-tagged cases once more to confirm nothing regressed:

```bash
python -m evals --tag release
```

Stop when `python -m evals --tag release` exits 0 **and** prints an `Eval Summary` block. If a re-run aborts mid-stream (no summary, regardless of exit code), treat it as inconclusive — re-run before declaring green.

## 5. Add a new case (if needed)

If diagnosing a failure reveals a missing assertion, add it to [`evals/cases.py`](../../../evals/cases.py). (That's the one authoring move that belongs here — for coverage-shaped work, an agent with no cases at all, or mining sessions for scenarios, hand off to [`create-evals`](../create-evals/SKILL.md).)

```python
Case(
    name="<short_id>",
    agent=<the_agent>,
    input="<prompt>",
    tags=("release",),  # add "smoke" only for fast core checks; use "live" for current web/source checks
    # Either or both of:
    criteria="<rubric describing a correct response>",
    expected_tool_calls=("<tool_name>",),
    # Required whenever the case's agent has the ungated create/edit/publish
    # Studio tools (every platform-builder case) — the snapshot-diff hooks delete
    # whatever the run created (components, schedules, learnings), even on timeout:
    setup=snapshot_builder_state,
    teardown=cleanup_new_builder_state,
)
```

Run `python -m evals --name <case>` to confirm it passes against the current agent. Commit the new case alongside any fixes.

## 6. Track regressions over time

Every case logs to Postgres via `db=eval_db`. Connect your AgentOS at [os.agno.com](https://os.agno.com) and view eval history — useful for catching slow drift on a weekly cron.

For the template's opt-in scheduled check, see [`workflows/run_evals.py`](../../../workflows/run_evals.py). It runs the `${EVALS_TAG:-smoke}`-tagged cases in-process (no subprocess) and returns a compact markdown report. Its cron is always registered but ships disabled — enable it from the AgentOS UI when you want it running daily.

---

## Reference: Case shape

`Case` ships with agno (`from agno.eval import Case`) — the template declares cases, agno runs them:

```python
@dataclass(frozen=True)
class Case:
    name: str
    input: str
    agent: Agent
    tags: tuple[str, ...] = ()
    timeout_seconds: int | None = None

    # Judge (LLM rubric, binary pass/fail): set to enable.
    criteria: str | None = None
    judge_model: Model | None = None  # per-case judge override

    # Reliability (tool-call assertion): set to enable.
    expected_tool_calls: tuple[str, ...] | None = None
    allow_additional_tool_calls: bool = True

    # Lifecycle hooks: setup runs before the agent; its return value is passed to
    # teardown, which always runs (pass, fail, error, timeout).
    setup: Callable | None = None
    teardown: Callable | None = None
```

The runner calls `agent.arun()` once per case and feeds the response into both checks, so cases that set both fields cost one agent run, not two.

Set `setup=snapshot_builder_state, teardown=cleanup_new_builder_state` (both in [`evals/cases.py`](../../../evals/cases.py)) on every case whose agent can reach the ungated create/edit/publish Studio tools (all platform-builder cases do this): setup snapshots Studio component ids, schedule ids, and learning/note state before the case and teardown hard-deletes only the new rows after, so eval runs never leave components behind — or schedules that would keep firing daily — and never touch pre-existing ones. The same pattern covers the other learning-store components: `setup=snapshot_learning_state, teardown=cleanup_new_learning_state` on every case that probes `agno`, `platform-manager`, or `platform-engineer`, so entities, memories, and notes a case *creates* are removed after it. One limit to know, because it decides how you write the case: the diff is on row identity, and an entity's facts, events and relationships all live inside a single row. So a case that merges into an entity, profile, or note that already existed leaves that edit behind — a superseded fact or a rewritten note line cannot be undone. Give every fixture a name no real team would have on file (`agno_captures_project_fact` and `agno_grounded_no_on_unknown` both do), and the case only ever touches rows it created.

`evals/cases.py` also conditions Agno's expected web tool name on `PARALLEL_API_KEY` (Parallel SDK if the key is set, keyless MCP otherwise). If your shell has the var set but `.env` doesn't (or vice versa), the assertion checks the wrong tool — sync them before debugging.
