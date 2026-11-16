---
name: create-evals
description: Author eval coverage for an agent in this AgentOS — read what the agent promises, choose the behaviors worth testing, then write, run and audit Case entries in evals/cases.py. Use when the user wants evals created, coverage added, or an agent's behavior pinned down as tests. For failing suites or agent hardening, use improve instead.
---

# Create Evals

> _Coding-agent workflow: run as `/create-evals` or by describing the task._

Turn what an agent promises into `Case` entries in [`evals/cases.py`](../../../evals/cases.py),
so a regression shows up as a failed case. Read [`AGENTS.md`](../../../AGENTS.md) first.

Evals need PostgreSQL running and the project venv (`./scripts/venv_setup.sh`, then
`source .venv/bin/activate`). They do not need the API. Each run spends model calls and saves
its session and result in the application's database.

## 1. Choose what to test

Read the agent's instructions and tools. Pick two or three behaviors that matter most to its
job: what it must always do, what it must never do, and which tool it should use for what.
Real requests from past sessions make good inputs. A recorded answer is not a correct answer.
Skip what `evals/cases.py` already covers. Ask the user only which failures would hurt most.

## 2. Write the case

Add it to `CASES` in `evals/cases.py`:

```python
Case(
    name="<agent>_<behavior>",
    agent=<the_agent>,  # use team= for a team
    input="<a realistic request>",
    criteria="<what a correct answer contains, checkable from the answer alone>",
    expected_tool_calls=("<tool>",),
    user_id="<a test user of your own>",
    tags=("smoke",),
)
```

- The judge sees only the answer, not your files or database. Write criteria it can check
  from the answer, and state any fact it needs.
- `expected_tool_calls` checks that a tool was called, not that it succeeded.
- An agent built in Studio has no file. Load it with
  `Agent.load("<id>", db=get_postgres_db(), registry=registry, published_only=True)`.
- If the agent uses MCP tools, connect them in [`evals/__main__.py`](../../../evals/__main__.py);
  it connects Super Agent's only.

## 3. Run and audit

```bash
python -m evals --name <case>
```

Read the answer, the tools that fired and the judge's reason. If the case is wrong, fix the
case. If the agent is wrong, say so and use [`/improve`](../improve/SKILL.md). Run a case again
when its verdict changes between runs, and tighten vague criteria.

## 4. Hand over

List the new cases and show `git diff evals/cases.py`. Say which ones pass.
