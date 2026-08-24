---
name: extend-agent
description: User-driven loop to change an existing agent in this AgentOS — add a tool/MCP server/toolkit, add a capability (knowledge base, learning/memory, sub-agent, scheduled task), grow the safe Studio registry so components built at runtime gain a new capability, refine its instructions, or fix a specific known bug, verifying each change against the live container. Use whenever the user names a concrete change to an agent, or wants a new building block available to the platform. For autonomous hardening with no specific change in mind, use improve-agent.
---

# Extend an Agent

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/extend-agent`) or describe the task and it triggers automatically._

You are recursively extending a target agent **with the user in the driver's seat**. Each iteration: the user names a change, you implement it, verify it against the live agent, then ask if there's more to do. Stop when the user says they're done.

This is the user-driven half of the iteration loop. The autonomous half lives in [`improve-agent`](../improve-agent/SKILL.md) — run it afterward to confirm nothing else regressed.

The platform is on `http://localhost:8000` (`RUNTIME_ENV=dev`). Compose runs uvicorn with a scoped `--reload`, so code edits hot-reload; Step 5 covers restarts.

## 0. Preconditions

- Live container reachable: `curl -sSf http://localhost:8000/health` returns 200. If not, ask the user to `docker compose up -d --build` first. (`docker compose ps` is unreliable from worktrees or alternate clones — trust the health probe.)
- Live container is bound to *this* checkout — otherwise restarts won't pick up your edits:

  ```bash
  docker inspect agentos-api --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' | grep -F "$(pwd)"
  ```

  Empty result = the container's `/app` is bound to a different repo path. Either `cd` to that repo or restart the container from this directory (`docker compose down && docker compose up -d --build`).
- Ask the user for the target agent **slug** (e.g. `platform-manager`).
- Recommend the user create a feature branch (`git checkout -b extend/<slug>-$(date +%Y%m%d)`) so any wrong turns are easy to revert.

## 1. Read the agent first

