---
name: eval-and-improve
description: Run the eval suite (python -m evals), diagnose every failure, fix what's in scope, and loop until all cases pass. Use when evals are failing — including overnight run-evals schedule failures — or when the user wants to run, diagnose, or repair the eval suite. To author new coverage, use create-evals instead.
---

# Eval and Improve

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/eval-and-improve`) or describe the task and it triggers automatically._

You're running the platform's eval suite, diagnosing every failure, fixing what's in scope, and stopping when all cases pass. The eval wiring lives in [`evals/cases.py`](../../../evals/cases.py) (declares `agno.eval.Case`s), [`evals/hooks.py`](../../../evals/hooks.py) (the setup/teardown sweeps behind them), and [`evals/__main__.py`](../../../evals/__main__.py) (a thin entrypoint over agno's eval suite runner, `agno.eval.cli`). Each case uses agno's built-in [`AgentAsJudgeEval`](https://docs.agno.com/evals/agent-as-judge) (LLM judge against a `criteria` rubric, binary pass/fail by default), [`ReliabilityEval`](https://docs.agno.com/evals/reliability) (asserts which tools fired), and/or a `scorer` (deterministic, in-process, no model call).

## 0. Preconditions

- Postgres reachable on 5432: `nc -z localhost 5432` returns 0. If not, `docker compose up -d agentos-db` from the source repo. (`docker compose ps` is unreliable from worktrees or alternate clones.)
- Venv active: `source .venv/bin/activate`. If `.venv` doesn't exist (fresh checkout or worktree), run `./scripts/venv_setup.sh` first. `evals/cases.py` imports the components directly from `agents/` and `teams/`, so no AgentOS server has to be running.
- `.env` populated with `OPENAI_API_KEY` (and `PARALLEL_API_KEY` if you have one — `evals/cases.py` pins Agno's expected web tool name from it at import time). `evals/__main__.py` loads `.env` at startup (via `python-dotenv`), so you do not need to source `.env` first. Worktrees don't inherit `.env` (it's gitignored) — copy it from the source repo if missing.

## 1. Run the suite

```bash
python -m evals --tag smoke            # fast template smoke checks
python -m evals --tag release          # broader pre-release checks
python -m evals --tag live             # current web/source checks
python -m evals --name <case>          # single case while iterating
python -m evals --tag smoke --list     # what a selector picks up, without running it
python -m evals --json-output out.json # machine-readable results
python -m evals -v                     # stream the full agent run with rich panels
```

Output ends with a summary block. Exit code is 0 on all-pass, non-zero on any failure or error.

**Be the only writer.** The learning and builder teardowns sweep by snapshot diff, so a note, entity, memory, or component that lands in the shared stores while a case is running reads as new and gets deleted — including one a teammate filed through Agno in the same window. Run the suite when nobody else is talking to the platform; if you can't be sure, say so before running rather than after.

**Arriving from a scheduled failure?** Start from the recorded history: eval runs live in Postgres (`db.get_eval_runs()` — also visible at os.agno.com, or ask Platform Manager), so find which case failed and when, then reproduce it locally with `python -m evals --name <case>` before diagnosing. A scheduled failure that won't reproduce locally is usually environment (rate limits, a live source that moved) — note it, don't chase it with prompt edits.

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
| Case error `agent: run paused awaiting user input` (or `team: …`) | The run hit a HITL confirmation gate and never completed, so it was never graded — Platform Builder's archive/delete pauses are the usual cause | Rewrite the case `input` to stay on the ungated side of the gate, unless the gate itself is what you meant to test — a paused run is a failed case, never a judgeable one |
| `cleanup:` in a case's error | A snapshot-diff `teardown` hook couldn't delete what the case created — Studio components and schedules (builder cases) or learning writes (entities, memories, notes). Both surfaces are ungated, so cases write real DB rows (an abort does not mean nothing was created: the hooks wait out an in-flight write before sweeping, then delete what landed) | Check Postgres, then hard-delete the leftovers by id: `eval_db.delete_component(<id>, hard_delete=True)` for components, `ScheduleManager(eval_db).delete(<id>)` for schedules, `eval_db.delete_learning(<id>)` for learnings / `notes.delete(<path>)` for shared notes; don't edit the agent or the case |
| `refusing to sweep …` in a case's error | A teardown guard tripped rather than delete rows it can't attribute to the case: a learning row missing from the snapshot predates it (`created_at` before the snapshot's `taken_at`, or NULL) — proof the snapshot missed rows, since a transient DB error during `setup` reads as an empty store; or more new learning rows (25) or schedules (5) than a case plausibly creates; or reserved schedule names present against an empty snapshot | Don't loosen the guard. Look at the rows, confirm which the case actually created, delete those by hand (the error names the call), and re-run once the DB is healthy |

**Rule:** never weaken a case to make it green. Edit a case only when the assertion was wrong (overspecified rubric, wrong tool name, mismatch with how the agent's tools are named today).

Quick test for "wrong assertion vs. real regression": read both sides — the agent's actual response next to the judge's stated reason (`--json-output` carries `judge_reason`). If the response looks correct against the user's intent but the rubric flagged a missing detail, the rubric was overspecified. If the response is genuinely wrong, the agent's instructions need work.

When you edit a case, check the green is earned: the expected tool actually fired, and the rubric can't be met by a shortcut (answering from memory without searching, citing sources never fetched).

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

If diagnosing a failure reveals a missing assertion, add it to [`evals/cases.py`](../../../evals/cases.py). (For coverage-shaped work, an agent with no cases at all, or mining sessions for scenarios, hand off to [`create-evals`](../create-evals/SKILL.md).)

```python
Case(
    name="<short_id>",
    agent=<the_agent>,  # a Team goes in team=<the_team> — separate fields, exactly one set
    input="<prompt>",
    tags=("release",),  # add "smoke" only for fast core checks; use "live" for current web/source checks
    # At least one check, any combination:
    criteria="<rubric describing a correct response>",
    expected_tool_calls=("<tool_name>",),
    # Required whenever the case's component can reach the ungated create/edit/publish
    # Studio tools (every platform-builder case) — the snapshot-diff hooks delete
    # whatever the run created (components, schedules, learnings), even on timeout:
    **BUILDER_HOOKS,  # or **LEARNING_HOOKS for a non-builder learning-store case — see evals/hooks.py
)
```

Run `python -m evals --name <case>` to confirm it passes against the current agent. Commit the new case alongside any fixes.

## 6. Track regressions over time

Every case logs to Postgres via `db=eval_db`. Connect your AgentOS at [os.agno.com](https://os.agno.com) and view eval history — useful for catching slow drift on a weekly cron.

For the template's opt-in scheduled check, see [`workflows/run_evals.py`](../../../workflows/run_evals.py). It runs the `${EVALS_TAG:-smoke}`-tagged cases in-process (no subprocess) and returns a compact markdown report. Its cron is always registered but ships disabled — enable it from the AgentOS UI when you want it running daily.

Enabling it carries the only-writer rule from Step 1 into an unattended run: smoke includes learning-store cases, so a scheduled run that fires mid-conversation sweeps what somebody just filed with Agno. If you recommend enabling it, name an hour nobody is on the platform in the same breath — and on a busy platform, say plainly that leaving it off and running the suite deliberately is the better trade.

---

## Reference: Case shape

`Case` ships with agno (`from agno.eval import Case`) — the template declares cases, agno runs them:

```python
@dataclass(frozen=True)
class Case:
    name: str
    input: str
    # The component under test — exactly one of these two; both or neither raises
    # at construction. A Team never rides in a field named `agent`.
    agent: Agent | None = None
    team: Team | None = None
    tags: tuple[str, ...] = ()
    timeout_seconds: int | None = None  # falls back to the runner's --timeout

    # Judge (LLM rubric): set `criteria` to enable.
    criteria: str | None = None
    judge_model: Model | None = None            # per-case judge override
    judge_mode: JudgeMode = JudgeMode.BINARY    # NUMERIC grades 1-10 instead
    judge_threshold: int = 7                    # read only in NUMERIC mode

    # Reliability (tool-call assertion): set `expected_tool_calls` to enable.
    expected_tool_calls: tuple[str, ...] | None = None
    allow_additional_tool_calls: bool = True

    # Lifecycle hooks: setup runs before the run, outside the timeout; its return value
    # is passed to teardown, which always runs once setup completed (pass, fail, error,
    # timeout) and receives (context, result) so it can inspect result.error/.timed_out.
    setup: Callable | None = None
    teardown: Callable | None = None

    # Scorer (deterministic, in-process): set `scorer` to enable.
    scorer: Scorer | None = None
    expected: Any | None = None   # handed to the scorer alongside the run
