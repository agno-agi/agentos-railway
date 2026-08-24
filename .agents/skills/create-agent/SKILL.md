---
name: create-agent
description: Add a new agent to this AgentOS. Runs guided discovery or takes a concrete idea, then generates agents/slug.py, registers it in app/main.py, adds its manifest entry (description + quick prompts), restarts the container, and smoke-tests it live. Use whenever the user wants to add or create a new agent.
---

# Create a New Agent

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/create-agent`) or describe the task and it triggers automatically._

You are creating a new agent in this AgentOS. The user already has the platform running locally on `http://localhost:8000` (`RUNTIME_ENV=dev`); code edits hot-reload (Step 6).

## 0. Preconditions

- Live container reachable: `curl -sSf http://localhost:8000/health` returns 200. (`docker compose ps` is unreliable from worktrees or alternate clones — trust the health probe.)

If it isn't reachable, ask the user to run `docker compose up -d --build` and wait for it to come up.

## 1. Find the agent worth building

**Be self-driving: ask only what needs a human, decide the rest, and say what you decided.** Two exchanges is the target — one to understand the job, one to confirm what you'll build.

Use the coding agent's structured user-input control when available (Claude Code's `AskUserQuestion`, Codex's user-input tool, or an equivalent) for the choice-shaped questions below. Use plain prompts for free-form answers.

### Two lanes, and this is yours

Agents live in two places here. **Lane 1 is a source file in `agents/`, governed by git — this skill.** Lane 2 is a component Platform Builder composes at runtime from the registry, for people who aren't writing code. The user is here, so build the file.

Lane 1 is the only one that can touch the repo, so it owns anything needing a code change: a toolkit or MCP server the registry doesn't carry, custom Python, a new dependency, a new skill, or growing [`app/registry.py`](../../../app/registry.py) — which is how lane 2 gets its blocks in the first place.

