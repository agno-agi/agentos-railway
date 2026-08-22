---
name: create-agent
description: Add a new agent to this AgentOS. Runs guided discovery or takes a concrete idea, then generates agents/slug.py, registers it in app/main.py, adds its manifest entry (description + quick prompts), restarts the container, and smoke-tests it live. Use whenever the user wants to add or create a new agent.
---

# Create a New Agent

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/create-agent`) or describe the task and it triggers automatically._

You are creating a new agent in this AgentOS. The user already has the platform running locally on `http://localhost:8000` (`RUNTIME_ENV=dev`). Compose runs uvicorn with a scoped `--reload`, so code edits are picked up automatically; Step 6 covers when to restart instead.

## 0. Preconditions

- Live container reachable: `curl -sSf http://localhost:8000/health` returns 200. (`docker compose ps` is unreliable from worktrees or alternate clones — trust the health probe.)

If it isn't reachable, ask the user to run `docker compose up -d --build` and wait for it to come up.

## 1. Find the agent worth building

**Be self-driving: ask only what needs a human, decide the rest, and say what you decided.** Two exchanges is the target — one to understand the job, one to confirm what you'll build. The pattern, the slug, the model, and the toolkits are your calls, not the user's. They came here to watch an idea come alive, not to fill in a form.

Use the coding agent's structured user-input control when available (Claude Code's `AskUserQuestion`, Codex's user-input tool, or an equivalent) for the choice-shaped questions below. Use plain prompts for free-form answers.

### First: is this a source file, or is it Platform Builder's?

This platform builds agents two ways, and only one of them is yours. **Lane 1 is a source file in `agents/`, governed by git — that's this skill.** Lane 2 is a component Platform Builder composes at runtime from the safe registry, stored in the database and versioned through the Studio catalog. A runnable id on this platform may have no source file at all.

Take lane 1 when the agent needs something the registry doesn't carry: a toolkit not in [`app/registry.py`](../../../app/registry.py), a custom Python function, a context provider, an MCP server, code the user should own and review. That's the common case, and it's why a coding agent is here.

Hand it to Platform Builder instead when the whole thing composes from blocks the registry already has — registry toolkits, the shared self, the platform knowledge base, the deterministic step functions. Say so plainly and stop: "This one's registry blocks end to end — ask Agno to build it and it's live in a minute, no rebuild, no restart." A file is the heavier instrument; don't reach for it out of habit.

**One exception, and it's absolute: the first agent of a [`setup-platform`](../setup-platform/SKILL.md) run is always a file**, however cleanly it would have composed. That moment is the user watching their own code appear in their own repo and go live — routing it to the runtime builder trades the thing they came for against a minute of build time. Offer lane 2 later, once they have one file they own.