```

**One run, every check.** The runner calls `arun()` once on whichever of `agent`/`team` is set and feeds that single response into the judge, the reliability assertion, and the scorer, so a case with all three costs one run, not three. A case passes only when every check it configured passed — and it must configure at least one: `criteria=""` and `expected_tool_calls=()` count as unset and construction raises.

**Only a completed run is graded.** A run that ends paused, cancelled, or in error is failed with that status in `error` and never reaches the judge. So an unresolved HITL confirmation reads as `agent: run paused awaiting user input`, not as a rubric failure — see the diagnostics table.

**`team=` is not cosmetic.** Nothing type-checks these fields at runtime, and mypy can't either (`agno.eval` resolves `Case` through a module-level `__getattr__`, so it types as `Any`), so a team in `agent=` runs green while reporting the team's id under `agent_id` with `team_id` null — in `--json-output`, in `--list`, and in the `agent:`-labelled error lines. The stored eval rows are unaffected (`ReliabilityEval` reads the ids off the run output, not off the case).

**Binary is the default.** `judge_mode=JudgeMode.NUMERIC` swaps the pass/fail verdict for a 1-10 score that passes at `judge_threshold`, surfaced in the payload as `judge_score`. It's useful for tracking quality drift a bare verdict hides, and it's the wrong tool for a regression gate. The `scorer` is the opposite lever — an object with `async ascore(run, expected) -> Score` (the `agno.scorer` protocol), run in-process on gradeable runs with no model call. Use it when the assertion is exact (a number, a JSON shape, an exact substring) and a rubric would only fuzz it.

Set `**BUILDER_HOOKS` (defined in [`evals/hooks.py`](../../../evals/hooks.py)) on every case whose component can reach the ungated create/edit/publish Studio tools: setup snapshots Studio component ids, schedule ids, and learning/note state; teardown hard-deletes only the rows that appeared — never pre-existing ones — and refuses rather than guesses when the snapshot looks incomplete (the `refusing to sweep` row above). Every `platform-builder` case qualifies, and so does an `agno` case one delegation away from a build (`agno_dispatch_honest_roster`), since the team reaches the builder through its member. Every other case probing `agno`, `platform-manager`, or `platform-engineer` takes the narrower pair, `**LEARNING_HOOKS`, so the entities, memories, and notes it *creates* are removed. The builder pair is a strict superset, so upgrading a borderline case is always safe. The diff is on row identity, and an entity's facts, events, and relationships live inside a single row: a case that merges into an entity, profile, or note that already existed leaves that edit behind — a superseded fact or a rewritten note line cannot be undone. So give every fixture a name no real team would have on file (`agno_captures_project_fact` does), and the case only ever touches rows it created.