**Check the id is free first.** Both lanes share an id space and code wins, so a file under a taken id doesn't error — it makes the runtime component vanish from `/agents` and from Agno's dispatch, rows still in the database.

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\t\(.is_component)"'
```

`is_component: true` marks the Studio-built ones; pick a different slug. Same check on `/teams` and `/workflows`. If the ask was really "change *that* agent" and it's a component, there's no file to edit — that one's Platform Builder's.

### If they already named an agent

"Build me a GitHub PR reviewer" is a complete brief. **Ask nothing.** Design it (Step 2), then state what you're building in one message and start:

> Building **PR Reviewer** (`pr-reviewer`) — reads open PRs on a repo and summarizes what changed and what looks risky. Uses `GithubTools`; needs `GITHUB_ACCESS_TOKEN`, which is already in your `.env`. Building now — stop me if I've read it wrong.

Don't wait for a reply. Only pause if something is genuinely missing (see **Stop only for this**).

### If they want guidance

Open with **one** question:

> What's something you do every week that you'd rather hand off?

Their first answer will be vague — *"I keep up with what competitors ship"*. **Dig once:** a generic answer yields a generic agent, and nobody keeps one.

Ask one grounded follow-up, in their own terms — whichever unlocks the design:

- Where do you look when you do it? (Which repos, sites, channels, tools?)
- What do you do with the result — post it, file it, decide from it?
- What's the annoying part — the volume, the context-switching, the writing-up?

Then propose **one agent you recommend**, plus two alternates — a recommendation with a fallback, not a menu. For each: a name, one sentence on what it does, and the toolkit(s) behind it, grounded in the `agno-docs` MCP ([`.mcp.json`](../../../.mcp.json)) — never invent one.

Skip the demo classics (news digest, generic web researcher) unless that's what they described.

### Decide these yourself — don't ask

| Decision | How you decide it |
|---|---|
| **Pattern** | **Direct tools** (the required structure in Step 3; [`agents/manager.py`](../../../agents/manager.py) shows it live) when the agent uses ≤2 toolkits — the common case. **Context provider** (mirror the `codebase` wiring in [`agents/engineer.py`](../../../agents/engineer.py)) when it queries one information source — a single `query_<thing>` tool by default, or the provider's direct read tools in `ContextMode.tools` as the engineer does. Pick one and mention it in a clause. |
| **Slug** | Derive it from the purpose (`pr-reviewer`, `linear-triager`). Kebab-case. State it. |
| **Model** | `default_model()` (`gpt-5.6`). Override only if the user asks. |
| **Toolkits** | Choose from what the discovery answers imply, grounded in agno docs (Step 2). Prefer what is already in this image and needs no key — the keyless Parallel MCP for anything web-facing, `HackerNewsTools`, `CalculatorTools`, the shared notebook's scoped tools (`get_shared_notes_tools()`, [`app/notes.py`](../../../app/notes.py)) for files and state. Anything beyond that set costs a rebuild or a key, and an unverified import takes down the platform — check it in the container (Step 2). |
| **Memory / history** | **Wire `learning=shared_learning`** ([`app/learning.py`](../../../app/learning.py)) whenever the agent should know the person it works for across sessions — most agents worth keeping. It joins the new agent to the same per-user self Agno and the three platform agents carry. Leave it off only when the agent's durable state isn't per-user (Step 3 notes). History defaults come from the template pattern. Don't ask either way; say which you did. |

### Stop only for this

An API key that the chosen toolkit **requires** and that isn't in `.env`. Check `.env` yourself first — don't ask the user what's in a file you can read. If a key is genuinely missing, say which toolkit needs it and offer the two real choices:

- add the key to `.env` now (they paste it in; never read or print it), or
- swap to a toolkit that's keyless *and already in the image* — verify the import (Step 2) before you offer it — or a variant of the idea that is, and build now. (Some jobs have no such route; then the key is the only choice — say so plainly.)

Everything else — proceed and report.

## 2. Ground the design in agno docs

For every toolkit, MCP server, or integration the agent will use (Linear, Stripe, GitHub, …), search agno docs **before** writing code:

- Preferred: the `agno-docs` MCP server (configured in [`.mcp.json`](../../../.mcp.json)) — search for the toolkit / integration name and read the relevant page(s).
- Fallback: fetch <https://docs.agno.com/llms.txt> and search inline for the relevant sections.

For each toolkit, capture four things:

- **Import path** (e.g. `from agno.tools.exa import ExaTools`).
- **Constructor args** that matter for this agent (categories, domains, max_results, etc.).
- **Required env vars** — check them against `.env` (Step 1, **Stop only for this**).
- **Pip dependencies** — some toolkits need extra packages (`exa-py`, `anthropic`, `jina`, `yfinance`, …). The toolkit's `Prerequisites` section lists them. Capture now, then add them to `pyproject.toml` before generating `requirements.txt` in Step 6.

Don't guess any of the four. Skip this step entirely if the agent is chat-only with no tools.

### The image decides dependencies, not the docs page

**Verify the import in the container before you write it.** 85 toolkit modules in this image import their third-party package at module scope and raise `ImportError` when it's missing. That is not a degraded agent, it's a dead platform: `app/main.py` imports every registered agent at module scope, so the `ImportError` propagates out of `app.main`, uvicorn's reload fails, and **nothing serves** — including the agents that worked a minute ago.

```bash
docker exec agentos-api python -c 'from agno.tools.exa import ExaTools'
```

Silence means it's there. An `ImportError` names the package: either add it to `pyproject.toml` and take the rebuild path in Step 6, or pick a different toolkit.

A docs page with no `Prerequisites` section proves nothing about this image: `ArxivTools` (`arxiv`, `pypdf`), `WikipediaTools` (`wikipedia`), and `WebSearchTools` / `DuckDuckGoTools` (`ddgs`) are all key-free and still fail to import here. Of the usual keyless suspects only `HackerNewsTools` is in the image.

**For web search there is exactly one route that needs neither a key nor a rebuild** — the keyless Parallel MCP this platform already runs on ([`teams/lead.py`](../../../teams/lead.py), [`app/registry.py`](../../../app/registry.py)):

```python
from agno.tools.mcp import MCPTools

# Keyless. AgentOS connects and closes MCP servers as part of its lifespan.
# timeout_seconds: web_fetch page extraction regularly exceeds the 10s MCP default.
web_tools = MCPTools(
    url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
)
```

It exposes two tools, `web_search` and `web_fetch`. (`ParallelTools()` is the SDK path the same two files switch to when `PARALLEL_API_KEY` is set — mirror it only if the user has that key.)

## 3. Generate the agent file

Create `agents/<slug>.py` (replacing `-` with `_` for the filename: `agents/linear_agent.py`). Follow the closest reference pattern:

- **Direct tools** → follow the required structure below. [`agents/manager.py`](../../../agents/manager.py) is the live example.
- **Context provider** → mirror the `codebase` part of [`agents/engineer.py`](../../../agents/engineer.py): build the `WorkspaceContextProvider`, unpack `*provider.get_tools()` into `tools=`, and append `provider.instructions()` to the agent's instructions — without it the agent holds tools nobody explained.
- **Studio builder** → mirror [`agents/builder.py`](../../../agents/builder.py) when the agent should create or refine AgentOS components through StudioTools.

Required structure (no `offload_tool_results` — result offloading is for the four platform agents only; a new agent does not get it):

```python
"""
<Title>
=======
"""