**Then check the id is free, before you write anything.** Both lanes land in the same id space, and the code half wins: `/agents` excludes any database component whose id a registered agent holds, so a file with a taken id doesn't collide loudly — it makes the runtime component disappear from the listing and from Agno's dispatch, with its rows still sitting in the database.

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\t\(.is_component)"'
```

`is_component: true` marks the Studio-built ones. If your slug is taken there, pick a different slug — and if the user's ask was really "change that agent", it's a Platform Builder job, not a file that shadows it. (Same check on `/teams` and `/workflows` when the target is one of those.)

### If they already named an agent

"Build me a GitHub PR reviewer" is a complete brief. **Ask nothing.** Design it (Step 2), then state what you're building in one message and start:

> Building **PR Reviewer** (`pr-reviewer`) — reads open PRs on a repo and summarizes what changed and what looks risky. Uses `GithubTools`; needs `GITHUB_ACCESS_TOKEN`, which is already in your `.env`. Building now — stop me if I've read it wrong.

Don't wait for a reply. Only pause if something is genuinely missing (see **Stop only for this**).

### If they want guidance

Open with **one** question:

> What's something you do every week that you'd rather hand off?

Their first answer will be vague — *"I keep up with what competitors ship"*, *"I triage bugs"*. **Dig once. This is the most important moment in the skill.** A generic answer yields a generic agent, and nobody keeps a generic agent. A specific answer yields an agent about *their* work, which is the one they'll come back to and eventually deploy.

Ask a single grounded follow-up, in their own terms — pick the one that actually unlocks the design:

- Where do you look when you do it? (Which repos, sites, channels, tools?)
- What do you do with the result — post it, file it, decide from it?
- What's the annoying part — the volume, the context-switching, the writing-up?

One follow-up. Not an interrogation.

Then propose **one agent you actually recommend**, plus two alternates, as a single pick. Not a menu to shop through — a recommendation with a fallback. For each: a name, one sentence on what it does, and the toolkit(s) behind it. Ground every toolkit in the `agno-docs` MCP (configured in [`.mcp.json`](../../../.mcp.json)) — never invent one.

Build what makes *their* week easier. Resist the demo classics (news digest, generic web researcher) unless that's genuinely what they described — those are the agents people try once and forget.

### Decide these yourself — don't ask

| Decision | How you decide it |
|---|---|
| **Pattern** | **Direct tools** (the required structure in Step 3; [`agents/manager.py`](../../../agents/manager.py) shows it live — ignore its `learning=` extras) when the agent uses ≤2 toolkits — this is the common case. **Context provider** (mirror the `codebase` wiring in [`agents/engineer.py`](../../../agents/engineer.py)) when it queries one information source — a single `query_<thing>` tool by default, or the provider's direct read tools in `ContextMode.tools` as the engineer does. Pick one and mention it in a clause; never make the user choose. |
| **Slug** | Derive it from the purpose (`pr-reviewer`, `linear-triager`). Kebab-case. State it, don't ask for sign-off. |
| **Model** | `default_model()` — already `gpt-5.6-sol`. Override only if the user asks. |
| **Toolkits** | Choose from what the discovery answers imply, grounded in agno docs (Step 2). Prefer what is already in this image and needs no key — the keyless Parallel MCP for anything web-facing, `HackerNewsTools`, `CalculatorTools`, an agent `FileSystem` for state. Every toolkit beyond that set costs the user a rebuild or a key before their agent answers, and an unverified import costs them the whole platform: check it in the container (Step 2). |
| **Memory / history** | **Wire `learning=shared_self`** ([`app/learning.py`](../../../app/learning.py)) whenever the agent should know the person it works for across sessions — which is most agents worth keeping. It's one import and one line, and it's what joins the new agent to the same self Agno and the three platform agents already carry, instead of starting cold. Leave it off only when the agent's durable state isn't per-user — a ledger, a shared corpus, anything a scheduled run with no user id has to read (see Step 3). History defaults come from the template pattern. Don't ask either way; say which you did. |

### Stop only for this

An API key that the chosen toolkit **requires** and that isn't in `.env`. Check `.env` yourself first — don't ask the user what's in a file you can read. If a key is genuinely missing, say which toolkit needs it and offer the two real choices:

- add the key to `.env` now (they paste it in; never read or print it), or
- swap to a toolkit that's keyless *and already in the image* — or a variant of the idea that is — and build right now. Keyless alone isn't enough: a substitute that needs a package this image lacks trades a missing key for a rebuild, so verify the import (Step 2) before you offer it. (Some jobs have no such route; then the key is the only real choice, so say so plainly.)

Everything else — proceed and report.

## 2. Ground the design in agno docs

If the user named any specific toolkit, MCP server, or integration the agent should use (Linear, Stripe, GitHub, Anthropic Claude, etc.), search agno docs **before** writing code:

- Preferred: the `agno-docs` MCP server (configured in [`.mcp.json`](../../../.mcp.json)) — search for the toolkit / integration name and read the relevant page(s).
- Fallback: fetch <https://docs.agno.com/llms.txt> and search inline for the relevant sections.

For each toolkit, capture four things:

- **Import path** (e.g. `from agno.tools.exa import ExaTools`).
- **Constructor args** that matter for this agent (categories, domains, max_results, etc.).
- **Required env vars** — check them against `.env` yourself. Only stop for the user if a required key is missing (Step 1, **Stop only for this**).
- **Pip dependencies** — some toolkits need extra packages (`exa-py`, `anthropic`, `jina`, `yfinance`, …). The toolkit's `Prerequisites` section lists them. Capture now, then add them to `pyproject.toml` before generating `requirements.txt` in Step 6.

Don't guess any of the four. Skip this step entirely if the agent is chat-only with no tools.

### The image decides dependencies, not the docs page

**Verify the import in the container before you write it.** Most agno toolkits import their third-party package at module scope and raise `ImportError` right there when it's missing — 84 toolkit modules in this image do exactly that today, a clear majority of the ones that need a third-party package at all. A missing package is not a degraded agent, it's a dead platform: `app/main.py` imports every registered agent at module scope, so the `ImportError` propagates out of `app.main`, uvicorn's reload fails, and **nothing serves** — including the agents that worked a minute ago.

```bash
docker exec agentos-api python -c 'from agno.tools.exa import ExaTools'
```

Silence means it's there. An `ImportError` names the package: either add it to `pyproject.toml` and take the rebuild path in Step 6, or pick a different toolkit. Never register an agent whose imports you haven't run in the container.

Absence of a `Prerequisites` section on the docs page proves nothing about this image, so don't read it as "keyless, therefore safe" — `ArxivTools` (`arxiv`, `pypdf`), `WikipediaTools` (`wikipedia`), and `WebSearchTools` / `DuckDuckGoTools` (`ddgs`) all take a key-free docs page and still fail to import here. Of the usual keyless suspects only `HackerNewsTools` is actually in the image.

**For web search there is exactly one route that needs neither a key nor a rebuild** — the keyless Parallel MCP this platform already runs on ([`teams/lead.py`](../../../teams/lead.py), [`app/registry.py`](../../../app/registry.py)):

```python
from agno.tools.mcp import MCPTools

