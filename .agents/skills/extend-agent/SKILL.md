---
name: extend-agent
description: User-driven loop to change an existing agent in this AgentOS — add a tool/MCP server/toolkit, add a capability (knowledge base, learning/memory, sub-agent, scheduled task), grow the safe Studio registry so components built at runtime gain a new capability, refine its instructions, or fix a specific known bug, verifying each change against the live container. Use whenever the user names a concrete change to an agent, or wants a new building block available to the platform. For autonomous hardening with no specific change in mind, use improve-agent.
---

# Extend an Agent

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/extend-agent`) or describe the task and it triggers automatically._

You are recursively extending a target agent **with the user in the driver's seat**. Each iteration: the user names a change, you implement it with an Agno-aware eye (using the `agno-docs` MCP for any toolkit / API research), the change is verified against the live agent, then you ask if there's more to do. Stop when the user says they're done.

This is the user-driven half of the iteration loop. The autonomous half lives in [`improve-agent`](../improve-agent/SKILL.md) — Claude derives probes from the agent's `INSTRUCTIONS` and recorded usage, and hardens behavior with no user input. Run it afterward to confirm nothing else regressed.

The platform is on `http://localhost:8000` (`RUNTIME_ENV=dev`). Compose runs uvicorn with a scoped `--reload`, so code edits are picked up automatically; restart `agentos-api` for dependency changes or a guaranteed-clean state — Step 5 covers this.

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