**First, confirm the slug has a file at all.** A runnable id is either code (a file in `agents/`, `teams/`, or `workflows/`, registered in `app/main.py`) or a Studio-built component that lives only in the database. The listing endpoints label which (`/teams` and `/workflows` carry the same field):

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\tis_component=\(.is_component)"'
```

`is_component=true` means there is no source file to open. Resolution checks the code list passed to `AgentOS(agents=[...])` before the database, so a new `agents/<slug>.py` registered in [`app/main.py`](../../../app/main.py) under an id the Studio already publishes *shadows* the runtime component — every run goes to your file while the user's component sits untouched behind it, and it looks like it worked. Route that ask to Platform Builder (`edit_agent` / `edit_team` / `edit_workflow`, then `publish_component`); stay in this skill only if the user means to *replace* the built component with a code one, which starts by archiving it.

Then open the component's file — `agents/<slug>.py` for user-built agents; the reference components map ids to files: `platform-builder` → [`agents/builder.py`](../../../agents/builder.py), `platform-manager` → [`agents/manager.py`](../../../agents/manager.py), `platform-engineer` → [`agents/engineer.py`](../../../agents/engineer.py), the `agno` team → [`teams/lead.py`](../../../teams/lead.py). Capture:

- **Stated purpose** — the file's docstring + the `INSTRUCTIONS` string.
- **Tools** — what's wired and what each one does.
- **Pattern** — direct tools plus a `learning=` machine ([`teams/lead.py`](../../../teams/lead.py)), context provider (the `WorkspaceContextProvider` in [`agents/engineer.py`](../../../agents/engineer.py), tools mode), Studio tools (Platform Builder), or a mix (Platform Manager: read-only `AgentOSTools` plus the deployment-check functions).
- **Existing levers** — `learning=` (which LearningMachine, and which stores on it), `num_history_runs`, `knowledge=`, model id.

Restate the agent's purpose to the user in 1-2 sentences before asking what to change.

## 2. Ask what to improve

Use the coding agent's structured user-input control when available (for example Claude Code's `AskUserQuestion`), otherwise plain text, with these branches. Multi-select is fine — handle the changes sequentially through Steps 3-6, then loop:

- **Add a tool** — new MCP server, agno toolkit, or function tool.
- **Add a capability** — knowledge base (RAG), learning / memory, sub-agent / context provider, scheduled task.
- **Grow the registry** — the lane-2 sibling of "Add a tool": declare a capability in [`app/registry.py`](../../../app/registry.py) so everything the platform *builds* at runtime can carry it, not just this one agent.
- **Refine instructions** — clarify a rule, narrow scope, change tone, change format.
- **Fix a bug** — user has a specific failing prompt or wrong behavior in mind.
- **Something else** — free-form; let the user describe.

Offer "Grow the registry" unprompted when the ask sounds like a *platform* capability rather than one agent's tool — "agents should be able to send Slack messages." Wiring that onto one agent file leaves every Studio-built component without it.

If the user picked "Fix a bug" or "Something else," ask a follow-up free-form question for the specifics (the failing prompt, the observed behavior, what they want instead).

## 3. Ground the change in agno docs

Search the **`agno-docs` MCP** ([`.mcp.json`](../../../.mcp.json)) before writing code, and capture four things: import path, the constructor args that matter here, required env vars, pip dependencies. Fall back to <https://docs.agno.com/llms.txt> only if the MCP is down. Where the docs read loosely, the installed source settles it:

```bash
docker exec agentos-api python -c "import inspect, agno.agent; print(inspect.signature(agno.agent.Agent.__init__))"
```

**Then run the import in the container before you write it.** A missing package is not a degraded agent: `app/main.py` imports every agent at module scope, so the `ImportError` propagates and nothing serves.

```bash
docker exec agentos-api python -c 'from agno.tools.exa import ExaTools'
```

Per branch, the parts the docs can't tell you because they're about this repo:

- **Add a tool** — the toolkit's `Prerequisites` section lists deps and auth. Its absence proves nothing about this image, so run the import anyway.
- **Learning / memory** — the lever is `learning=`. `enable_user_memories` is not a parameter on `Agent` and raises `TypeError`; `enable_agentic_memory` must stay off wherever a LearningMachine is wired, or its `update_user_memory` shadows the store's own. For "it should remember me too", pass `learning=shared_learning` ([`app/learning.py`](../../../app/learning.py)). Declare a new machine only when the store set genuinely differs, and give it `db=` and `model=` explicitly. Entities are Agno's claim ([`teams/lead.py`](../../../teams/lead.py)), so a second component indexing them duplicates the index. `add_history_to_context` is a different lever: it replays the current session and persists nothing.
- **Knowledge** — the platform already has one base, [`app/knowledge.py`](../../../app/knowledge.py); wire `knowledge=shared_knowledge` (one object — the list form belongs to `AgentOS(...)` in `app/main.py`; an agent given a list accepts it and then searches nothing) rather than declaring a second corpus someone then has to keep current.
- **Sub-agent / context provider** — mirror [`agents/engineer.py`](../../../agents/engineer.py): spread `provider.get_tools()` into `tools=`, append `provider.instructions()` to `INSTRUCTIONS`. `ContextMode.tools` mounts the provider's read tools directly; the default gives the parent one `query_<thing>` tool backed by a sub-agent.
- **Scheduled task** — [agno scheduler docs](https://docs.agno.com/agent-os/scheduler), and the `scheduler=True` line in [`app/main.py`](../../../app/main.py).
- **Grow the registry** — [`app/registry.py`](../../../app/registry.py) is the membrane: Platform Builder composes only what it declares. The bucket you declare into decides how a built component references the block (`tool_names`, `model_id`, `knowledge_name`, `learning_name`, `function_name`). Declared entries are buildable; the wiring the framework discovers from registered components at boot resolves but is refused in a build with `tool_not_allowed`. Tool names are global to an agent, so two toolkits exposing `read_file` silently drop the second — `shared_notes` is the registry's one file-like toolkit, so a second `FileSystem` or `Workspace` cannot join it; check first which declared toolkit already claims the name (non-empty means collision), and give any new toolkit `add_instructions=True`. That flag is not optional: a built component's instructions are written by a model, so it is the only channel your usage guidance has.

  ```bash
  docker exec agentos-api python -c "from app.registry import registry; print([t.name for t in registry.tools if 'read_file' in t.functions])"
  ```

- **Refine instructions** — no docs needed. Read the current `INSTRUCTIONS` and propose a minimal diff, narrowing ("on recent-events questions, follow up with a `web_fetch`") rather than forbidding.
- **Fix a bug** — reproduce it on the live agent first (Step 6), then find the layer: `INSTRUCTIONS` (most common), tool, model, or env.

If the docs return nothing for a name the user gave, say so and offer generic `MCPTools(url=..., transport=...)` instead.

## 4. Propose, then edit

Before editing, tell the user in 2-3 lines what you're about to change and why. Get a quick "yes."

Then edit. Files in scope:

- [`agents/<slug>.py`](../../../agents/) (or the component's file — see Step 1's map) — instructions, tools, model, `learning=`, `knowledge=`.
- [`app/registry.py`](../../../app/registry.py) — the "Grow the registry" branch, and nothing else.
- A new module beside it (`app/<thing>.py`) when the block is more than a constructor call — [`app/knowledge.py`](../../../app/knowledge.py), [`app/learning.py`](../../../app/learning.py), and [`app/notes.py`](../../../app/notes.py) each declare one block and get imported by `app/registry.py`.
- [`app/main.py`](../../../app/main.py) — only if registering a new sub-agent, mounting a page the block needs (`knowledge=[...]` is what puts the Knowledge load path in the UI), or changing interface wiring.
- [`app/config.yaml`](../../../app/config.yaml) — update the agent's manifest entry: refresh the `description` if the job changed, and add or update `quick_prompts` to exercise the new capability.
- [`pyproject.toml`](../../../pyproject.toml) — only if a toolkit needs new pip deps.

Keep edits surgical: one change per iteration of this loop, so each can be smoke-tested on its own.

## 5. Restart

- Restart after edits:

  ```bash
  docker compose restart agentos-api
  ```

- **Added pip deps in `pyproject.toml`** — regenerate the lockfile and rebuild:

  ```bash
  ./scripts/generate_requirements.sh
  docker compose up -d --build
  ```

After a restart or rebuild, poll `/health` until the API is back:

```bash
until curl -sSf http://localhost:8000/health > /dev/null; do sleep 0.5; done
```

Confirm the edit reached the container before smoke-testing (`/app/<the file you edited>` — `agents/<slug>.py` for an agent change, `app/registry.py` for a registry one):

```bash
docker exec agentos-api grep -c "<unique substring from your edit>" /app/agents/<slug>.py
```

`0` means the file in the container hasn't changed — almost always a bind-mount mismatch.

## 6. Smoke test the change

Pick a prompt that **exercises the change you just made**: one that forces the new tool to fire, the failing prompt the user described, or one the refined rule was meant to handle. (Targeting the `agno` team? Swap `/agents/<slug>/runs` below for `/teams/agno/runs` — same flags.)

A registry change gets one extra check first — "declared" and "buildable" are different facts. Ask `platform-builder` for the palette row:

```bash
curl -sS -X POST http://localhost:8000/agents/platform-builder/runs \
  -F "message=Call list_tools and show me the row for <tool name> exactly as returned — name, buildable, source. Do not create anything." \
  -F "user_id=claude-extend-agent" -F "stream=false" | jq -r '.content // .'
