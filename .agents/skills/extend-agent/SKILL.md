---
name: extend-agent
description: User-driven loop to change an existing agent in this AgentOS — add a tool/MCP server/toolkit, add a capability (knowledge base, learning/memory, sub-agent, scheduled task), grow the safe Studio registry so components built at runtime gain a new capability, refine its instructions, or fix a specific known bug, verifying each change against the live container. Use whenever the user names a concrete change to an agent, or wants a new building block available to the platform. For autonomous hardening with no specific change in mind, use improve-agent.
---

# Extend an Agent

> _Coding-agent workflow: run as `/extend-agent` or by describing the task._

The user names a change; you implement it, verify it against the live agent, and ask if there's more. Stop when they say done. The autonomous half is [`improve-agent`](../improve-agent/SKILL.md) — run it afterward.

The platform is on `http://localhost:8000` (`RUNTIME_ENV=dev`); code edits hot-reload.

## 0. Preconditions

- `curl -sSf http://localhost:8000/health` returns 200 (else ask for `docker compose up -d --build`).
- The container is bound to *this* checkout: `docker inspect agentos-api --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' | grep -F "$(pwd)"` prints a line. Empty → `cd` to the bound repo or restart compose from here.
- Ask for the target **slug**. Suggest a branch: `git checkout -b extend/<slug>-$(date +%Y%m%d)`.

## 1. Read the agent

Confirm the slug is code, not a Studio-built component:

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\tis_component=\(.is_component)"'
```

`is_component=true` has no source file — route the change through Platform Builder (`edit_agent` / `edit_team` / `edit_workflow`, then `publish_component`). Never create `agents/<slug>.py` under that id: code wins on resolution and silently shadows the built component.

Open the file — `agents/<slug>.py`, or for the reference components `platform-builder` → [`agents/builder.py`](../../../agents/builder.py), `platform-manager` → [`agents/manager.py`](../../../agents/manager.py), `platform-engineer` → [`agents/engineer.py`](../../../agents/engineer.py), `agno` → [`teams/lead.py`](../../../teams/lead.py). Capture purpose (docstring + `INSTRUCTIONS`), tools, pattern, and the existing levers (`learning=`, `knowledge=`, `num_history_runs`, model). Restate the purpose in 1–2 sentences.

## 2. Ask what to change

Structured choice when the harness has one, else plain text. Multi-select is fine — handle sequentially, then loop:

- **Add a tool** — MCP server, agno toolkit, or function tool.
- **Add a capability** — knowledge base, learning/memory, sub-agent/context provider, scheduled task.
- **Grow the registry** — declare a block in [`app/registry.py`](../../../app/registry.py) so everything the platform *builds* can carry it. Offer this unprompted when the ask is plural ("agents should be able to…").
- **Refine instructions** — clarify, narrow, change tone or format.
- **Fix a bug** — ask for the failing prompt, the observed behavior, what they want instead.
- **Something else.**

## 3. Ground the change

Search the `agno-docs` MCP ([`.mcp.json`](../../../.mcp.json)) for import path, constructor args, required env vars, pip deps. Fallback: <https://docs.agno.com/llms.txt>. When docs are loose, the installed source settles it:

```bash
docker exec agentos-api python -c "import inspect, agno.agent; print(inspect.signature(agno.agent.Agent.__init__))"
docker exec agentos-api python -c 'from agno.tools.exa import ExaTools'   # verify EVERY new import in the container
```

A failing import is a dead platform, not a degraded agent — `app/main.py` imports every agent at module scope.

Repo-specific rules per branch:

- **Learning / memory** — the lever is `learning=shared_learning` ([`app/learning.py`](../../../app/learning.py)). `enable_user_memories` is not an `Agent` parameter; `enable_agentic_memory` must stay off beside a LearningMachine. Entities are Agno's — don't index them from a second component. `add_history_to_context` replays the session and persists nothing.
- **Knowledge** — wire `knowledge=shared_knowledge` ([`app/knowledge.py`](../../../app/knowledge.py)) as one object (a list on an agent searches nothing). A product agent gets its own base — see create-agent's product pattern.
- **Sub-agent / context provider** — mirror [`agents/engineer.py`](../../../agents/engineer.py): spread `provider.get_tools()` into `tools=`, append `provider.instructions()` to `INSTRUCTIONS`.
- **Scheduled task** — [agno scheduler docs](https://docs.agno.com/agent-os/scheduler); `scheduler=True` is already on in `app/main.py`.
- **Grow the registry** — the bucket you declare into decides how a built component references it (`tool_names`, `model_id`, `knowledge_name`, `learning_name`, `function_name`). Tool names are global to an agent, so a toolkit exposing a name another declared toolkit already has is silently dropped — check first, and give any new toolkit `add_instructions=True` (a built component's instructions are model-written; this is your only usage channel):

  ```bash
  docker exec agentos-api python -c "from app.registry import registry; print([t.name for t in registry.tools if 'read_file' in t.functions])"
  ```

- **Refine instructions** — propose a minimal diff; narrow ("on recent-events questions, follow up with a `web_fetch`") rather than forbid.
- **Fix a bug** — reproduce on the live agent first (Step 6), then find the layer: `INSTRUCTIONS` (most common), tool, model, env.

## 4. Propose, then edit

Say in 2–3 lines what you'll change and why; get a "yes". Then edit, one change per loop:

- The component's file — instructions, tools, model, `learning=`, `knowledge=`.
- [`app/registry.py`](../../../app/registry.py) — registry branch only; a new `app/<thing>.py` when the block is more than a constructor call.
- [`app/main.py`](../../../app/main.py) — only for a new sub-agent, `knowledge=[...]`, or interface wiring.
- [`app/config.yaml`](../../../app/config.yaml) — refresh the description and add a quick prompt that exercises the change.
- [`pyproject.toml`](../../../pyproject.toml) — only for new pip deps.

## 5. Restart

```bash
docker compose restart agentos-api                                   # no new deps
./scripts/generate_requirements.sh && docker compose up -d --build   # new deps
until curl -sSf http://localhost:8000/health > /dev/null; do sleep 0.5; done
docker exec agentos-api grep -c "<unique substring from your edit>" /app/agents/<slug>.py   # 0 = edit didn't reach the container
```

## 6. Smoke test

Pick a prompt that exercises the change (teams: `/teams/agno/runs`, same flags):

```bash
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<the targeted prompt>" -F "user_id=claude-extend-agent" -F "stream=false" \
  -o /tmp/extend-out.json -w "HTTP %{http_code} in %{time_total}s\n"