**First, confirm the slug has a file at all.** A runnable id on this platform is either code (a file in `agents/`, `teams/`, or `workflows/`, registered in `app/main.py`) or a Studio-built component that lives only in the database. The listing endpoints label which:

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\tis_component=\(.is_component)"'
```

`is_component=true` means there is no source file to open. Resolution checks the code list passed to `AgentOS(agents=[...])` first and only falls through to the database on a miss, so a new `agents/<slug>.py` registered in [`app/main.py`](../../../app/main.py) under an id the Studio already publishes *shadows* the runtime component rather than editing it — every run goes to your file while the user's actual component sits untouched behind it, and it looks like it worked. Route that ask to Platform Builder instead (`edit_agent` / `edit_team` / `edit_workflow`, then `publish_component`), and stay in this skill only if the user's real intent is to *replace* the built component with a code one, which starts by archiving it. `/teams` and `/workflows` carry the same field.

Then open the component's file — `agents/<slug>.py` for user-built agents; the reference components map ids to files: `platform-builder` → [`agents/builder.py`](../../../agents/builder.py), `platform-manager` → [`agents/manager.py`](../../../agents/manager.py), `platform-engineer` → [`agents/engineer.py`](../../../agents/engineer.py), the `agno` team → [`teams/lead.py`](../../../teams/lead.py). Capture:

- **Stated purpose** — the file's docstring + the `INSTRUCTIONS` string.
- **Tools** — what's wired and what each one does.
- **Pattern** — direct tools (like the notes toolkit in [`teams/lead.py`](../../../teams/lead.py), which also composes a `learning=` machine), context provider (the `WorkspaceContextProvider` wiring in [`agents/engineer.py`](../../../agents/engineer.py), run in tools mode for direct reads), or a mix (Platform Manager pairs the read-only `AgentOSTools` runtime toolkit with the deployment-check functions; Platform Builder is the Studio-tools pattern).
- **Existing levers** — `learning=` (which LearningMachine, and which stores on it), `num_history_runs`, `knowledge=`, model id.

Restate the agent's purpose to the user in 1-2 sentences before asking what to change. This catches "I thought it did X but actually it does Y" upfront.

## 2. Ask what to improve

Use the coding agent's structured user-input control when available (for example Claude Code's `AskUserQuestion`) with these branches. If no structured control is available, ask the same choices in concise plain text. Multi-select is fine if the user wants multiple changes in one pass — handle them sequentially in Steps 3-6, then loop:

- **Add a tool** — new MCP server, agno toolkit, or function tool.
- **Add a capability** — knowledge base (RAG), learning / memory, sub-agent / context provider, scheduled task.
- **Grow the registry** — the lane-2 sibling of "Add a tool": declare a capability in [`app/registry.py`](../../../app/registry.py) so everything the platform *builds* at runtime can carry it, not just this one agent.
- **Refine instructions** — clarify a rule, narrow scope, change tone, change format.
- **Fix a bug** — user has a specific failing prompt or wrong behavior in mind.
- **Something else** — free-form; let the user describe.

"Grow the registry" is worth offering unprompted when the ask sounds like a *platform* capability rather than one agent's tool — "agents should be able to send Slack messages." Wiring that onto one agent file leaves every Studio-built component without it.

If the user picked "Fix a bug" or "Something else," ask a follow-up free-form question for the specifics (the failing prompt, the observed behavior, what they want instead).

## 3. Ground the change in agno docs

For any change touching agno surface area — toolkit imports, knowledge config, learning stores, registry blocks, scheduler, sub-agent patterns — search the **`agno-docs` MCP** (configured in [`.mcp.json`](../../../.mcp.json)) before writing code. Fall back to fetching <https://docs.agno.com/llms.txt> only if the MCP is unavailable. For anything the docs describe loosely, the installed source is the tiebreaker: `docker exec agentos-api python -c "import inspect, agno.agent; print(inspect.signature(agno.agent.Agent.__init__))"` settles whether a constructor argument exists on the version this platform actually runs.

What to capture per branch:

- **Add a tool** — import path (e.g. `from agno.tools.exa import ExaTools`), constructor args that matter for this agent, required env vars, pip dependencies. The toolkit's `Prerequisites` section lists deps and auth.
- **Add a capability**:
  - *Knowledge base* — `from db import create_knowledge`, instantiate with a name + table, pass via `knowledge=` on the Agent. Document load step (`.add_content_async()`) goes wherever ingestion lives.
  - *Learning / memory* — the lever is `learning=`, not the legacy memory flags. `enable_user_memories` no longer exists on `Agent` in agno 3.0 (not a parameter, so passing it raises `TypeError`), and `enable_agentic_memory` must stay `False` anywhere a LearningMachine with a `user_memory` store is wired: it registers a tool named `update_user_memory`, tool parsing keeps the first name it sees, and the learning store's tool of that name is dropped. All four reference components carry such a machine, so on this repo that flag is always the wrong answer.
    - *Join the platform's self* — the usual ask ("this agent should remember me too"). Import `shared_self` from [`app/learning.py`](../../../app/learning.py) and pass `learning=shared_self`, the same machine [`agents/manager.py`](../../../agents/manager.py) and [`agents/engineer.py`](../../../agents/engineer.py) carry. Its two stores are `user_profile` and `user_memory`, both `LearningMode.AGENTIC` — the tools (`update_profile`, `update_user_memory`) exist only on runs carrying a user id, and recall is automatic (`add_learnings_to_context` defaults True). This is a join, not a copy: rows are keyed by user id alone (`user_profile_<user_id>`, `memories_<user_id>`), so on one database there is no component-private self to create.
    - *Add a store* — a `LearningMachine` takes `user_profile`, `user_memory`, `session_context`, `entity_memory`, `learned_knowledge`, and `decision_log`, each off by default and each accepting `True`, its `*Config`, or a store instance; the mode on a config is `always`, `agentic`, `propose`, or `hitl`. Stores bring their own tools — `entity_memory` adds `remember_about`, `link_entities`, `search_entities`, `forget`; `learned_knowledge` adds `search_learnings` and `save_learning`. Check one-claim-one-home before adding one: entities are already Agno's claim ([`teams/lead.py`](../../../teams/lead.py) declares `entity_memory` on namespace `global`), so a second component indexing entities duplicates the index rather than extending it. Declaring a *new* machine is the right move only when the store set genuinely differs; give it `db=` and `model=` explicitly, for the reason [`app/learning.py`](../../../app/learning.py) documents.
    - *Session recall is a different lever* — `add_history_to_context` and `num_history_runs` replay recent turns of the current session and do not persist across sessions. Reach for them when the agent loses the thread mid-conversation, and for `learning=` when it should still know something next week.
    - *For a built component, the same self has a name* — `shared_self` is registered as `user-self`, so Platform Builder wires it with `learning_name="user-self"`. That is a registry concern, not a file edit — see the "Grow the registry" branch.
  - *Sub-agent / context provider* — mirror the `WorkspaceContextProvider` wiring in [`agents/engineer.py`](../../../agents/engineer.py): instantiate the provider, spread `provider.get_tools()` into `tools=[...]`, and append `provider.instructions()` to `INSTRUCTIONS`. In the default mode the parent sees one `query_<thing>(question)` tool and a sub-agent does the work; `engineer.py` opts into `ContextMode.tools` so the agent gets the provider's read tools (`read_file`, `list_files`, `search_content`) directly.
  - *Scheduled task* — see [agno scheduler docs](https://docs.agno.com/agent-os/scheduler) and the `scheduler=True` line in [`app/main.py`](../../../app/main.py).
- **Grow the registry** — [`app/registry.py`](../../../app/registry.py) is the membrane between the two lanes: Platform Builder composes what it declares, so a reviewed edit here is the *only* route to new runtime capability. Four things to get right, in order:
  1. *Declare the block in the right bucket.* `Registry(...)` takes `tools`, `models`, `dbs`, `vector_dbs`, `schemas`, `functions`, `knowledge`, `learning`, `memory_managers`, `session_summary_managers`, `agents`, `teams`, and `workflows`. The bucket decides how a built component references it: `tool_names` for tools, `model_id` for a model, `knowledge_name` for a base, `learning_name` for a machine, `function_name` on a workflow step for a function, `member_ids` for agents joining a built team. Follow the file's shape — a `get_<thing>_tools()` helper returning a list, spread into the constructor. The registry is imported at boot by [`app/main.py`](../../../app/main.py), so a block whose dependency might be absent returns `[]` rather than raising; `get_slack_tools` and `get_media_tools` are the pattern.
  2. *Decide buildable vs. discovered.* Only **declared** entries are buildable. At boot the framework also folds every OS-registered component's own wiring into the live registry — those tools resolve (so an existing component keeps working) but are **not** buildable, and wiring one into a build is refused with `tool_not_allowed`. `list_tools` reports both facts per row: `buildable`, and `source` of `declared` or `discovered`.
  3. *Mind the flat tool namespace.* Tool names are global to an agent, not scoped by their toolkit. Mount two toolkits that both expose `read_file` and agno logs `Duplicate tool name 'read_file' from toolkit '<name>' already registered on agent; skipping the duplicate` and drops the second — the model never sees it, so the symptom is a capability that silently does nothing. `agent_files` already claims `read_file`, `list_files`, and `search_content`. Check candidate names before you add them — `registry.tool_is_declared(name)` answers for a top-level toolkit name and a toolkit member alike:

     ```bash
     docker exec agentos-api python -c "from app.registry import registry; print(registry.tool_is_declared('read_file'))"
     ```

     On a collision, wrap the operations you actually want in plainly named functions and give them their own `Toolkit(name=..., tools=[...], instructions=..., add_instructions=True)`. Renaming also lets you narrow: `app/notes.py` exposes create and append but no replace or delete, because a shared notebook should not let a built agent retire a colleague's note.
  4. *Write the guidance in.* A built component's instructions are written by a model at build time, not by you, so `add_instructions=True` on the toolkit is the only channel your usage guidance has into it. `get_agent_files_tools` and `get_shared_notes_tools` both set it.
- **Refine instructions** — no docs needed. Read the current `INSTRUCTIONS`, propose a minimal diff. Prefer narrowing ("on recent-events questions, follow up with a `web_fetch`") over forbidding.
- **Fix a bug** — first reproduce the failure on the live agent (see Step 6). Then identify the layer: `INSTRUCTIONS` (most common), tool (wrong tool wired or missing), model (under-capable), env (rate limit, missing key, MCP unreachable).

Don't guess any of these. If the agno-docs MCP returns nothing for a name the user gave (e.g. an MCP server they want to wire), tell them; offer to use generic `MCPTools(url=..., transport=...)` and ask for the URL.

## 4. Propose, then edit

Before editing, tell the user in 2-3 lines what you're about to change and why. Get a quick "yes."

Then edit. Files in scope:

- [`agents/<slug>.py`](../../../agents/) (or the component's file — see Step 1's map) — instructions, tools, model, `learning=`, `knowledge=`.
- [`app/registry.py`](../../../app/registry.py) — the "Grow the registry" branch, and nothing else.
- A new module beside it (`app/<thing>.py`) when the block is more than a constructor call — [`app/knowledge.py`](../../../app/knowledge.py), [`app/learning.py`](../../../app/learning.py), and [`app/notes.py`](../../../app/notes.py) each declare one block and get imported by `app/registry.py`.
- [`app/main.py`](../../../app/main.py) — only if registering a new sub-agent, mounting a page the block needs (`knowledge=[...]` is what puts the Knowledge load path in the UI), or changing interface wiring.
- [`app/config.yaml`](../../../app/config.yaml) — update the agent's manifest entry: refresh the `description` if the job changed, and add or update `quick_prompts` to exercise the new capability.
- [`pyproject.toml`](../../../pyproject.toml) — only if a toolkit needs new pip deps.

Keep edits surgical. One change per iteration of this loop — if the user asked for three things, do them one at a time so each can be smoke-tested independently.

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

Pick a prompt that **exercises the change you just made**. For "Add a tool," the prompt should force the new tool to fire. For "Fix a bug," reuse the failing prompt the user described. For "Refine instructions," pick a prompt the rule was meant to handle. (Targeting the `agno` team? Swap `/agents/<slug>/runs` below for `/teams/agno/runs` — same flags.)

A registry change gets one extra check first, because "the block is declared" and "a build can wire it" are different facts. Ask `platform-builder` to list the palette and read the row:

```bash
curl -sS -X POST http://localhost:8000/agents/platform-builder/runs \
  -F "message=Call list_tools and show me the row for <tool name> exactly as returned — name, buildable, source. Do not create anything." \
  -F "user_id=claude-extend-agent" -F "stream=false" | jq -r '.content // .'
