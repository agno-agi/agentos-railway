---
name: create-agent
description: Add a new agent to this AgentOS. Runs guided discovery or takes a concrete idea, then generates agents/slug.py, registers it in app/main.py, adds its manifest entry (description + quick prompts), restarts the container, and smoke-tests it for you. Covers the product agent too — ingest a product's website/docs into the product knowledge base and build a knowledge-only agent over it. Use whenever the user wants to add or create a new agent, or names a product (theirs or one they use) they want an agent for.
---

# Create a New Agent

> _Coding-agent workflow: run as `/create-agent` or by describing the task._

The platform is on `http://localhost:8000` (`RUNTIME_ENV=dev`); code edits hot-reload.

## 0. Preconditions

`curl -sSf http://localhost:8000/health` returns 200. If not, ask the user to `docker compose up -d --build`.

## 1. Find the agent worth building

**Be self-driving: ask only what needs a human, decide the rest, say what you decided.** Two exchanges is the target. Use the harness's structured choice control for choice-shaped questions, plain prompts for free-form ones.

This skill builds lane 1 — a source file in `agents/`, governed by git. Lane 2 is a component Platform Builder composes at runtime; it can't touch the repo, so anything needing a code change (a toolkit the registry lacks, custom Python, a dependency, growing [`app/registry.py`](../../../app/registry.py)) is yours.

**Check the id is free first** — both lanes share one id space and code silently wins, hiding a Studio-built component under your file:

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | "\(.id)\t\(.is_component)"'
```

**They named an agent** ("build me a GitHub PR reviewer") → ask nothing. Design it, state it in one message, start:

> Building **PR Reviewer** (`pr-reviewer`) — reads open PRs on a repo and summarizes what changed and what looks risky. Uses `GithubTools`; needs `GITHUB_ACCESS_TOKEN`, already in your `.env`. Building now — stop me if I've read it wrong.

**They named a product** (a URL, "an agent for Acme") → the product-agent pattern in Step 3. Ask nothing beyond the URL.

**They want guidance** → one question: *"What's something you do every week that you'd rather hand off?"* Dig once with a grounded follow-up (where do you look? what do you do with the result? what's the annoying part?), then propose one recommendation plus two alternates — name, one sentence, toolkit — grounded in the `agno-docs` MCP ([`.mcp.json`](../../../.mcp.json)). Skip the demo classics.

Decide these yourself:

| Decision | How |
|---|---|
| **Pattern** | **Product agent** when the ask names a product. **Direct tools** ([`agents/manager.py`](../../../agents/manager.py)) for ≤2 toolkits — the common case. **Context provider** ([`agents/engineer.py`](../../../agents/engineer.py)) when it queries one information source. |
| **Slug** | From the purpose, kebab-case (`pr-reviewer`). |
| **Model** | `default_model()`. Override only if asked. |
| **Toolkits** | From the discovery answers, grounded in docs. Prefer what's in the image and keyless: the Parallel MCP for anything web-facing, `HackerNewsTools`, `CalculatorTools`, `get_shared_notes_tools()` for files and state. |
| **Memory** | `learning=shared_learning` whenever the agent should know its person across sessions — most agents. Off only when its durable state is the platform's, not a person's (a ledger, a queue). Say which. |

**Stop only for** an API key the chosen toolkit requires that isn't in `.env` (check yourself). Offer: add it to `.env` (never read or print it), or a keyless toolkit already in the image.

## 2. Ground the design in agno docs

For every toolkit or MCP server, search the `agno-docs` MCP (fallback: <https://docs.agno.com/llms.txt>) and capture the import path, the constructor args that matter, required env vars, and pip dependencies. Skip if chat-only.

**Verify every import in the container before writing it** — a missing package is a dead platform, not a degraded agent (`app/main.py` imports every agent at module scope):

```bash
docker exec agentos-api python -c 'from agno.tools.exa import ExaTools'
```

Many key-free toolkits still fail to import here (`ArxivTools`, `WikipediaTools`, `DuckDuckGoTools`); of the usual suspects only `HackerNewsTools` is in the image. Web search without a key or rebuild is the keyless Parallel MCP this platform already runs on:

```python
from agno.tools.mcp import MCPTools