# Keyless. AgentOS connects and closes MCP servers as part of its lifespan.
# timeout_seconds: web_fetch page extraction regularly exceeds the 10s MCP default.
web_tools = MCPTools(
    url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
)
```

It exposes two tools, `web_search` and `web_fetch`. Reach for this whenever the agent needs the web. (`ParallelTools()` is the SDK path the same two files switch to when `PARALLEL_API_KEY` is set — worth mirroring only if the user has that key.)

## 3. Generate the agent file

Create `agents/<slug>.py` (replacing `-` with `_` for the filename: `agents/linear_agent.py`). Follow the closest reference pattern:

- **Direct tools** → follow the required structure below. [`agents/manager.py`](../../../agents/manager.py) is the live example, `learning=` included.
- **Context provider** → mirror the `codebase` part of [`agents/engineer.py`](../../../agents/engineer.py): build the `WorkspaceContextProvider`, unpack `*provider.get_tools()` into `tools=`, and append `provider.instructions()` to the agent's instructions. A toolkit's own `instructions()` is not optional decoration — mounting the tools without it leaves the agent holding tools nobody explained.
- **Studio builder** → mirror [`agents/builder.py`](../../../agents/builder.py) when the agent should create or refine AgentOS components through StudioTools.

Required structure:

```python
"""
<Title>
=======
"""

from agno.agent import Agent

from app.learning import shared_self
from app.settings import default_model
from db import get_postgres_db

INSTRUCTIONS = """\
<one short paragraph describing the agent's job, tools, and the rules
it should follow when answering>
"""

