---
name: create-agent
description: Create and register a code-defined agent in this AgentOS from a concrete request or guided discovery, add its UI prompts, reload the development runtime, and verify a real run. Use when the user wants to build or add an agent.
---

# Create a New Agent

> _Coding-agent workflow: run as `/create-agent` or by describing the task._

Add one agent to this AgentOS as a source file in `agents/`, managed by git, registered with
the platform and proven with a real run. Super Agent can also build agents at runtime; those
live in the database, not the repo. Use this skill when the agent belongs in code.

Read `AGENTS.md` first. Build from what the user asked for and state your choices (name, ID,
tools) as you go. Ask only when the job is unclear or a tool needs a key that `.env` lacks.

## 1. Write the agent

Create `agents/<slug_underscore>.py`:

```python
"""
<Title>
=======
"""

from agno.agent import Agent

from app.registry import shared_learning
from app.settings import default_model
from db import get_postgres_db

INSTRUCTIONS = """\
You are <DisplayName>: <the agent's job, in one line>.

How you speak:
- <one rule per line: tone, length, what to confirm>

How you <work>:
- <one rule per line: which tool for what, what to refuse, what to hand off>\
"""

<slug_underscore> = Agent(
    id="<slug>",
    name="<DisplayName>",
    model=default_model(),
    db=get_postgres_db(),
    learning=shared_learning,
    tools=[...],
    instructions=INSTRUCTIONS,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

- **Tools:** look them up in the Agno docs (the `agno-docs` MCP in [`.mcp.json`](../../../.mcp.json))
  and confirm the import works in the running API. `get_web_tools()` in
  [`app/registry.py`](../../../app/registry.py) covers web search and fetch without a key.
- **User:** inherit the caller's identity; do not set a fixed `user_id`. Anonymous runs
  have unowned sessions and no per-user learning.
- **ID:** pick one no other agent uses. A code agent hides a Studio-built agent with the same ID.
  List them with `curl -s http://localhost:8000/agents | jq -r '.[].id'`.

## 2. Register it

- [`app/main.py`](../../../app/main.py): import the agent and add it to the existing `agents` list.
- [`app/config.yaml`](../../../app/config.yaml): add a `manifest` entry keyed by the agent ID, with a
  description and three quick prompts. The UI shows them, and Super Agent reads the description
  to decide when to run the agent, so state the job it does in one line under 120 characters.

Python changes reload on their own. Restart the API after editing YAML:
`docker compose restart agentos-api`.

## 3. Run it

```bash
mkdir -p tmp
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  --form-string "message=<one of the quick prompts>" \
  --form-string "user_id=create-agent-check" \
  --form-string "stream=false" --output tmp/create-agent-run.json
jq '{status, content, tools}' tmp/create-agent-run.json
```

Read the answer and the tool calls; a 200 alone is not a pass. If the run fails, read
`docker compose logs agentos-api`, fix the cause and run it again. Then run
`./scripts/validate.sh`.

## 4. Hand over

Show the answer from the run, then where the agent lives:

- The AgentOS UI at `https://os.agno.com/?ref=railway-template` (refresh the Agents list).
- `POST /agents/<slug>/runs` and the `run_agent` MCP tool.
- Super Agent, which can now run it by name and schedule it for recurring work.

Say what you verified and what you did not. Next steps:
[`/extend-agent`](../extend-agent/SKILL.md) for a specific change,
[`/improve`](../improve/SKILL.md) to harden it, and
[`/create-evals`](../create-evals/SKILL.md) to keep the run above as its first eval.
