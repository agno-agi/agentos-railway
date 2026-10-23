---
name: extend-agent
description: User-driven loop to change an existing agent in this AgentOS — add a tool/MCP server/toolkit, add a capability (knowledge base, learning/memory, sub-agent, scheduled task), grow the safe Studio registry so components built at runtime gain a new capability, refine its instructions, or fix a specific known bug, verifying each change against the selected development runtime. Use whenever the user names a concrete change to an agent, or wants a new building block available to the platform. For autonomous hardening with no specific change in mind, use eval-and-improve.
---

# Extend an Agent

> _Coding-agent workflow: run as `/extend-agent` or by describing the task._

Implement the concrete requested change and verify the affected behavior. Use
[eval-and-improve](../eval-and-improve/SKILL.md) for broader exploratory hardening when
requested; a narrow change does not require a separate hardening campaign.

## 0. Select the development runtime

Read `AGENTS.md` and inspect `git status`. Use the runtime already serving this checkout;
do not switch modes or start a second API on port 8000.

- **Compose API:** confirm its bind mount points to this checkout. Run Python with
  `docker compose exec -T agentos-api python`; inspect `docker compose logs agentos-api`.
  If setup is needed, follow [setup-platform](../setup-platform/SKILL.md).
- **Host API:** follow the [sandbox setup commands](../../../docs/sandboxes.md#local-docker-sandbox).
  Confirm the process's working directory and startup environment. Run Python with
  `.venv/bin/python` and the same `.env`/runtime/DB settings as that process; use
  `uv run --no-project --env-file .env .venv/bin/python` when loading the env file.
  Keep the API in a persistent terminal and inspect that process's log. No API container
  or container bind mount is required in this mode.

Check `/health` at the configured endpoint with its existing authentication. If unavailable,
diagnose the selected runtime rather than assuming Compose is required. Use a bounded startup
wait and inspect logs on failure. For MCP checks use `scripts/mcp_check.sh` with Compose or
`MCP_CHECK_HOST=1 ./scripts/mcp_check.sh` with the host API.

Infer the target from the request and registrations; ask for its ID only if ambiguous.

## 1. Read the agent

Confirm the slug is code, not a Studio-built component:

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\tis_component=\(.is_component)"'
```

`is_component=true` has no source file — route the change through OS Manager (`edit_agent` / `edit_team` / `edit_workflow`, then `publish_component`). Never create `agents/<slug>.py` under that id: code wins on resolution and silently shadows the built component.

Open the user's `agents/<slug>.py`. For OS Manager (`os-manager-internal`), inspect its `OSManager(...)` configuration in [`app/main.py`](../../../app/main.py) and the installed framework source; its members are framework-owned. Capture purpose, tools, learning, knowledge and model. Do not recreate the internal agents in this template.

## 2. Resolve the requested change

Use the change already specified by the user. Ask only for missing details that affect the outcome. If they want guidance, the available directions include:

- **Add a tool** — MCP server, agno toolkit, or function tool.
- **Add a capability** — knowledge base, learning/memory, sub-agent/context provider, scheduled task.
- **Grow the registry** — declare a block in [`app/registry.py`](../../../app/registry.py) so everything the platform *builds* can carry it. Offer this unprompted when the ask is plural ("agents should be able to…").
- **Refine instructions** — clarify, narrow, change tone or format.
- **Fix a bug** — ask for the failing prompt, the observed behavior, what they want instead.
- **Something else.**

## 3. Ground the change

Search the `agno-docs` MCP ([`.mcp.json`](../../../.mcp.json)) for import path, constructor args, required env vars, pip deps. Fallback: <https://docs.agno.com/llms.txt>. When docs are loose, the installed source settles it:

Run Python in the selected Compose or host environment from Step 0, for example:

```python
import inspect
from agno.agent import Agent

print(inspect.signature(Agent.__init__))
```

Verify proposed imports in that same environment before adding them to startup.

A failing import is a dead platform, not a degraded agent — `app/main.py` imports every agent at module scope.

Repo-specific rules per branch:

- **Learning / memory** — the lever is `learning=shared_learning` ([`app/registry.py`](../../../app/registry.py)). `enable_user_memories` is not an `Agent` parameter; `enable_agentic_memory` must stay off beside a LearningMachine. Entities are Agno's — don't index them from a second component. `add_history_to_context` includes session history; it does not replace per-user learning.
- **Knowledge** — wire `knowledge=shared_knowledge` ([`app/registry.py`](../../../app/registry.py)) as one object (a list on an agent searches nothing). A product agent gets its own base — see create-agent's product pattern.
- **Shared notes** — import `shared_notes` from `app.registry` and add `shared_notes.tools()` to `tools`. Studio uses the declared toolkit name `filesystem`. Default tools read, write, append, replace, list, search and move PostgreSQL notes. User scoping follows AgentOS user isolation; keep personal profiles in learning and Company knowledge in Company wiki. Do not attach it to end-user product agents.
- **Sub-agent / context** — choose a supported Agent/Team composition or tool interface from the pinned framework, and verify the import and constructor before wiring it. For read access to a directory, use `WorkspaceContextProvider` (`agno.context.workspace`) with `mode=ContextMode.tools` (`agno.context.mode`): spread `provider.get_tools()` into `tools=` and append `provider.instructions()` to the instructions. Default exclusions block env and credential files.
- **Scheduled task** — [agno scheduler docs](https://docs.agno.com/agent-os/scheduler); `scheduler=True` is already on in `app/main.py`.
- **Grow the registry** — the bucket you declare into decides how a built component references it (`tool_names`, `model_id`, `knowledge_name`, `learning_name`, `function_name`). Tool names are global to an agent, so a toolkit exposing a name another declared toolkit already has is silently dropped — check first, enable `add_instructions=True` when the toolkit supports and supplies useful instructions:

  Inspect `registry.tools` and the proposed toolkit's registered functions in the selected
  runtime. Verify name collisions and the Studio-visible catalog rather than assuming a
  successfully imported toolkit is buildable. MCP toolkits (such as `parallel_tools`) register
  their functions only after connecting, so an empty function list from a fresh Python process
  is expected for them; confirm those with the OS Manager `list_tools` check in Step 6.


- **Refine instructions** — propose a minimal diff; narrow ("on recent-events questions, follow up with a `web_fetch`") rather than forbid.
- **Fix a bug** — reproduce on the live agent first (Step 6), then identify the responsible layer: instructions, tool, model, configuration or framework.

## 4. Propose, then edit

State the intended change and why. Proceed when the user has already authorized it; ask only when a material decision or scope expansion remains. Preserve existing registrations and shared resources. Edit the applicable files:

- The component's file — instructions, tools, model, `learning=`, `knowledge=`.
- [`app/registry.py`](../../../app/registry.py) — shared capabilities and resource wiring; keep the starter lean instead of creating a new module by default.
- [`app/main.py`](../../../app/main.py) — only for a new sub-agent, `knowledge=[...]`, or interface wiring.
- [`app/config.yaml`](../../../app/config.yaml) — refresh the description and add a quick prompt that exercises the change.
- [`pyproject.toml`](../../../pyproject.toml) — only for new pip deps.

## 5. Reload the selected runtime

For Compose, restart `agentos-api` when needed. For the host API, use its reload process or
restart that host process with the same environment; do not start an API container. Restart
explicitly after YAML/env changes. After dependency changes, regenerate requirements,
update the host venv if used (deactivate before setup), and rebuild both Dockerfile targets
as required by `AGENTS.md`. Use a bounded health wait and inspect the matching runtime log
if startup fails. Confirm the intended code and component IDs are served before probing.

## 6. Smoke test

Pick a prompt that exercises the change. Use `/agents/<id>/runs` for agents or `/teams/<id>/runs` for the actual target team (OS Manager is `os-manager-internal`). The example assumes the local development endpoint:

```bash
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<the targeted prompt>" -F "user_id=claude-extend-agent" -F "stream=false" \
  -o /tmp/extend-out.json -w "HTTP %{http_code} in %{time_total}s\n"
jq -r '.content // .' < /tmp/extend-out.json
```

Inspect the run status, answer, tool results and matching runtime logs; HTTP 200 alone is not success. Use the configured endpoint/authentication when different from the example.

A registry change gets one check first — ask `os-manager-internal`: *"Call list_tools and show the row for <tool> exactly as returned — name, buildable, source. Do not create anything."* `buildable: true`, `source: declared` means it landed; `discovered` means it came from boot discovery and a build will refuse it.

**Side effects.** `os-manager-internal` creates and publishes real components on "build me…" prompts, and learning components (`os-manager-internal`, anything with `learning=`) file what they're told into shared stores. Cases run through `python -m evals` against the application's configured database, where sessions and results persist for the UI. Use explicitly owned fixtures for mutating cases and never sweep shared data after probes. Verify HTTP availability separately from model behavior.

Did the change land? Yes → Step 7. Almost → one more pass, at most 2–3, then ask how to proceed. Worse → show `git diff` and offer to revert only your patch.

## 7. Loop or wrap up

Report completion once the requested change and relevant checks are handled. Continue another change only when requested.

## 8. Report

One line per accepted change, `git diff --stat` plus the agent-file diff, a suggested commit (`feat(<slug>): …`, `fix(<slug>): …`, `chore(<slug>): refine instructions`), and any remaining verification. Suggest [`eval-and-improve`](../eval-and-improve/SKILL.md) only when broader hardening would be useful. Update [`AGENTS.md`](../../../AGENTS.md) only when the change affects its documented conventions.