<slug_underscore> = Agent(
    id="<slug>",
    name="<DisplayName>",
    model=default_model(),
    db=get_postgres_db(),
    # One self per human, platform-wide: the same profile and memory Agno and the
    # three platform agents carry. The machine attaches its own tools and recall.
    learning=shared_self,
    # Identity fallback for unauthenticated runs (dev MCP, evals). It pairs with
    # learning: in agentic mode the profile and memory tools are not registered
    # at all on a run carrying no user id, so without this they vanish silently.
    user_id="anonymous-user",
    tools=[...],                     # or context_provider.get_tools()
    instructions=INSTRUCTIONS,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
    markdown=True,
)
```

Notes:

- **Drop the `learning=` / `user_id` pair only for a deliberate reason, and comment the reason in the file.** Per-user is the wrong shape when the agent's durable state belongs to the platform rather than to a person — a ledger of what it has already reported, a queue, anything a scheduled run has to read back. Profile and memory rows are keyed by user id alone, so state filed there is invisible to the next user and to any run without one. Reach for an agent `FileSystem` for that kind of state, and keep learning for what the agent knows about its human.
- Don't add a `if __name__ == "__main__":` smoke block — the platform-driven workflow is the smoke test.
- If the agent uses an `MCPTools` instance, pass it through `tools=[mcp_tools]` directly. AgentOS connects/closes MCP servers automatically — don't manage the lifecycle yourself.
- If a context provider needs a model, reuse `default_model()` so the model id stays in one place.

## 4. Register in `app/main.py`

Add the import and append to the `agents=[…]` list:

```python
from agents.<slug_underscore> import <slug_underscore>

agent_os = AgentOS(
    ...
    agents=[platform_builder, platform_manager, platform_engineer, <slug_underscore>],
    ...
)
```

This list does more than mount REST routes. Agno discovers every component the OS registers, and its runner is wired to dispatch the code-defined ones — so this line is also what puts the new agent on the team lead's roster, runnable by name ("Agno, have radar scan the week") from the AgentOS UI, Slack, or any MCP client. An agent that never lands here is reachable only by the id you give people.

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

Compose runs uvicorn with a scoped `--reload`, so the new agent file and its `app/main.py` registration are picked up automatically within a couple of seconds. Restarting is the deterministic option when you don't want to race the reload:

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

1. **Show them their agent working.** Lead with the answer it just gave in the smoke test — that's their idea, alive, in their own words. Then the slug, and where to reach it: `https://os.agno.com` — hit **Refresh** (top right) and it's in the Agents list next to the built-in ones, or `http://localhost:8000` directly if their OS isn't connected. It's also exposed through the AgentOS MCP endpoint at `/mcp` (`run_agent` tool). And it's on Agno's roster now (Step 4), so they can just ask the team lead for it by name — that's the one worth saying out loud, because it means their agent is part of the platform rather than a file in it.
2. **Hand them the loop.** The agent they just built is a first draft, and both ways to sharpen it are already in this session:
   - [`/extend-agent`](../extend-agent/SKILL.md) — they drive: add a tool or source, teach it a new trick, fix something it got wrong.
   - [`/improve-agent`](../improve-agent/SKILL.md) — you drive: probe it against its own `INSTRUCTIONS`, judge, edit, re-probe until it's reliable. No input needed from them.
   - [`/create-evals`](../create-evals/SKILL.md) — pin today's behavior down as tests. The smoke test that just passed is already a first case in the making; offer to persist it so the eval suite (and the scheduled run-evals check) watches their agent from day one. (Studio-builder agents: the smoke probe was deliberately read-only — create-evals is where the real build loop gets tested safely, because its cases carry snapshot hooks that delete whatever a run creates.)

   Suggest whichever fits what the smoke test actually showed — if a tool didn't fire or an answer was thin, name that and point at the loop that fixes it.

A simple agent usually takes 5-10 minutes from invoking the `create-agent` skill to working. More if the user asks for custom tools or an MCP server with auth.