```

`buildable: true` with `source: declared` means your declaration landed. `source: discovered` means the name is reaching the registry through the boot fold rather than through `app/registry.py`, and a build wiring it will be refused with `tool_not_allowed`. Only then is the real smoke test worth running: a small build that actually wires the block, under the `platform-builder` bracket below.

> **Warning — smoke tests against `platform-builder` mutate the DB.** Its create / edit / publish Studio tools execute immediately (create/edit produce drafts, but the builder's instructions make `publish=true` the default completion — only `archive_component` / `delete_version` / `delete_schedule` pause for confirmation), so a prompt like "build an agent that…" creates and publishes a real component, and can create a schedule that keeps firing daily. Prefer a plan-only probe ("Which registry components would you pick for X? Do not create anything."), or snapshot state before the run and hard-delete anything new afterward — `snapshot_builder_state()` then `delete_new_builder_state(pre)` from [`evals/cases.py`](../../../evals/cases.py) (components plus schedules plus learning rows — the builder carries the shared per-user profile/memory stores; the `cleanup_new_*` names beside them are the async eval hooks, which take a `CaseResult`). The same applies when reproducing a bug on `platform-builder` in Step 3.

> **Warning — smoke tests against a learning component write durable rows.** `agno`, `platform-manager`, `platform-engineer`, and anything else carrying `learning=` capture ungated: a prompt that tells the agent something files it, and Agno's notes and entities are shared by everyone on the platform. Two rules: make every fixture something no real team would have on file (invented names, invented projects), and never smoke with a real decision or a real person's details, because the diff below removes rows a run *created* and cannot undo an edit *inside* a row that already existed. The bracket, around the whole session rather than each prompt:
>
> ```bash
> source .venv/bin/activate
>
> # before the first smoke prompt
> python -c "
> from dotenv import load_dotenv; load_dotenv()
> import json
> from evals.cases import snapshot_learning_state
> print(json.dumps({k: sorted(v) for k, v in snapshot_learning_state().items()}))" > /tmp/pre-extend-learning.json
>
> # after the last one — removes only what the session created
> python -c "
> from dotenv import load_dotenv; load_dotenv()
> import json
> from evals.cases import delete_new_learning_state
> delete_new_learning_state({k: set(v) for k, v in json.load(open('/tmp/pre-extend-learning.json')).items()})"
> ```
>
> Skip this pair when the target is `platform-builder` — its bracket above already sweeps learning state. And do not run the delete side at all if someone else is talking to Agno while you work: the diff is by row identity, so a note a teammate files during your session looks new and gets swept. On a busy platform, either smoke-test in a window you own, or leave the rows in place and tell the user in Step 8 exactly what the smoke prompts filed, so they can retire it themselves.

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

A simple change (one tool, one prompt refinement) takes 5-10 minutes. A capability addition (knowledge base, sub-agent) usually 15-30.

---

## Worked example

Target: the `agno` team ([`teams/lead.py`](../../../teams/lead.py)). The user wants Agno to also be able to read pages and PDFs from URLs, so "file this link" captures the content, not just the address.

**Step 2** — user picks "Add a tool."

**Step 3** — search the agno-docs MCP for "PDF" and "fetch." Find that Agno's existing Parallel web tools already cover fetching HTML pages, but PDF parsing isn't included. Find `agno.tools.jina` (Jina Reader turns any URL, PDF, or HTML into clean markdown) — capture import, env var (`JINA_API_KEY`, optional — it works keyless, a key just raises the rate ceiling), pip dep (`jina`).

**Step 4** — propose: *"Add `JinaReaderTools` so `agno` can fetch and parse the links you hand it before filing them. Needs `jina` in `pyproject.toml`; works keyless, set `JINA_API_KEY` for higher limits. Add a quick prompt that exercises a PDF URL."* User says yes.

Edit `teams/lead.py` to import `JinaReaderTools` and add it to `tools=[notes.tools(), web_tools, studio_runners, JinaReaderTools()]`. Check the new toolkit's tool names against what Agno already carries — the leader is already holding a `FileSystem` toolkit, and a name that collides gets dropped with a `Duplicate tool name` warning rather than an error. Add `jina` to `pyproject.toml` (and optionally `JINA_API_KEY=` to [`example.env`](../../../example.env)). Add a quick prompt to the team's manifest entry in `app/config.yaml`:

```yaml
manifest:
  agno:
    quick_prompts:
      - "Read https://arxiv.org/pdf/2501.12948 and file what matters"