```

`buildable: true` with `source: declared` means your declaration landed. `source: discovered` means the name reaches the registry through boot discovery rather than `app/registry.py`, and a build wiring it is refused with `tool_not_allowed`. Then the real smoke test: a small build that wires the block, inside the `platform-builder` bracket below.

> **Warning — smoke tests against `platform-builder` mutate the DB.** Its create / edit / publish Studio tools execute immediately (only `archive_component` / `delete_version` / `delete_schedule` pause for confirmation), so a prompt like "build an agent that…" creates and publishes a real component, and can create a schedule that keeps firing daily. Prefer a plan-only probe ("Which registry components would you pick for X? Do not create anything."), or bracket the run: `snapshot_builder_state()` before, `delete_new_builder_state(pre)` after, from [`evals/hooks.py`](../../../evals/hooks.py) — it hard-deletes new components, schedules, and learning rows alike (the `cleanup_new_*` names beside them are the async eval hooks, which take a `CaseResult`). The same applies when reproducing a bug on `platform-builder` in Step 3.

> **Warning — smoke tests against a learning component write durable rows.** `agno`, `platform-manager`, `platform-engineer`, and anything else carrying `learning=` capture ungated: a prompt that tells the agent something files it, and Agno's notes and entities are shared by everyone on the platform. Make every fixture something no real team would have on file (invented names, invented projects), and never smoke with a real decision or a real person's details: the sweep removes rows a run *created* and cannot undo an edit *inside* a row that already existed. Bracket the whole session, rather than each prompt, with the `snapshot_learning_state` / `delete_new_learning_state` pair from [`evals/hooks.py`](../../../evals/hooks.py) — the full snippet is in [improve-agent Step 2](../improve-agent/SKILL.md). Skip the pair when the target is `platform-builder` — its bracket above already sweeps learning state. Never run the delete side while someone else is talking to Agno: the diff is by row identity, so a note a teammate files during your session looks new and gets swept. On a busy platform, either smoke-test in a window you own, or leave the rows in place and tell the user in Step 8 exactly what the smoke prompts filed, so they can retire it themselves.

```bash
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<the targeted prompt>" \
  -F "user_id=claude-extend-agent" \
  -F "stream=false" \
  -o /tmp/improve-out.json \
  -w "HTTP %{http_code} in %{time_total}s\n"