web_tools = MCPTools(
    url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
)
```

(`ParallelTools()` when the user has `PARALLEL_API_KEY`.) It exposes `web_search` and `web_fetch`. AgentOS manages MCP connect/close.

## 3. Generate the agent file

Create `agents/<slug_underscore>.py`:

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
- <one rule per line: which tool for what, what to refuse, what to hand off>\
"""

<slug_underscore> = Agent(
    id="<slug>",
    name="<DisplayName>",
    model=default_model(),
    db=get_postgres_db(),
    learning=shared_learning,
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    tools=[...],
    instructions=INSTRUCTIONS,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

- No `offload_tool_results` — that's for the four platform agents only.
- Drop `learning=`/`user_id` only for a stated reason, in a comment. Platform-owned state goes in the shared notebook: `tools=[*get_shared_notes_tools(), ...]` ([`app/notes.py`](../../../app/notes.py)), working files under `<slug>/`.
- Context provider: spread `provider.get_tools()` into `tools=` and append `provider.instructions()` to the instructions.
- **Every line ≤120 characters, `INSTRUCTIONS` included** — the repo lints `E501` and ruff won't reflow string literals. Wrap long bullets with a two-space hanging indent like [`agents/manager.py`](../../../agents/manager.py).

### The product agent

Answers questions about one product from that product's docs, and nothing else. The recommended first agent (setup-platform hands off here). Two trust rules: **knowledge search is its only tool** (no web tools, no notes — it can answer badly but must not act badly; `learning=shared_learning` stays, so it knows each person across sessions), and **it reads `product-knowledge`, never `shared-knowledge`** (both in [`app/knowledge.py`](../../../app/knowledge.py) — operator content stays out of an end-user agent's retrieval). Platform Builder builds the same agent at runtime from the same pieces; this is the code-level twin.

Decide and state: slug from the product; root URL (prefer the docs subdomain); page cap **50** — the sitemap in order up to the cap, never a keyword slice (a skipped page turns a true answer into "not documented"). Cost, said once: embeddings under a cent for 50 pages; Parallel spends about one credit per 8 pages.

**Ingest** with the platform's own function ([`app/tools.py`](../../../app/tools.py) — sitemap discovery with indexes followed, Parallel-backed extraction when `PARALLEL_API_KEY` is set with a built-in fetcher otherwise, one row per page with its source URL). Run it inside the container — no host venv needed:

```bash
docker exec agentos-api python -c "import asyncio; from app.tools import get_knowledge_management_tools; \
print(asyncio.run(get_knowledge_management_tools().aingest_url(None, 'https://docs.example.com')))"
```

It returns `pages`, `route`, and `seconds` (50 pages: ~25s with Parallel, ~2 minutes without). Zero pages is a stop. Re-run it when the docs change — it refreshes in place.

**The file:** the structure above with `knowledge=product_knowledge` (from [`app/knowledge.py`](../../../app/knowledge.py)), `learning=shared_learning`, and no tools. Write `INSTRUCTIONS` yourself in the product's own terms — its name, how its docs speak, the support channel you saw in the pages — and write them against the failure mode that breaks product agents: **the model remembers the real docs and completes gaps from memory under a real citation** — exact flags, prices, and code that were never in the returned text. A prompt that merely says "answer from the docs, say so if not covered" does not stop it; these three guarantees do, at no cost to covered answers. So the instructions must guarantee:

- a detail counts as documented only when it appears in text the search returned — a page that merely mentions a topic (a name in a list, a link, a heading) does not document it;
- only returned Source URLs get cited, never one from memory, and none on a refusal;
- when the docs do not answer, the agent says so, names the closest page, and points to support rather than writing a partial how-to — and it declines anything off topic, easy asks included, without adopting another name or product.

Step 7: three probes, not one — a covered question (details plus a Source URL), an in-scope question the cap probably excluded (a grounded refusal pointing at support — the pass that matters most), an off-topic one (a scoped refusal). Before calling a refusal-probe answer a leak, check the base — `select count(*) from ai.product_knowledge where content ilike '%<detail>%'` — index and cheat-sheet pages cover far more than their titles. Thin covered answers → raise the cap and re-ingest before touching the prompt. Step 9: lead with the serving story — live in the UI, over MCP, on Agno's roster; claude.ai/ChatGPT via connectors once deployed; for their end users, REST with per-user JWTs (`user_isolation=True` ships on; `JWT_JWKS_FILE` lets their login mint the tokens).

## 4. Register in `app/main.py`

Import it and put it **first** in `agents=[…]` — it's what the platform is for; the platform agents come after. That line also puts it on Agno's roster (the team runs every registered agent by name).

```python
from agents.<slug_underscore> import <slug_underscore>

agent_os = AgentOS(
    ...
    agents=[<slug_underscore>, platform_builder, platform_manager, platform_engineer],
)
```

## 5. Manifest entry

In [`app/config.yaml`](../../../app/config.yaml) under `manifest`, keyed by id: one-line description and three quick prompts (the home card and chat page read these; `Agent(description=)` is unused here).

## 6. Reload

```bash
docker compose restart agentos-api                                   # no new deps
./scripts/generate_requirements.sh && docker compose up -d --build   # new deps in pyproject.toml
curl -s http://localhost:8000/agents | jq -r '.[].id' | grep <slug>  # missing → Step 8
```

## 7. Smoke test

```bash
until curl -sSf http://localhost:8000/health > /dev/null; do sleep 0.5; done
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<one of the quick_prompts>" -F "user_id=claude-create-agent" -F "stream=false" \
  -o /tmp/agent-out.json -w "HTTP %{http_code} in %{time_total}s\n"
jq -r '.content // .' < /tmp/agent-out.json
docker logs agentos-api --since 30s 2>&1 | grep -E "Running: \w+\(" | head -40   # which tools fired
```

Pass = 200 and non-empty content. Studio-builder-pattern agents: probe read-only ("What components can you see?") — a "build me X" prompt creates and publishes a real component.

## 8. If it fails

- **404** — not registered, not restarted, or the container is bound to another checkout: `docker inspect agentos-api --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}'`.
- **5xx** — `docker logs agentos-api --tail 50`: usually an import error, a missing env var, or a typo in `tools=`.
- **Empty response** — tool errors in the logs (rate limit, key, MCP unreachable). Tell the user.
- **Tool not firing** — the prompt isn't strong enough; suggest [`improve-agent`](../improve-agent/SKILL.md).

Iterate 2–3 times, then ask.

## 9. Done

Lead with the smoke-test answer. Then where it lives: `https://os.agno.com` (**Refresh**, Agents list) or `http://localhost:8000`; `/mcp` (`run_agent`); Agno's roster — say that one out loud. Then the loop: [`/extend-agent`](../extend-agent/SKILL.md) (they drive), [`/improve-agent`](../improve-agent/SKILL.md) (you drive), [`/create-evals`](../create-evals/SKILL.md) (offer to persist the smoke test as the first case). A simple agent takes 5–10 minutes; a product agent about the same, ingestion being most of it.
