---
name: create-agent
description: Add a new agent to this AgentOS. Runs guided discovery or takes a concrete idea, then generates agents/slug.py, registers it in app/main.py, adds its manifest entry (description + quick prompts), reloads the selected development runtime, and smoke-tests it for you. Covers the product agent too — ingest a product's website/docs into the product knowledge base and build a knowledge-only agent over it. Use whenever the user wants to add or create a new agent, or names a product (theirs or one they use) they want an agent for.
---

# Create a New Agent

> _Coding-agent workflow: run as `/create-agent` or by describing the task._

## 0. Select the development runtime

Read `AGENTS.md` and inspect `git status`. Use the runtime already serving this checkout;
do not switch modes or start a second API on port 8000.

- **Compose API:** confirm its bind mount points to this checkout. Run Python with
  `docker compose exec -T agentos-api python`; inspect `docker compose logs agentos-api`.
  If setup is needed, follow [setup-platform](../setup-platform/SKILL.md).
- **Host API:** follow the [README Engineers commands](../../../README.md#engineers).
  Confirm the process's working directory and startup environment. Run Python with
  `.venv/bin/python` and the same `.env`/runtime/DB settings as that process; use
  `uv run --no-project --env-file .env .venv/bin/python` when loading the env file.
  Keep the API in a persistent terminal and inspect that process's log. No API container
  or container bind mount is required in this mode.

Check `/health` at the configured endpoint with its existing authentication. If unavailable,
diagnose the selected runtime rather than assuming Compose is required. Use a bounded startup
wait and inspect logs on failure. For MCP checks use `scripts/mcp_check.sh` with Compose or
`MCP_CHECK_HOST=1 ./scripts/mcp_check.sh` with the host API.

## 1. Find the agent worth building

**Be self-driving: ask only what needs a human, decide the rest, say what you decided.** Two exchanges is the target. Use the harness's structured choice control for choice-shaped questions, plain prompts for free-form ones.

This skill builds lane 1 — a source file in `agents/`, governed by git. Lane 2 is a component OS Manager composes at runtime; it can't touch the repo, so anything needing a code change (a toolkit the registry lacks, custom Python, a dependency, growing [`app/registry.py`](../../../app/registry.py)) is yours.

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
| **Pattern** | **Product agent** when the ask names a product. **Direct tools** (the Agent shape below) for ≤2 toolkits — the common case. For one information source, use the appropriate supported toolkit or knowledge base; verify the pinned API before choosing a different composition. |
| **Slug** | From the purpose, kebab-case (`pr-reviewer`). |
| **Model** | `default_model()`. Override only if asked. |
| **Toolkits** | From the discovery answers, grounded in docs. Prefer what's in the image and keyless: the Parallel MCP for anything web-facing, `HackerNewsTools`, `CalculatorTools`. |
| **Memory** | `learning=shared_learning` whenever the agent should know its person across sessions — most agents. Off only when its durable state is the platform's, not a person's (a ledger, a queue). Say which. |

**Stop only for** an API key the chosen toolkit requires that isn't in `.env` (check yourself). Offer: add it to `.env` (never read or print it), or a keyless toolkit already in the image.

## 2. Ground the design in agno docs

For every toolkit or MCP server, search the `agno-docs` MCP (fallback: <https://docs.agno.com/llms.txt>) and capture the import path, the constructor args that matter, required env vars, and pip dependencies. Skip if chat-only.

**Verify imports in the selected runtime** before adding them to application startup.
Run this Python in the Compose container or the host environment selected in Step 0:

```python
from agno.tools.exa import ExaTools
```

Check the installed Agno version against `pyproject.toml`; verify optional dependencies
instead of assuming that a toolkit is installed.

For web access, reuse `get_web_tools()` from `app.registry` when its contract fits. Its keyless branch uses this MCP configuration:

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
    # Identity fallback for unauthenticated runs (dev MCP, evals).
    user_id="anonymous-user",
    tools=[...],
    instructions=INSTRUCTIONS,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

- No `offload_tool_results` — that's for the OS Manager and its internal members only.
- Drop `learning=`/`user_id` only for a stated reason. Company knowledge belongs in Company wiki. For a notebook, import `shared_notes` from `app.registry` and add `shared_notes.tools()` to `tools`. User scoping follows AgentOS user isolation; keep personal profiles in per-user learning.
- **Every line ≤120 characters, `INSTRUCTIONS` included** — the repo lints `E501` and ruff won't reflow string literals. Wrap long bullets with a two-space hanging indent.

### The product agent

Answers questions about one product from that product's docs, and nothing else. The recommended first agent (setup-platform hands off here). Two trust rules: **knowledge search is its only tool** (no web tools, no notes — it can answer badly but must not act badly; `learning=shared_learning` stays, so it knows each person across sessions), and **it reads a dedicated product knowledge base, never `shared-knowledge`** — operator content stays out of an end-user agent's retrieval. No product knowledge base ships by default. Declare one in [`app/registry.py`](../../../app/registry.py) when creating this agent; Studio can use it once registered.

Choose the slug, documentation root URL and an initial page cap (normally 50). Explain that ingestion may incur embedding and extraction charges; do not quote a fixed cost without a current, applicable estimate. A capped crawl can omit relevant pages, so report its actual coverage and expand it when needed.

**Declare the knowledge base** in `app/registry.py` before `registry = Registry(...)`:

```python
product_knowledge = create_knowledge(name="product-knowledge", table_name="product_knowledge")
```

Add it to `registry.knowledge` and the existing `AgentOS(knowledge=[...])` list in `app/main.py`, preserving all current knowledge entries.
Use a product-specific variable, name and table for additional products. Reuse a matching
existing declaration; do not mix unrelated products or operator documents. Import the
knowledge object and `shared_learning` from `app.registry` in the new agent.

**Ingest** through Agno's `KnowledgeManagementTools` bound to that knowledge base.
Run this Python using the selected runtime, substituting the product URL and declaration:

```python
import asyncio

from agno.tools.knowledge import KnowledgeManagementTools
from app.registry import product_knowledge

tools = KnowledgeManagementTools(knowledge=product_knowledge)
print(asyncio.run(tools.aingest_url(None, "https://docs.example.com", max_pages=50)))
```

Inspect the returned result and verify content was stored before testing retrieval. Do not promise a page count, cost or runtime without measuring it. For host development run the same code with the configured venv and environment.

**The file:** the structure above with `knowledge=product_knowledge` (from [`app/registry.py`](../../../app/registry.py)), `learning=shared_learning`, and no tools. Write `INSTRUCTIONS` yourself in the product's own terms — its name, how its docs speak, the support channel you saw in the pages — and write them against the failure mode that breaks product agents: **the model remembers the real docs and completes gaps from memory under a real citation** — exact flags, prices, and code that were never in the returned text. A prompt that merely says "answer from the docs, say so if not covered" does not stop it; the following rules make that expectation explicit and testable. Include these rules and verify them with probes:

- a detail counts as documented only when it appears in text the search returned — a page that merely mentions a topic (a name in a list, a link, a heading) does not document it;
- only returned Source URLs get cited, never one from memory, and none on a refusal;
- when the docs do not answer, the agent says so, names the closest page, and points to support rather than writing a partial how-to — and it declines anything off topic, easy asks included, without adopting another name or product.

Step 7: three probes, not one — a covered question (details plus a Source URL), an in-scope question the cap probably excluded (a grounded refusal pointing at support — the pass that matters most), an off-topic one (a scoped refusal). Before calling a refusal-probe answer a leak, check the base — `select count(*) from ai.product_knowledge where content ilike '%<detail>%'` — index and cheat-sheet pages cover far more than their titles. Thin covered answers → raise the cap and re-ingest before touching the prompt. Step 9: lead with the serving story — live in the UI, over MCP, on Agno's roster; claude.ai/ChatGPT via connectors once deployed; for their end users, REST with per-user JWTs (`user_isolation=True` ships on; `JWT_JWKS_FILE` lets their login mint the tokens).

## 4. Register in `app/main.py`

Import the new agent and insert it into the existing `agents` list. Preserve every existing
application agent and `*engineers`; do not replace the list with a starter example. Preserve
the `teams`, `workflows`, `knowledge`, manager and Company wiring too. Check both code and
Studio IDs before registration. AgentOS makes registered agents discoverable to OS Manager.

For example, adding a new agent when another already exists is an insertion:

```diff
 agents=[
+    new_agent,
     existing_agent,
     *engineers,
 ],
```

## 5. Manifest entry

In [`app/config.yaml`](../../../app/config.yaml) under `manifest`, keyed by id: one-line description and three quick prompts (the home card and chat page read these; `Agent(description=)` is unused here).

## 6. Reload the selected runtime

For Compose, restart `agentos-api` when needed; for the host API, use the existing reload
process or restart that host process with its original environment. YAML/env changes need
an explicit restart. Do not run `docker compose up` for a host API.

After dependency changes, regenerate `requirements.txt`, update the host venv if used
(deactivate before `scripts/venv_setup.sh`), and rebuild both Dockerfile targets as required
by `AGENTS.md`. Restart the selected API and confirm `/health` within a bounded wait.
Verify the new agent and all previously registered application agents remain in `/agents`.

## 7. Smoke test

```bash
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<one of the quick_prompts>" -F "user_id=claude-create-agent" -F "stream=false" \
  -o /tmp/agent-out.json -w "HTTP %{http_code} in %{time_total}s\n"
jq -r '.content // .' < /tmp/agent-out.json
```

Use the configured endpoint/authentication if different from this local example. Inspect the run status, answer, tool results and the selected runtime log; HTTP 200 and nonempty content alone are not a pass. A run must complete and satisfy the prompt. Studio probes should be read-only unless mutations are explicitly in scope; a "build me X" prompt creates and publishes a real component.

## 8. If it fails

- **404** — inspect registration, reload status and whether the selected runtime serves this checkout.
- **5xx** — inspect the selected runtime's logs for import/configuration errors.
- **Empty, paused or failed run** — inspect run status and tool errors before changing the prompt.
- **Tool not firing** — inspect tool registration, connection and the scenario's expectations;
  use [eval-and-improve](../eval-and-improve/SKILL.md) for behavioral diagnosis.

Iterate 2–3 times, then ask.

## 9. Done

Lead with the smoke-test answer. Then where it lives: `https://os.agno.com/?ref=railway-template` (**Refresh**, Agents list) or `http://localhost:8000`; `/mcp` (`run_agent`); Agno's roster — say that one out loud. Then the loop: [`/extend-agent`](../extend-agent/SKILL.md) (they drive), [`/eval-and-improve`](../eval-and-improve/SKILL.md) (you drive), [`/create-evals`](../create-evals/SKILL.md) (offer to persist the smoke test as the first case). Report measured setup/ingestion results and any verification still outstanding.