jq -r '.content // .' < /tmp/improve-out.json
```

Read tool calls from the container logs to confirm the right tool fired:

```bash
docker logs agentos-api --since 30s 2>&1 | grep -E "Running: \w+\(" | head -40
```

(`Running: <tool>(` is the line shape agno emits per tool call when `AGNO_DEBUG=True`, which compose sets for dev.)

Show the user the response and the tool calls. Did the change land?

- **Yes** — go to Step 7.
- **Almost** — one more edit pass. Iterate at most 2-3 times before stopping and asking the user how they want to proceed (revert, try a different approach, accept and move on).
- **No / made it worse** — surface what happened. Offer to revert only your last patch after showing `git diff agents/<slug>.py`; do not discard unrelated user edits.

## 7. Loop or wrap up

Ask the user (free-form): *"Anything else to improve, or are we done?"*

- **More to do** — go back to Step 2.
- **Done** — Step 8.

## 8. Report

Summarize for the user:

- One line per accepted change (which lever, what changed).
- `git diff --stat` plus a short `git diff` block for the agent file.
- Suggested commit message — `feat(<slug>): <one-line>` for new tools/capabilities, `fix(<slug>): <one-line>` for bug fixes, `chore(<slug>): refine instructions` for prompt-only edits. Combine if multiple types in one session.
- **Recommended next step** — run [`improve-agent`](../improve-agent/SKILL.md) to autonomously verify the agent still does what its `INSTRUCTIONS` say it does.

---

## Worked example

Target: the `agno` team ([`teams/lead.py`](../../../teams/lead.py)). The user wants Agno to also be able to read pages and PDFs from URLs, so "file this link" captures the content, not just the address.

**Step 2** — user picks "Add a tool."

**Step 3** — search the agno-docs MCP for "PDF" and "fetch." Find `agno.tools.jina` (`JinaReaderTools`: any URL or PDF to clean markdown) — capture the import, the env var (`JINA_API_KEY`, optional: keyless works, a key raises the rate ceiling), and that it needs no extra package. The import check in the container passes.

**Step 4** — propose: *"Add `JinaReaderTools` so `agno` can fetch and parse the links you hand it before filing them. No new dependency; works keyless, set `JINA_API_KEY` for higher limits. Add a quick prompt that exercises a PDF URL."* User says yes.

Edit `teams/lead.py` to import `JinaReaderTools` and add it to `tools=[notes.tools(), web_tools, studio_runners, JinaReaderTools()]`. Check its tool name (`read_url`) against what the leader already carries — a name that collides gets dropped with a `Duplicate tool name` warning rather than an error. Optionally add `JINA_API_KEY=` to [`example.env`](../../../example.env). Add a quick prompt to the team's manifest entry in `app/config.yaml`:

```yaml
manifest:
  agno:
    quick_prompts:
      - "Read https://arxiv.org/pdf/2501.12948 and file what matters"
```

**Step 5** — no new pip deps: `docker compose restart agentos-api`, then poll `/health`.

**Step 6** — the prompt ends in a write to the shared notebook, so take the learning snapshot first. Then cURL the team (`POST /teams/agno/runs`) with the quick prompt. Logs show `Running: read_url(` against the arxiv URL, then a note write with the distilled content. Run the delete side of the bracket afterward.

**Step 7** — user says "no, that's it."

**Step 8** — diff summary, commit `feat(agno): add JinaReaderTools for URL and PDF capture`, recommend the `improve-agent` skill.

## A second worked example: growing the registry

Target: the platform, not an agent. The user says *"agents you build should be able to read pages and PDFs too."*

**Step 2** — "Grow the registry." The tell is the plural: *agents you build*, not *this agent*.

**Step 3** — the block is a tool, so it goes in the registry's `tools=[...]` and a built component references it by `tool_names`. The docs work is the first example's (`JinaReaderTools`, no extra package, keyless). The registry-specific question is the name: its one function is `read_url`, and `docker exec agentos-api python -c "from app.registry import registry; print([t.name for t in registry.tools if 'read_url' in t.functions])"` prints `[]`, so no declared toolkit drops it (the bare import lists declared toolkits only, which is the right set — discovered ones cannot be wired into a build anyway). The toolkit ships no usage instructions of its own, so `add_instructions=True` needs an `instructions=` string beside it: when to fetch, and that a PDF URL works as-is.

**Step 4** — propose: *"Add `JinaReaderTools(instructions=..., add_instructions=True)` to `app/registry.py`'s `tools=[...]` so any built agent can turn a URL or PDF into clean markdown. No new dependency; keyless, `JINA_API_KEY` raises the limit. Only `app/registry.py` changes."* User says yes. Add the import and the entry.

**Step 5** — no new pip deps, so `docker compose restart agentos-api` and poll `/health`; `grep -c JinaReaderTools /app/app/registry.py` in the container is non-zero.

**Step 6** — the palette check first: `jina_reader_tools` comes back `buildable: true`, `source: declared`. Then, inside the builder bracket, one build that wires `jina_reader_tools` and a run that reads a fixture URL. Logs show `Running: read_url(`.

**Step 8** — commit `feat(registry): expose JinaReaderTools to built components`. The follow-up is not `improve-agent` — no existing agent changed — but a line in [`AGENTS.md`](../../../AGENTS.md)'s registry inventory, because the membrane's contents are documented there.
