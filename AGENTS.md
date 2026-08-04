# AgentOS — Railway template

This file is the source of truth for any agent (Claude Code, Codex, others) working in this repo. `CLAUDE.md` is a symlink to this file — edit one, both update.

## Project Overview

**AgentOS: FastAPI for agents — one AI backend for every frontend.** AgentOS is an agent server built on [Agno](https://docs.agno.com) that turns your agents into a production API that attaches to any client: **REST API** for programmatic use, **chat interfaces** for humans (Slack is wired in; WhatsApp/Telegram/Discord mirror the same pattern), and **MCP** at `/mcp` for AI apps (claude.ai, ChatGPT, Cursor, Claude Code) — which work *through* the platform, not just on it. The repo itself is designed for coding agents to build and extend. It comes with eight coding agent skills that cover platform setup, the full agent development lifecycle, and the production deploy, plus two platform agents — Agent Builder (creates agents, teams, and workflows) and Platform Manager (understands, monitors, and explains the platform) — and Chief, the one your team tags in ("Chief, what's happening with radar?" — "Chief, help plan this"): it holds the thread — people, projects, decisions, living notes — learns how each user works, and answers with the state of play from Slack, claude.ai, ChatGPT, or any MCP client. Postgres (pgvector) handles persistence for sessions, memory, and knowledge. Runs locally via Docker; this template deploys to Railway with a single script and is the reference sibling of the `agentos-*` deployment family — see [Portable core vs. deploy layer](#portable-core-vs-deploy-layer).

## Architecture

```
AgentOS  (app/main.py)
├── Chief        (agents/chief.py)        — team mascot: LearningMachine + notes + web tools
├── Platform Manager (agents/platform_manager.py) — WorkspaceContextProvider + AgentOSTools read-only ops toolkit + shared per-user profile/memory
├── Agent Builder (agents/agent_builder.py) — Agno docs MCP + StudioTools + shared per-user profile/memory
├── DeployCheck  (workflows/deployment_check.py) — deterministic readiness workflow
└── RunEvals     (workflows/run_evals.py) — opt-in eval suite workflow
```

Shared:
- PostgreSQL + pgvector for sessions, memory, knowledge.
- All three reference agents wire the LearningMachine's per-user profile and memory stores over the shared DB — one human, one self across every agent. Entities and notes stay Chief's.
- `app.settings.default_model()` returns `OpenAIResponses(id="gpt-5.6-sol")` — bump the model in one place.
- `app.registry.registry` exposes the safe Studio registry Agent Builder can use: Agno docs MCP, web search, reasoning tools, utility functions, the default model, the shared DB, and the reference agents (chief, platform-manager). At runtime agno folds every registered agent's own wiring into the live registry too (`studio`, Chief's `filesystem` notes, the `agentos` ops toolkit) — Agent Builder's instructions treat those as off-limits for builds unless the user asks for the capability by name.
- Scheduler enabled by default (`scheduler=True`); `app/schedules.py` registers schedules from the lifespan. Deployment check runs daily **on** by default — set `ENABLE_DEPLOY_CHECK=False` to disable it. The run-evals schedule is always registered but ships **disabled** (it uses model calls) — flip it on from the AgentOS UI when you want scheduled eval runs; the toggle survives reboots.
- Slack interface lights up automatically when both `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` are set.
- MCP server on by default (`mcp_server=True`) at `/mcp` — see [MCP interface](#mcp-interface).
- MCP OAuth lights up when `MCP_CONNECT_SECRET` is set (built-in authorization server) — how claude.ai and ChatGPT (web) connect; see [MCP interface](#mcp-interface).
- JWT auth on whenever `RUNTIME_ENV` is anything but `dev` (so production deploys, which default to `prd`, are gated by default).

## Key Files

| File | Purpose |
|------|---------|
| [`app/main.py`](app/main.py) | AgentOS entrypoint — lifespan hook, conditional Slack, conditional MCP OAuth, JWT gate. |
| [`app/settings.py`](app/settings.py) | `default_model()` factory. |
| [`app/registry.py`](app/registry.py) | Safe Studio registry used by Agent Builder — docs MCP, web tools, utility functions, reference agents. |
| [`app/config.yaml`](app/config.yaml) | UI manifest per component (keyed by `id`): description + quick prompts. |
| [`agents/chief.py`](agents/chief.py) | The team mascot — LearningMachine (profile, memory, entities in agentic mode) + FileSystem notes + web tools (Parallel SDK or keyless MCP); the Slack default agent. |
| [`agents/platform_manager.py`](agents/platform_manager.py) | Flagship agent — codebase context provider + agno's `AgentOSTools` read-only ops toolkit (usage metrics, run and tool activity from traces, eval history, schedules and their run history, runtime-built components, pending approvals) + deployment-check reports with an on-demand diagnostic run. Wires the shared per-user profile/memory stores. |
| [`agents/agent_builder.py`](agents/agent_builder.py) | Reference agent — creates, edits, and publishes agents, teams, and workflows through StudioTools immediately; only deletes keep a HITL confirmation gate. Wires the shared per-user profile/memory stores. |
| [`workflows/deployment_check.py`](workflows/deployment_check.py) | Reference workflow — a deterministic `Step` that checks DB, auth, scheduler URL, MCP reachability, Slack config, schedule state, and component imports; imported into `app/main.py` and passed to `AgentOS(workflows=[...])`. |
| [`workflows/run_evals.py`](workflows/run_evals.py) | Optional workflow — runs a tagged subset of the eval suite and returns a compact report. Its daily schedule ships disabled — enable it from the AgentOS UI. |
| [`app/schedules.py`](app/schedules.py) | `register_schedules()` — cron registration, called from the lifespan (idempotent, fail-soft). |
| [`db/session.py`](db/session.py) | `get_postgres_db()`, `create_knowledge()`. |
| [`db/url.py`](db/url.py) | Builds the database URL from env. |
| [`evals/cases.py`](evals/cases.py) | Eval cases (each is a `Case` with optional judge + reliability checks). |
| [`evals/__main__.py`](evals/__main__.py) | `python -m evals` — thin entrypoint over agno's eval suite runner (`agno.eval.cli`). |
| [`.agents/skills/`](.agents/skills/) | Dev-time **coding-agent workflows** (`setup-platform`, `create-agent`, `extend-agent`, `improve-agent`, `create-evals`, `eval-and-improve`, `review-and-improve`, `deploy-platform`) — slash commands coding agents run *on this repo*. `.claude/skills` is a committed symlink into it — see [Working with coding agents](#working-with-coding-agents). |
| [`README.md`](README.md) | Public entry point — its Get Started prompt hands a coding agent to the `setup-platform` skill (clone to first agent). |
| [`compose.yaml`](compose.yaml) | Docker Compose for local development. |
| [`railway.json`](railway.json) | Railway deploy config (Docker + 1 replica + 4Gi/2vCPU). |

## Development Setup

### Local with Docker

```bash
cp example.env .env
# Edit .env and set OPENAI_API_KEY

docker compose up -d --build
```

`compose.yaml` sets `RUNTIME_ENV=dev`, `AGNO_DEBUG=True`, and `WAIT_FOR_DB=True` so JWT is off and the API blocks on the DB before serving. It runs uvicorn with a scoped `--reload` (watching `agents/`, `app/`, `db/`, `evals/`, `workflows/`), so code edits hot-reload in a second or two. Restart `agentos-api` after dependency or env changes, or whenever you want a guaranteed-clean state.

### Format & Validate

The format / validate / eval scripts run on the host, so they need a venv. Set one up once:

```bash
./scripts/venv_setup.sh
source .venv/bin/activate
```

Then:

```bash
./scripts/format.sh     # ruff format + import sort
./scripts/validate.sh   # ruff check + mypy (runs both, summarizes)
```

CI installs the same pinned `requirements.txt` and runs the same `scripts/validate.sh` — local and CI never drift.

## Conventions

### Agent pattern

Every agent file has the same shape:

```python
"""
<Title> Agent
=============
"""

from agno.agent import Agent

from app.settings import default_model
from db import get_postgres_db

INSTRUCTIONS = """\
<one short paragraph: what the agent does, which tools it uses, the
rules to follow when answering>
"""

my_agent = Agent(
    id="my-agent",
    name="My Agent",
    model=default_model(),
    db=get_postgres_db(),
    tools=[...],
    instructions=INSTRUCTIONS,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

Three patterns to copy from:

- **Learning agent** — see [`agents/chief.py`](agents/chief.py). Direct tools (the notes toolkit — the agent sees each tool individually) plus `learning=`: the LearningMachine attaches its stores' tools, guidance, and recall automatically. Best when the agent should accumulate durable state across sessions. For a plain direct-tools agent, use the same shape without `learning=`.
- **Context provider** — see [`agents/platform_manager.py`](agents/platform_manager.py). The agent sees one `query_<thing>` tool that hands off to a sub-agent. Best for one-source agents and when collapsing many tools into one keeps the model focused. Platform Manager also shows combining a provider with direct read-only tools — two lenses on one domain.
- **Studio builder** — see [`agents/agent_builder.py`](agents/agent_builder.py). The agent sees StudioTools, a safe `Registry`, Agno docs MCP, and delete-only confirmation gates: create/edit/publish execute immediately (every mutation lands in the DB as a versioned component — inspectable and reversible), while deletes pause for human approval. Best when the user should create or refine components from the AgentOS UI, Slack, or an MCP frontend.

### Database

```python
# Plain agent — sessions, memory, agentic memory live here
from db import get_postgres_db
agent_db = get_postgres_db()

# Agent with a Knowledge base (RAG) — pass through `knowledge=`
from db import create_knowledge
my_kb = create_knowledge("My Knowledge", "my_vectors")
```

Knowledge bases use PgVector with `SearchType.hybrid` and `text-embedding-3-small`. Document contents go into `<table_name>_contents`.

## Adding a new agent

Two options:

1. **Hand it to Claude Code** — run the `/create-agent` skill (or just ask to "create a new agent") in a Claude Code session pointed at this repo. Claude asks the user what the agent should do, generates the file, registers it, smoke-tests it. See [Working with coding agents](#working-with-coding-agents).
2. **Do it manually** — create `agents/<slug>.py`, register in `app/main.py`, add its manifest entry (description + quick prompts) to `app/config.yaml`. The scoped uvicorn reload picks the changes up automatically; restart `agentos-api` if you changed dependencies or env.

## Iterating on an agent

Two recursive loops over the same agent. Use them together.

- **`/extend-agent`** ([`.agents/skills/extend-agent`](.agents/skills/extend-agent/SKILL.md)) — **you drive.** Add a tool, add a capability, refine the prompt, fix a known bug. Claude is the Agno-aware pair-programmer (uses the `agno-docs` MCP for any toolkit research). Loop: change → smoke-test → "anything else?".
- **`/improve-agent`** ([`.agents/skills/improve-agent`](.agents/skills/improve-agent/SKILL.md)) — **Claude drives.** Derives probes from the agent's `INSTRUCTIONS` and from real usage in the database (when the platform has any), judges, edits, re-runs — reflective self-improvement. No user input needed. Loop: mine → probe → judge → edit → re-probe.

Use `/extend-agent` to *change* the agent; use `/improve-agent` to *harden* it against its stated intent. Most fixes from either loop are one sentence in `INSTRUCTIONS`.

## Evals

The eval suite lives in [`evals/`](evals/) and runs on agno's eval suite runner (`agno.eval`): the template declares `Case`s, agno runs them. Each case wraps agno's [`AgentAsJudgeEval`](https://docs.agno.com/evals/agent-as-judge) (LLM judge against a rubric, binary pass/fail) and/or [`ReliabilityEval`](https://docs.agno.com/evals/reliability) (tool-call assertion). Any case whose agent can reach the ungated create/edit/publish Studio tools (anything probing `agent-builder`) must set the builder hooks from `evals/cases.py` (`setup=snapshot_builder_state, teardown=cleanup_new_builder_state`) — setup records the Studio component ids plus learning/note state before the case and teardown hard-deletes any new rows afterwards, even on timeout. Likewise, any other case probing an agent with learning stores (`chief`, `platform-manager`) must set the learning hooks (`setup=snapshot_learning_state, teardown=cleanup_new_learning_state`) — capture is ungated, so entities, memories, and notes really land in the shared stores, and the teardown removes the rows that appeared while the case ran. Two consequences worth knowing before you run the suite against stores people are using: a row that already existed is never deleted, but an edit *inside* one is never undone either; and a row someone else writes during the case window looks new to the diff and gets swept. Run the suite when you are the only writer, and give fixtures names no real team would have on file. As a backstop, a teardown that would sweep more than 25 learning rows refuses and errors instead — that many new rows means the snapshot itself is suspect (a transient DB error during setup reads as an empty store), and a `cleanup:` error beats a silent mass delete. Cases carry tags:

- `smoke` — fast checks that prove the template's self-driving surfaces still work.
- `release` — broader checks for pre-release confidence.
- `live` — current web/source checks that are useful but should not be deterministic release gates.

Run with `python -m evals --tag smoke`, `python -m evals --tag release`, or `python -m evals --name <case>`. Add `--json-output out.json` when a workflow or coding agent needs machine-readable results. Results log to Postgres via `db=eval_db` so history is visible at os.agno.com.

Two skills work this suite from opposite ends. To author coverage — especially for agents you build, which start with none — run [`/create-evals`](.agents/skills/create-evals/SKILL.md): it maps what an agent promises, mines real sessions from Postgres for scenarios, and writes audited cases into a marked user-cases section it adds to `evals/cases.py` on first use. To diagnose failures and fix in scope, run [`/eval-and-improve`](.agents/skills/eval-and-improve/SKILL.md).

## Reviewing the repo

Run the `/review-and-improve` skill ([`.agents/skills/review-and-improve`](.agents/skills/review-and-improve/SKILL.md)). A recurring sweep that diffs docs against code: every agent registered, every env var documented, every path in a doc still exists, every script behaves as advertised. Auto-fixes mechanical drift; flags anything bigger. Best run before a public-facing release or after a refactor.

## Working with coding agents

Dev-time **coding-agent workflows** live in [`.agents/skills/`](.agents/skills/) — the vendor-neutral home for coding-agent assets, mirroring how `CLAUDE.md` symlinks to `AGENTS.md`. `.claude/skills` is a committed symlink into it, so Claude Code picks the skills up on every clone with no setup step; other harnesses (Codex, Cursor, …) can symlink the same folder. (Windows needs developer mode or `core.symlinks=true` for the symlink to materialize.) Claude-specific config like `.claude/settings.json` stays a real file in `.claude/`.

These workflows cover platform setup, the agent-development lifecycle, and the production deploy in this template:

- **`/setup-platform`** — take a fresh clone to a running platform with a first agent live on it: Docker check, `.env`, boot, MCP proof, the AgentOS UI connect, a `create-agent` handoff, then a make-it-yours re-home into the user's own private repo (the template stays wired as `upstream` for updates). The README's Get Started prompt and the os.agno.com onboarding prompt both drive it.
- **`/create-agent`** — scaffold a new agent: guided discovery or from a concrete idea → generate `agents/<slug>.py`, register it, smoke-test it live.
- **`/extend-agent`** — you drive. Add a tool/source, refine `INSTRUCTIONS`, fix a known bug. Uses the `agno-docs` MCP for grounded toolkit research.
- **`/improve-agent`** — Claude drives. Derives probes from the agent's `INSTRUCTIONS` and real usage in the database, judges, edits, re-runs. No user input needed.
- **`/create-evals`** — author eval coverage for an agent: map its promises, mine real sessions from Postgres for scenarios, propose capabilities, write and audit `Case` entries. How a user's own agents join the suite.
- **`/eval-and-improve`** — run the eval suite, diagnose failures, fix in scope until green.
- **`/review-and-improve`** — repo-wide drift sweep (docs vs code vs config).
- **`/deploy-platform`** — take the proven local platform to production with this repo's deploy scripts: preflight the CLI and account, deploy, walk the JWT key step, verify the live platform on its public URL, hand over redeploy/logs/teardown.

Invoke a skill by name (`/extend-agent`) or just describe the task — Claude Code matches it from the skill's `description`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | yes | — | OpenAI key for models + embeddings. |
| `RUNTIME_ENV` | no | `prd` | `dev` disables JWT. Compose sets this to `dev` for local — never put it in an env file that syncs to Railway, or production deploys unauthenticated. |
| `JWT_VERIFICATION_KEY` | prd | — | Public key from os.agno.com. Required when `RUNTIME_ENV=prd` and `authorization=True`, unless `JWT_JWKS_FILE` is set. |
| `JWT_JWKS_FILE` | prd | — | Path to a JWKS file; alternative to `JWT_VERIFICATION_KEY` for production JWT verification. |
| `AGENTOS_URL` | no | `http://127.0.0.1:8000` | Scheduler base URL — cron triggers reach AgentOS over this. `scripts/railway/up.sh` auto-sets it to the created Railway domain (and writes it back into your env file); only set it by hand for custom domains or tunnels. Left at the localhost default in prod, scheduled jobs silently never fire. Also the public origin OAuth metadata derives from when `MCP_CONNECT_SECRET` is set. |
| `MCP_CONNECT_SECRET` | no | — | If set (≥16 chars, e.g. `openssl rand -base64 32`), `/mcp` becomes its own OAuth 2.1 authorization server (built-in tier) so claude.ai and ChatGPT (web) can connect; connecting asks for this secret on a consent page. Requires `AGENTOS_URL`. PAT and JWT bearers keep working alongside. `scripts/railway/up.sh` auto-generates it into your env file on deploy. |
| `AGENTOS_MCP_SIGNING_KEY` | no | — | Optional high-entropy signing-key material (≥32 chars) for OAuth tokens. Unset, a strong key is generated and persisted in the database. Rotating it invalidates outstanding tokens. |
| `ENABLE_DEPLOY_CHECK` | no | `True` | The reference deployment-check cron (`app/schedules.py`) runs daily by default. Set `False` to disable; the workflow stays runnable on demand regardless. |
| `EVALS_TAG` | no | `smoke` | Eval tag run by the run-evals workflow. |
| `EVALS_CASE_TIMEOUT_SECONDS` | no | `90` | Default per-case timeout for run-evals runs; applies only to cases that don't set their own `timeout_seconds`. |
| `EVALS_SUITE_TIMEOUT_SECONDS` | no | `900` | Whole-suite timeout for run-evals runs; per-case timeouts are the granular limit. The default bounds the `smoke` tag's worst case (incl. builder-case teardown). |
| `PARALLEL_API_KEY` | no | — | Authenticates Chief's and the Studio registry's web search tools (Parallel SDK when set; keyless MCP fallback with a lower rate ceiling). |
| `SLACK_BOT_TOKEN` | no | — | Bot token. Set with signing secret to enable the Slack interface. |
| `SLACK_SIGNING_SECRET` | no | — | Signing secret. Both it and the bot token must be set for the interface to load. |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | no | matches compose | Postgres connection. |
| `DB_DRIVER` | no | `postgresql+psycopg` | SQLAlchemy driver. |
| `AGNO_DEBUG` | no | `False` | If `True`, agno emits verbose debug logs. Compose sets this for dev. |
| `WAIT_FOR_DB` | no | `False` | If `True`, the entrypoint blocks on the DB before starting. Compose sets this. |

## Ports

- API: `8000`
- Database: `5432`

## Scheduler

`scheduler=True` is on in [`app/main.py`](app/main.py). A schedule is a cron expression + an HTTP endpoint (a workflow or agent run); the poller fires due jobs in the background. Registration lives in [`app/schedules.py`](app/schedules.py)'s `register_schedules()`, called from the lifespan — idempotent (`if_exists="update"`, safe on every boot) and fail-soft (a bad schedule logs a warning rather than crashing startup).

**Reference examples.** [`workflows/deployment_check.py`](workflows/deployment_check.py) is a one-step, **deterministic** workflow — no LLM, no token cost — that returns a deployment readiness report. It checks DB connectivity and tables, JWT config, scheduler URL, MCP endpoint reachability, Slack env consistency, schedule state, and reference component imports. [`app/schedules.py`](app/schedules.py) registers a daily cron that hits its endpoint (`POST /workflows/deployment-check/runs`). Because it's deterministic and free, the cron runs **on** by default (daily at 13:00 UTC); disable it with `ENABLE_DEPLOY_CHECK=False`.

[`workflows/run_evals.py`](workflows/run_evals.py) runs a tagged subset of the eval suite and returns a compact report. Its daily 14:00 UTC schedule is always registered but ships **disabled** because it uses model calls — enable it from the AgentOS UI (or `POST /schedules/{id}/enable`) to run the smoke-tagged cases daily. The enabled toggle is yours after that: boot-time registration refreshes the schedule's definition but never overrides it. Enable it with the Evals section's only-writer rule in mind: smoke includes learning-store cases whose teardown sweeps anything written to the shared stores during the case window, so a scheduled run while the team is talking to Chief can delete their filings — pick an hour nobody is, or leave the schedule off on a busy platform and run the suite deliberately instead.

To add your own: define a `Workflow` in `workflows/`, import it into [`app/main.py`](app/main.py) and add it to `AgentOS(workflows=[...])`, and register a schedule for it in `register_schedules()`. Other common uses: **maintenance** (purge old sessions, vacuum tables), **periodic re-evaluation** (run `python -m evals` weekly to catch regressions).

See [agno scheduler docs](https://docs.agno.com/agent-os/scheduler) for the cron API.

## Chief

Chief ([`agents/chief.py`](agents/chief.py)) is the team mascot — the one everybody tells things to. "Chief, we're going with PlanetScale over RDS." "Chief, zak's running the launch." From Slack, the AgentOS UI, or any MCP client: it takes what it's told, files it, and connects the dots when someone asks what's happening. The warmth is the surface; underneath, it runs on agno's LearningMachine and FileSystem. Three surfaces split the work: **notes** hold content (decisions with their reasoning, running documents — anything longer than a line), **entities** index the world (people, projects, systems: one-line current values, links, and a `note:` pointer to where the detail lives), and **profile/memory** hold the self (who each user is, how they like to work). The one-claim-one-home rule in its `INSTRUCTIONS` keeps those surfaces from duplicating each other. Chief also carries **web tools** (Parallel SDK when `PARALLEL_API_KEY` is set, keyless MCP otherwise): outside-world questions get searched and grounded, and processed pages are filed as **links plus a distilled takeaway — never pasted payloads**, because notes live in the database (1MB/file, 20MB/namespace caps) and the web can always be fetched again.

**The world is shared, the self is private.** Notes (`FileSystem` namespace `brain` — files land in Postgres under the `fs` schema) and entities (namespace `global`) are shared by everyone on the platform; user profile and user memory are per-user (agentic mode, so their tools only exist when a run carries a user id). The self also spans agents: Agent Builder and Platform Manager wire the same per-user profile/memory stores, so what Chief learns about a user follows them to every reference agent. Corrections supersede rather than accumulate — stating a new fact retires the contradicted one (a judged model call in the write path), and facts render with as-of dates.

**Identity decides what stays private.** A run's identity always wins: Slack runs as the sender, production runs as the JWT `sub`, PATs as `sa:<name>`. `Agent(user_id="anonymous-user")` is only the fallback for anonymous local runs (dev `/mcp`, evals) — without it they would silently lose the profile/memory tools. One caveat to know: the built-in MCP OAuth identifies the *connector registration*, not the person — claude.ai and ChatGPT connect as different `__oauth__:<client_id>` principals, so the same human gets separate private stores per app (shared notes and entities are unaffected). A JWT deployment is what gives one human one Chief across channels.

Two implementation notes: the legacy `enable_agentic_memory` flag stays **off** on all three reference agents — alongside learning stores it would register the legacy MemoryManager's `update_user_memory` tool, shadowing the learning store's tool of the same name. And eval cases that probe a learning-store agent must set the learning hooks (see [Evals](#evals)), and name their fixtures things no real team would have on file. The hooks diff on row identity, so they remove rows a case *created* but cannot undo an edit *inside* a row that already existed — a superseded fact, a replaced relationship, a rewritten note line. Distinctive names are what keep a case out of that path.

## Platform Manager

The platform's ops surface is the Platform Manager agent ([`agents/platform_manager.py`](agents/platform_manager.py)) — read-only by design. It combines the codebase context provider (how the platform is wired) with agno's `AgentOSTools` toolkit over Postgres (usage metrics, run and tool activity from traces, eval history, schedules and their run history, runtime-built components, pending approvals) plus this template's own deployment-check tools (reports — and running the check on demand when no report exists or the latest is stale), diagnoses issues across both lenses, and hands off fixes: code changes go to coding agents via the skills in [`.agents/skills/`](.agents/skills/), component changes go to Agent Builder.

Two of those tools answer the questions an operator asks first. `get_platform_metrics` is the ledger — runs, sessions, distinct users, token spend, and model mix per day. It refreshes before it reads, because agno computes these aggregates only on demand (`POST /metrics/refresh`, a button in the UI): a deployed platform nobody clicks reports nothing at all, indefinitely. The refresh is self-limiting — dates already complete are skipped — and writes only rollups derived from sessions that already exist. `get_run_activity` is the stopwatch, aggregating the traces `tracing=True` already records into per-agent, per-team, and per-workflow run counts, latency (average, p95, slowest), and failures. Traces with no component id are endpoint-level (an `/mcp` call wrapping an agent run) and are reported under a separate `endpoint_level` key so they never double-count the run they wrap; when a list is capped, the payload's notes say so rather than passing a sample off as the whole picture. `get_tool_activity` narrows the stopwatch to spans: which tools are called most, which run slowest, and how model calls are behaving — names, durations, and statuses only, never conversation content. Since 2.8.5 these arrive with agno's `AgentOSTools` toolkit — one line in the tools list — and the template adds only the deployment-check pair on top.

Keep it read-only. Least privilege is the point: an ops surface that only reads can't misfire, needs no confirmation gates, and stays safe to expose from any frontend. Visibility is the one caveat: `AgentOSTools` reads Postgres directly, so REST endpoint scopes never apply to it — anyone who can chat with the agent sees platform-wide aggregates, and `list_pending_approvals` carries user, session, and tool identifiers. That is the toolkit's own guidance too: expose the agent to operators, and trim surfaces with the toolkit's enable flags for anything wider. **Diagnostics are the one sanctioned trigger**: Platform Manager may run observations that are deterministic, free, idempotent, and non-mutating — `run_deployment_check` qualifies (it re-points the same checks the daily cron runs, and the run persists so report history stays coherent); run-evals does not (model spend), and anything that writes platform state never does. The metrics refresh inside `get_platform_metrics` sits just inside that line and is worth stating precisely: it is deterministic, free, and idempotent, and the only rows it writes are aggregates recomputed from sessions the platform already has — it derives, it does not mutate. The LearningMachine's per-user profile and memory writes sit outside the platform-state boundary altogether — they record who the user is, never what the platform does. Nothing that changes source state qualifies on those grounds. Schedule enable/disable and trigger stay out for the same reason: agno exposes them (`POST /schedules/{id}/enable`, `/disable`, `/trigger`), so the boundary here is a deliberate choice, not a missing capability. Approvals follow the same split — `list_pending_approvals` reads the queue; deciding one stays with the human. Future read tools (`git diff` inspection) belong here; mutations belong with coding agents through git, or behind Agent Builder's delete gate — which an MCP client can now approve in-chat via `continue_run`.

## MCP interface

`mcp_server=True` in [`app/main.py`](app/main.py) mounts an MCP server (streamable HTTP) at `/mcp`, on the same port as the REST API. This is the platform's second interface: chat apps (claude.ai and ChatGPT connectors) and coding agents (Claude Code, Cursor) drive the agents, teams, and workflows through it. The README's setup prompt hands a fresh machine to the [`setup-platform`](.agents/skills/setup-platform/SKILL.md) skill, which takes it from clone to first agent — proving `/mcp` end to end along the way (`scripts/mcp_check.sh`).

- **Tools are generic, not per-agent — eight of them.** `get_agentos_config` (how clients discover valid ids), `run_agent(agent_id, message, session_id)`, `run_team`, `run_workflow`, `continue_run`, `cancel_run`, `get_sessions`, and `get_session_runs`. Sessions are read-only over MCP and there is no memory CRUD. `run_agent` returns a trimmed ToolResult: `content[0].text` is the plain answer, and `structuredContent` carries `{run_id, session_id, status}`. The server needs the `fastmcp` package, which ships with the pinned `agno` dependency.
- **Auth mirrors the REST API, with first-class service accounts.** Dev (`RUNTIME_ENV=dev`) is open (unless MCP OAuth is on — next bullet). In prd the same middleware protects `/mcp`; clients send `Authorization: Bearer <token>`. Two token types work side by side: JWTs minted at os.agno.com, and opaque service-account PATs (`agno_pat_…`) minted via `POST /service-accounts` (the route auto-enables once a db is set). A PAT's default scopes — `agents:run`, `teams:run`, `workflows:run`, `sessions:read`, `config:read` — cover all eight tools, and it attributes as `sa:<name>`. The verified token subject overrides any caller-supplied `user_id`, so identity cannot be spoofed. `uvx agno connect` mints a PAT and registers `/mcp` in Claude Code / Claude Desktop / Codex / Cursor.
- **OAuth for the web chat apps — set `MCP_CONNECT_SECRET` and `/mcp` becomes its own OAuth 2.1 authorization server.** claude.ai and ChatGPT (web) connectors authenticate over OAuth only, so this is what lets them connect to a secured platform: paste `https://<domain>/mcp` as a custom connector (the form's optional client ID/secret fields stay empty — DCR registers the app), then approve the consent page with the connect secret. The built-in server (`AgentOSBuiltinAuth(url=agentos_url, secret=MCP_CONNECT_SECRET)` in [`app/main.py`](app/main.py), mirroring the Slack conditional) stores clients, single-use codes, and rotating refresh tokens hashed in Postgres; DCR is public-client + PKCE only; tokenless calls get the `401` + `WWW-Authenticate` challenge connectors use for discovery, and `/info`'s `mcp.oauth` block carries the OAuth discovery details (`auth_mode` keeps describing the REST plane). Existing PAT/JWT bearers keep working on the same endpoint (`MultiAuth`), so enabling OAuth never breaks `agno connect` clients. Gates `/mcp` in dev too — the OAuth flow needs a stable public origin (`AGENTOS_URL`).
- **HITL pauses resume over MCP via `continue_run`.** A paused `run_agent` returns immediately with `status=PAUSED` and unresolved `requirements` dicts in `structuredContent`; the client sets the resolution field (e.g. `confirmation: true`) and passes them back through `continue_run(run_id, agent_id, session_id, requirements)`. So a confirmation gate is no longer a dead end from chat frontends — this is what lets Agent Builder keep the delete gate usable over MCP. One agno 2.8.5 caveat: a bare `confirmation: true` is dropped on the continue path and audited as a rejection — until the upstream fix lands, also set `tool_execution.confirmed: true` inside each requirement you pass back.

Local smoke check: `./scripts/mcp_check.sh` — handshake, tool count, and one quick tool-free `run_agent` call through `/mcp` (finishes in seconds; pass your own question as an argument), executed inside the container. When `/mcp` is auth-gated (OAuth on, or prd JWT), it retries with a short-lived probe service account that it mints and deletes itself. To register the endpoint, run `uvx agno connect` (auto-detects Claude Code / Claude Desktop / Codex / Cursor and verifies with a real handshake); the manual fallback for Claude Code is `claude mcp add --transport http agentos http://localhost:8000/mcp`.

## Slack

Set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` and restart. The default wiring in `app/main.py` routes Slack messages to `chief`, so the mascot lives where the team already talks — each sender keeps their private profile and memory (identity is per-sender; sessions are thread-scoped — a new top-level mention starts a fresh session, replies within that thread share it) while notes and entities are shared. Change the `agent=` arg to point at another agent. See the [agno Slack interface docs](https://docs.agno.com/agent-os/interfaces/overview) for the Slack-side app setup.

For Discord, Telegram, WhatsApp, and custom UIs, mirror the Slack conditional pattern with the relevant agno interface — see [agno interfaces overview](https://docs.agno.com/agent-os/interfaces/overview).

## Portable core vs. deploy layer

This repo is the reference sibling of the `agentos-*` deployment family. Everything that defines the platform is **portable core — identical across the family**: `agents/`, `app/`, `db/`, `workflows/`, `evals/`, the MCP server wiring, the interfaces, and the coding-agent skills in `.agents/skills/`. `Dockerfile`, `compose.yaml`, and `scripts/entrypoint.sh` are shared local-dev/runtime infra, also not deployment-specific.

The **Railway-specific deploy layer** — what a sibling template swaps out — is exactly:

- [`railway.json`](railway.json)
- [`scripts/railway/`](scripts/railway/) (`up.sh`, `env-sync.sh`, `redeploy.sh`, `down.sh`)
- the "Deploying to Railway" prose here and in the README

When editing, keep that boundary crisp: platform behavior belongs in the core, Railway mechanics belong in the deploy layer, and nothing in the core should import from or depend on it.

## Deploying to Railway

Hand it to a coding agent — the [`/deploy-platform`](.agents/skills/deploy-platform/SKILL.md) skill conducts this whole flow (preflight, deploy, the JWT key step, live verification) — or drive it yourself:

```bash
./scripts/railway/up.sh        # provision Postgres + agent-os service
./scripts/railway/env-sync.sh  # sync .env.production (default) or .env
./scripts/railway/redeploy.sh  # redeploy after code changes
./scripts/railway/down.sh      # delete the Railway project (asks for confirmation; --yes to skip)
```

`up.sh` creates the domain before deploying and sets `AGENTOS_URL` to it (on Railway and in your env file), so the scheduler is reachable in prod out of the box. It also generates `MCP_CONNECT_SECRET` into the env file when missing and prints it in the closing summary, so chat apps can connect over OAuth from the first deploy — see [MCP interface](#mcp-interface).

JWT auth is on by default. After creating the Railway domain, `up.sh` pauses if `JWT_VERIFICATION_KEY` or `JWT_JWKS_FILE` is missing, so you can connect the OS at os.agno.com (Connect OS → Live, name it `Live AgentOS`, and flip Token-Based Authorization (JWT) on right on the connect panel — Settings → OS & Security is the fallback if you connected without it), paste the full PEM into the prompt, and let the script save it to the env file. Live AgentOS Connections are a paid feature; use `PLATFORM30` to get 1 month off. The script re-reads the env file and pushes the key before the first deploy. If you skip the prompt or run non-interactively, add the key later and run `./scripts/railway/env-sync.sh`.

The Railway *project* is `agentos-railway`; the app *service* is `agent-os`.

## Common Tasks

```bash
# Add a dependency
# 1. Edit pyproject.toml
./scripts/generate_requirements.sh   # keeps existing pins; add `upgrade` to refresh every pin
docker compose up -d --build

# Bump agno (alpha, rc, and final releases are the same flow)
# 1. Edit the agno pin in pyproject.toml
./scripts/generate_requirements.sh agnoctl   # agno follows the pin; agnoctl must be named — agno only floors it at the previous release
docker compose up -d --build
./scripts/validate.sh && python -m evals --tag smoke

# Build a multi-arch image (maintainer-only)
./scripts/build_image.sh

# Tail Railway logs
railway logs --service agent-os
```

## Documentation Links

- [Agno docs](https://docs.agno.com) — full framework reference.
- [Agno LLM-friendly docs](https://docs.agno.com/llms.txt) — concise overview, good for fetching.
- [AgentOS introduction](https://docs.agno.com/agent-os/introduction).
- [Agno tools / toolkits](https://docs.agno.com/tools/toolkits) — 100+ integrations.
- [Agno model providers](https://docs.agno.com/models) — OpenAI, Anthropic, Google, Ollama, Bedrock, Azure, etc.
- [Agno teams](https://docs.agno.com/teams/overview) — multi-agent routing/coordination.
- [Agno workflows](https://docs.agno.com/workflows/overview) — deterministic step-by-step pipelines.
- [Agno interfaces](https://docs.agno.com/agent-os/interfaces/overview) — Slack, Discord, Telegram, WhatsApp, custom UIs.