jq -r '.content // .' < /tmp/extend-out.json
docker logs agentos-api --since 30s 2>&1 | grep -E "Running: \w+\(" | head -40   # which tools fired
```

A registry change gets one check first — ask `platform-builder`: *"Call list_tools and show the row for <tool> exactly as returned — name, buildable, source. Do not create anything."* `buildable: true`, `source: declared` means it landed; `discovered` means it came from boot discovery and a build will refuse it.

**Side effects.** `platform-builder` creates and publishes real components on "build me…" prompts, and learning components (`agno`, `platform-manager`, `platform-engineer`, anything with `learning=`) file what they're told into shared stores. Prefer plan-only probes, use fixture content no real team would have, and bracket the session with the snapshot pairs in [improve-agent Step 2](../improve-agent/SKILL.md). Never run the delete side while someone else is talking to Agno.

Did the change land? Yes → Step 7. Almost → one more pass, at most 2–3, then ask how to proceed. Worse → show `git diff` and offer to revert only your patch.

## 7. Loop or wrap up

*"Anything else to improve, or are we done?"* More → Step 2. Done → Step 8.

## 8. Report

One line per accepted change, `git diff --stat` plus the agent-file diff, a suggested commit (`feat(<slug>): …`, `fix(<slug>): …`, `chore(<slug>): refine instructions`), and the next step: [`improve-agent`](../improve-agent/SKILL.md). A registry change also gets a line in [`AGENTS.md`](../../../AGENTS.md)'s registry inventory.