```

**Step 5** — pip deps changed: `./scripts/generate_requirements.sh && docker compose up -d --build`. Poll `/health`.

**Step 6** — this smoke test ends in a note write, and the notebook is shared, so take the learning snapshot from Step 6's second warning first. Then cURL the team (`POST /teams/agno/runs`) with the quick prompt. Logs show `Running: read_url(` against the arxiv URL, then a note write with the distilled content. Run the delete side of the bracket afterward so the platform's notebook goes back to what the team actually filed.

**Step 7** — user says "no, that's it."

**Step 8** — diff summary, commit `feat(agno): add JinaReaderTools for URL and PDF capture`, recommend the `improve-agent` skill to harden the broader behavior.

## A second worked example: growing the registry

Target: the platform, not an agent. The user says *"agents you build should be able to leave notes where the rest of the team can see them."* Today only Agno can write to the shared notebook, and a built agent's `agent_files` store is private to it.

**Step 2** — "Grow the registry." The tell is the plural: *agents you build*, not *this agent*.

**Step 3** — the block is a tool. The obvious move — declare a second `FileSystem` toolkit over the `brain` namespace — fails on the flat namespace: `agent_files` already claims `read_file`, `list_files`, and `search_content`, so an agent carrying both would silently lose one set. Confirm it rather than assume it: `docker exec agentos-api python -c "from app.registry import registry; print(registry.tool_is_declared('read_file'))"` returns `True`. So the shape is purpose-named functions instead — and the rename buys a narrower surface for free: create and append, no replace and no delete.

**Step 4** — propose: *"A new `app/notes.py` that declares the `brain` FileSystem once, plus five named functions — `read_shared_note`, `write_shared_note`, `append_shared_note`, `list_shared_notes`, `search_shared_notes` — wrapped in a `shared_notes` toolkit with `add_instructions=True`. `teams/lead.py` imports the FileSystem from there instead of declaring its own; `app/registry.py` exposes the toolkit. A built agent can then carry `agent_files` and `shared_notes` together."* User says yes. Write the module, spread `*get_shared_notes_tools()` into the registry's `tools=[...]`, repoint `teams/lead.py` at the shared declaration.

**Step 5** — no new pip deps, so `docker compose restart agentos-api` and poll `/health`.

**Step 6** — the palette check first: ask `platform-builder` for the `list_tools` row and confirm `shared_notes` comes back `buildable: true`, `source: declared`. Then, inside the builder bracket, one real build that wires both stores and a run that files something under a fixture name. Both toolkits' tools appear in the logs; nothing is dropped.

**Step 8** — commit `feat(registry): expose the shared notebook to built components`. The follow-up is not `improve-agent` this time — nothing about an existing agent changed. It is a line in [`AGENTS.md`](../../../AGENTS.md)'s registry inventory, because the membrane's contents are documented there.
