---
name: extend-agent
description: Change an existing agent in this AgentOS — add a tool or MCP server, add knowledge, memory or notes, make a capability available to agents built in Studio, refine instructions, or fix a known bug — then verify the change with a real run. Use when the user names a concrete change to an agent or wants a new building block on the platform. For hardening without a specific change in mind, use improve.
---

# Extend an Agent

> _Coding-agent workflow: run as `/extend-agent` or by describing the task._

Make the change the user asked for and prove it with a run that exercises it. Read
[`AGENTS.md`](../../../AGENTS.md) first. Ask only for details that change the outcome.

## 1. Find the agent

- A code agent has a file in `agents/`. Read its instructions, tools and model.
- An agent built in Studio has no file (`is_component` is true in `GET /agents`). Change it by
  asking Super Agent. Do not create a file with its ID; the file would hide it.
- Super Agent, Platform Builder and Mini Agent belong to Agno. Configure Super Agent through
  `OSManager(...)` in [`app/main.py`](../../../app/main.py); do not recreate them here.

## 2. Make the change

| Change | Where |
|---|---|
| Instructions, tools, model | The agent's file |
| Remember each user | `learning=shared_learning` |
| Search operator documents | `knowledge=shared_knowledge` (one object, not a list) |
| Keep notes | Add `shared_notes.tools()` to `tools` |
| Make something available in Studio | Declare it in [`app/registry.py`](../../../app/registry.py) |
| Description and quick prompts | [`app/config.yaml`](../../../app/config.yaml) |
| A new dependency | `pyproject.toml`, then `./scripts/generate_requirements.sh` and rebuild both images |
| A schedule | Ask Super Agent |

Look up tools and their arguments in the Agno docs (the `agno-docs` MCP in
[`.mcp.json`](../../../.mcp.json)). Try a new import in the running API before wiring it in,
because `app/main.py` imports every agent and one bad import stops the platform:

```bash
docker compose exec -T agentos-api python -c "from agno.tools.<module> import <Toolkit>"
```

Check tool names in `app/registry.py` before adding a toolkit. Distinct toolkits can share
function names, but unqualified references can become ambiguous; prefer distinct names.

## 3. Verify

Python changes reload on their own. After editing YAML, run
`docker compose restart agentos-api`. After editing `.env`, run
`docker compose up -d agentos-api` to recreate the container with the new environment.
Then run a prompt that exercises the change:

```bash
mkdir -p tmp
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  --form-string "message=<a prompt that exercises the change>" \
  --form-string "user_id=extend-agent-check" \
  --form-string "stream=false" --output tmp/extend-agent-run.json
jq '{status, content, tools}' tmp/extend-agent-run.json
```

Use `/teams/superagent/runs` for Super Agent. Read the answer and the tool calls; a 200 alone
is not a pass. Runs are real: Super Agent builds real components when asked to, and agents with
learning save what they are told, so use test data you own. Finish with `./scripts/validate.sh`.

## 4. Report

Say what changed, show the diff, and say what you verified and what you did not. Suggest
[`/improve`](../improve/SKILL.md) only if wider hardening would help.