from agno.agent import Agent

from app.learning import shared_learning
from app.settings import default_model
from db import get_postgres_db

INSTRUCTIONS = """\
You are <DisplayName>: <the agent's job, in one line>.

How you speak:
- <one rule per line: tone, length, what to confirm>

How you <work>:
- <one rule per line: which tool for what, what to refuse, what to hand off>
- <a sequence is a numbered list; no rationale, no examples longer than a clause>\
"""

<slug_underscore> = Agent(
    id="<slug>",
    name="<DisplayName>",
    model=default_model(),
    db=get_postgres_db(),
    # The learning machine attaches its tools, guidance, and recall automatically.
    learning=shared_learning,
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    tools=[...],                     # or context_provider.get_tools()
    instructions=INSTRUCTIONS,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

Notes:

- **Drop the `learning=` / `user_id` pair only for a deliberate reason, and comment the reason in the file.** Per-user is the wrong shape when the agent's durable state belongs to the platform rather than to a person — a ledger of what it has already reported, a queue, anything a scheduled run has to read back: profile and memory rows are keyed by user id alone, so state filed there is invisible to the next user and to any run without one. File that state in the shared notebook, the platform's one file store ([`app/notes.py`](../../../app/notes.py)): `tools=[*get_shared_notes_tools(), ...]` mounts `read_file`, `append_file`, `list_files`, `search_content`, and `check_lines` over the `shared-notes` namespace and carries its own usage instructions (append nothing to `INSTRUCTIONS` for it); the agent keeps its working files in a directory named after it (`<slug>/`). Keep learning for what the agent knows about its human.
- Don't add a `if __name__ == "__main__":` smoke block — the platform-driven workflow is the smoke test.
- If the agent uses an `MCPTools` instance, pass it through `tools=[mcp_tools]` directly — AgentOS manages the connect/close lifecycle.
- If a context provider needs a model, reuse `default_model()` so the model id stays in one place.

## 4. Register in `app/main.py`

Add the import and put the new agent first in the `agents=[…]` list:

```python
from agents.<slug_underscore> import <slug_underscore>

agent_os = AgentOS(
    ...
    agents=[<slug_underscore>, platform_builder, platform_manager, platform_engineer],
    ...
)
```

First, because this is the agent the people here actually talk to: Platform Builder, Manager, and Engineer run the platform and are usually reached through Agno rather than directly. The order carries into the AgentOS UI's agent list and into `get_agentos_config`, so what the platform is *for* reads before the machinery that runs it.

This line also puts the agent on Agno's roster: the team lead's runner dispatches every code-defined agent the OS registers, so people can ask for it by name ("Agno, have radar scan the week") from the AgentOS UI, Slack, or any MCP client.

## 5. Manifest entry

Add the agent to [`app/config.yaml`](../../../app/config.yaml) under `manifest`, keyed by the agent's `id`: a one-line description and three suggested prompts. The description renders on the AgentOS home card; quick prompts on the chat page. (The `description=` param on `Agent` is not used in this repo — UI metadata lives here. Optional `labels: [...]` are also supported for home-card tags.)

```yaml
manifest:
  <slug>:
    description: "<one line on what the agent does>"
    quick_prompts:
      - "First example prompt"
      - "Second example prompt"
      - "Third example prompt"
```

## 6. Reload the container

Compose runs uvicorn with a scoped `--reload`, so the new file and its `app/main.py` registration are picked up within a couple of seconds. A restart is the deterministic option:

- **No new pip deps** (the common case):

  ```bash
  docker compose restart agentos-api
  ```

- **New pip deps found in Step 2** — add each package to [`pyproject.toml`](../../../pyproject.toml), then update `requirements.txt` and rebuild:

  ```bash
  ./scripts/generate_requirements.sh
  docker compose up -d --build
  ```

Then verify the agent shows up in the registry before smoke-testing:

```bash
curl -s http://localhost:8000/agents | jq -r '.[].id' | grep <slug>
```

If `<slug>` isn't in the list, the restart didn't pick up your edits — jump to Step 8.

## 7. Smoke test

Poll `/health` until the API is back up, then probe the agent with **one of the quick prompts you wrote in Step 5** (so the smoke test exercises what real users will hit). Substitute `<slug>` and the `message=` value before running:

```bash
until curl -sSf http://localhost:8000/health > /dev/null; do sleep 0.5; done

curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<one of the quick_prompts you just wrote>" \
  -F "user_id=claude-create-agent" \
  -F "stream=false" \
  -o /tmp/agent-out.json \
  -w "HTTP %{http_code} in %{time_total}s\n"

jq -r '.content // .' < /tmp/agent-out.json
```

Pass = `HTTP 200` and a non-empty `.content` field.

> **Studio-builder-pattern agents:** create/edit StudioTools execute immediately against the DB, and the builder pattern treats publish as completion — only `archive_component`, `delete_version`, and `delete_schedule` pause for confirmation. Don't smoke-test with a "Build me X" quick prompt; it will create and publish a real component. Probe with a read-only prompt instead (e.g. "What components can you see in the registry?"), or archive anything the smoke test created (the archive pauses for approval — grant it in the AgentOS UI, or over MCP with the `continue_run` tool).

Check the container logs to see which tools fired:

```bash
docker logs agentos-api --since 30s 2>&1 | grep -E "Running: \w+\(" | head -40
```

(`Running: <tool>(` is the line shape agno emits per tool call when `AGNO_DEBUG=True`, which compose sets for dev. Without `AGNO_DEBUG`, expect no matches — `HTTP 200` and a non-empty body are then your only signal.)

## 8. If the smoke test fails

- **HTTP 404** — the agent isn't registered, the container wasn't restarted, or your edits aren't reaching the bind-mount. Re-check Step 4 and Step 6. If both look right, run `docker inspect agentos-api --format '{{ range .Mounts }}{{ .Source }} → {{ .Destination }}{{ "\n" }}{{ end }}'` to confirm `/app` is bound to *this* repo's path (a stale clone or a different worktree is a common cause).
- **HTTP 5xx** — read `docker logs agentos-api --tail 50` for the traceback. Most failures are import errors, missing env vars, or a typo in the agent's `tools=` list.
- **Empty response** — check the logs for tool call errors (rate limits, missing API keys, MCP server unreachable). Tell the user what went wrong; don't paper over it.
- **Tool not firing when expected** — the instruction prompt isn't strong enough. Tell the user; suggest tightening or running [`improve-agent`](../improve-agent/SKILL.md) once the agent is loaded.

Iterate at most 2-3 times on the prompt before stopping and asking the user.

## 9. Done

When the smoke test passes:

1. **Show them their agent working.** Lead with the answer it just gave in the smoke test. Then the slug, and where to reach it: `https://os.agno.com` (hit **Refresh**, top right, and it's in the Agents list next to the built-in ones), or `http://localhost:8000` directly if their OS isn't connected; the MCP endpoint at `/mcp` (`run_agent` tool); and Agno's roster (Step 4), so they can ask the team lead for it by name — say that one out loud.
2. **Hand them the loop.** The agent is a first draft; the ways to sharpen it are already in this session:
   - [`/extend-agent`](../extend-agent/SKILL.md) — they drive: add a tool or source, teach it a new trick, fix something it got wrong.
   - [`/improve-agent`](../improve-agent/SKILL.md) — you drive: probe it against its own `INSTRUCTIONS`, judge, edit, re-probe until it's reliable. No input needed from them.
   - [`/create-evals`](../create-evals/SKILL.md) — pin today's behavior down as tests. Offer to persist the smoke test that just passed as the first case, so the eval suite (and the scheduled run-evals check) watches their agent from day one. (Studio-builder agents: the smoke probe was deliberately read-only — create-evals is where the build loop gets tested safely, because its cases carry snapshot hooks that delete whatever a run creates.)

   Suggest whichever fits what the smoke test actually showed — if a tool didn't fire or an answer was thin, name that and point at the loop that fixes it.

A simple agent usually takes 5-10 minutes from invoking the `create-agent` skill to working. More if the user asks for custom tools or an MCP server with auth.
